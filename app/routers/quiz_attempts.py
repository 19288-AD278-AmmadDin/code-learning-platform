from datetime import datetime, timezone
from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session

from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(prefix="/quiz-attempts", tags=["Quiz Attempts"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_quiz_or_404(quiz_id: int, db: Session) -> models.Quiz:
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz {quiz_id} not found")
    return quiz


def _require_student(current_user: models.User) -> None:
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can submit quiz attempts")


def _calc_score(quiz: models.Quiz, selected_ids: set[int]) -> int:
    """Calculate score (0–100) based on selected answer IDs vs correct answers per question."""
    questions = quiz.questions
    if not questions:
        return 0

    correct_count = 0
    for question in questions:
        correct_ids = {a.id for a in question.answers if a.is_correct}
        student_ids = {a_id for a_id in selected_ids if a_id in {a.id for a in question.answers}}

        if question.question_type == "single_choice":
            # student must have selected exactly the one correct answer
            if student_ids == correct_ids:
                correct_count += 1
        else:  # multiple_choice
            # student must have selected ALL correct and NO wrong answers
            if student_ids == correct_ids:
                correct_count += 1

    return round((correct_count / len(questions)) * 100)

# ----------------------------------------------------------------------------- SUBMIT QUIZ ATTEMPT
@router.post("/quiz/{quiz_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.QuizAttemptResponse)
def submit_attempt(
    quiz_id: int,
    payload: schemas.QuizAttemptSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_student(current_user)
    quiz = _get_quiz_or_404(quiz_id, db)

    # One attempt per student per quiz
    existing = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == current_user.id,
        models.QuizAttempt.quiz_id == quiz_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already submitted an attempt for this quiz"
        )

    # Validate that all submitted answer IDs actually belong to this quiz
    all_answer_ids = {a.id for q in quiz.questions for a in q.answers}
    invalid = set(payload.selected_answer_ids) - all_answer_ids
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Answer IDs {sorted(invalid)} do not belong to this quiz"
        )

    score = _calc_score(quiz, set(payload.selected_answer_ids))

    attempt = models.QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        submitted_at=datetime.now(timezone.utc)
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    response = schemas.QuizAttemptResponse.model_validate(attempt)
    response.passed = score >= quiz.passing_score
    return response

# ----------------------------------------------------------------------------- GET ALL ATTEMPTS FOR A QUIZ (instructor)
@router.get("/quiz/{quiz_id}", response_model=List[schemas.QuizAttemptResponse])
def get_attempts_for_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    if current_user.role != "instructor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can view all attempts")

    quiz = _get_quiz_or_404(quiz_id, db)

    # Verify ownership
    lesson = db.query(models.Lesson).filter(models.Lesson.id == quiz.lesson_id).first()
    section = db.query(models.Section).filter(models.Section.id == lesson.section_id).first()
    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view attempts for this quiz")

    attempts = db.query(models.QuizAttempt).filter(models.QuizAttempt.quiz_id == quiz_id).all()
    if not attempts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No attempts found for this quiz")

    result = []
    for a in attempts:
        resp = schemas.QuizAttemptResponse.model_validate(a)
        resp.passed = a.score >= quiz.passing_score
        result.append(resp)
    return result