from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from starlette.responses import Response

from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/quizzes",
    tags=["Quizzes"]
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_quiz_or_404(quiz_id: int, db: Session) -> models.Quiz:
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quiz with id {quiz_id} not found")
    return quiz


def _get_course_for_lesson(lesson_id: int, db: Session) -> models.Course:
    """Traverse lesson → section → course and return the Course."""
    lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with id {lesson_id} not found")
    section = db.query(models.Section).filter(models.Section.id == lesson.section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated section not found")
    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated course not found")
    return course


def _require_instructor(current_user: models.User) -> None:
    if current_user.role != "instructor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can perform this action")


def _require_course_ownership(course: models.Course, current_user: models.User) -> None:
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this course's content")


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# ----------------------------------------------------------------------------- CREATE QUIZ FOR A LESSON
@router.post(
    "/lesson/{lesson_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.QuizResponse
)
def create_quiz(
    lesson_id: int,
    quiz: schemas.QuizCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    course = _get_course_for_lesson(lesson_id, db)
    _require_course_ownership(course, current_user)

    existing = db.query(models.Quiz).filter(models.Quiz.lesson_id == lesson_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A quiz already exists for lesson {lesson_id}"
        )

    new_quiz = models.Quiz(**quiz.model_dump(), lesson_id=lesson_id)
    db.add(new_quiz)
    db.commit()
    db.refresh(new_quiz)
    return new_quiz


# ----------------------------------------------------------------------------- GET QUIZ FOR A LESSON
@router.get(
    "/lesson/{lesson_id}",
    response_model=schemas.QuizDetailResponse
)
def get_quiz_for_lesson(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    quiz = db.query(models.Quiz).filter(models.Quiz.lesson_id == lesson_id).first()
    if not quiz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No quiz found for lesson {lesson_id}")

    attempts_count = db.query(models.QuizAttempt).filter(models.QuizAttempt.quiz_id == quiz.id).count()
    response = schemas.QuizDetailResponse.model_validate(quiz)
    response.attempts_count = attempts_count
    return response


# ----------------------------------------------------------------------------- GET QUIZ DETAIL BY ID
@router.get(
    "/{quiz_id}",
    response_model=schemas.QuizDetailResponse
)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    quiz = _get_quiz_or_404(quiz_id, db)
    attempts_count = db.query(models.QuizAttempt).filter(models.QuizAttempt.quiz_id == quiz_id).count()
    response = schemas.QuizDetailResponse.model_validate(quiz)
    response.attempts_count = attempts_count
    return response


# ----------------------------------------------------------------------------- UPDATE QUIZ
@router.put(
    "/{quiz_id}",
    response_model=schemas.QuizResponse
)
def update_quiz(
    quiz_id: int,
    quiz_update: schemas.QuizCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    quiz = _get_quiz_or_404(quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    for key, value in quiz_update.model_dump().items():
        setattr(quiz, key, value)

    db.commit()
    db.refresh(quiz)
    return quiz


# ----------------------------------------------------------------------------- DELETE QUIZ
@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    quiz = _get_quiz_or_404(quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    db.delete(quiz)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# ----------------------------------------------------------------------------- ADD QUESTION TO QUIZ
@router.post(
    "/{quiz_id}/questions",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.QuestionResponse
)
def add_question(
    quiz_id: int,
    question: schemas.QuestionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    quiz = _get_quiz_or_404(quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    # Use by_alias=False so we get field names, then map to model column names
    data = question.model_dump(by_alias=False)
    new_question = models.Question(
        question_text=data["text"],
        question_type=data["question_type"],
        quiz_id=quiz_id
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    return new_question


# ----------------------------------------------------------------------------- GET ALL QUESTIONS OF A QUIZ
@router.get(
    "/{quiz_id}/questions",
    response_model=List[schemas.QuestionResponse]
)
def get_questions(
    quiz_id: int,
    db: Session = Depends(get_db)
):
    _get_quiz_or_404(quiz_id, db)
    questions = db.query(models.Question).filter(models.Question.quiz_id == quiz_id).all()
    if not questions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questions found for this quiz")
    return questions


# ----------------------------------------------------------------------------- UPDATE QUESTION
@router.put(
    "/{quiz_id}/questions/{question_id}",
    response_model=schemas.QuestionResponse
)
def update_question(
    quiz_id: int,
    question_id: int,
    question_update: schemas.QuestionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    quiz = _get_quiz_or_404(quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    question = db.query(models.Question).filter(
        models.Question.id == question_id,
        models.Question.quiz_id == quiz_id
    ).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question {question_id} not found in quiz {quiz_id}")

    data = question_update.model_dump(by_alias=False)
    question.question_text = data["text"]
    question.question_type = data["question_type"]
    db.commit()
    db.refresh(question)
    return question


# ----------------------------------------------------------------------------- DELETE QUESTION
@router.delete(
    "/{quiz_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_question(
    quiz_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    quiz = _get_quiz_or_404(quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    question = db.query(models.Question).filter(
        models.Question.id == question_id,
        models.Question.quiz_id == quiz_id
    ).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question {question_id} not found in quiz {quiz_id}")

    db.delete(question)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# ANSWER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

def _get_question_or_404(question_id: int, db: Session) -> models.Question:
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with id {question_id} not found")
    return question


# ----------------------------------------------------------------------------- ADD ANSWER TO QUESTION
@router.post(
    "/questions/{question_id}/answers",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.AnswerResponse
)
def add_answer(
    question_id: int,
    answer: schemas.AnswerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    question = _get_question_or_404(question_id, db)
    quiz = _get_quiz_or_404(question.quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    # For true_false, cap at 2 answers
    if question.question_type == "true_false":
        existing_count = db.query(models.Answer).filter(models.Answer.question_id == question_id).count()
        if existing_count >= 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="True/False questions can only have 2 answers"
            )

    # For single_choice, only one correct answer allowed
    if question.question_type == "single_choice" and answer.is_correct:
        existing_correct = db.query(models.Answer).filter(
            models.Answer.question_id == question_id,
            models.Answer.is_correct == True  # noqa: E712
        ).first()
        if existing_correct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Single choice questions can only have one correct answer"
            )

    data = answer.model_dump(by_alias=False)
    new_answer = models.Answer(
        answer_text=data["text"],
        is_correct=data["is_correct"],
        question_id=question_id
    )
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)
    return new_answer


# ----------------------------------------------------------------------------- GET ALL ANSWERS FOR A QUESTION
@router.get(
    "/questions/{question_id}/answers",
    response_model=List[schemas.AnswerResponse]
)
def get_answers(
    question_id: int,
    db: Session = Depends(get_db)
):
    _get_question_or_404(question_id, db)
    answers = db.query(models.Answer).filter(models.Answer.question_id == question_id).all()
    if not answers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No answers found for this question")
    return answers


# ----------------------------------------------------------------------------- UPDATE ANSWER
@router.put(
    "/questions/{question_id}/answers/{answer_id}",
    response_model=schemas.AnswerResponse
)
def update_answer(
    question_id: int,
    answer_id: int,
    answer_update: schemas.AnswerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    question = _get_question_or_404(question_id, db)
    quiz = _get_quiz_or_404(question.quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    answer = db.query(models.Answer).filter(
        models.Answer.id == answer_id,
        models.Answer.question_id == question_id
    ).first()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Answer {answer_id} not found for question {question_id}")

    # Enforce single_choice correct-answer uniqueness on update
    if question.question_type == "single_choice" and answer_update.is_correct and not answer.is_correct:
        existing_correct = db.query(models.Answer).filter(
            models.Answer.question_id == question_id,
            models.Answer.is_correct == True,  # noqa: E712
            models.Answer.id != answer_id
        ).first()
        if existing_correct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Single choice questions can only have one correct answer"
            )

    data = answer_update.model_dump(by_alias=False)
    answer.answer_text = data["text"]
    answer.is_correct = data["is_correct"]
    db.commit()
    db.refresh(answer)
    return answer


# ----------------------------------------------------------------------------- DELETE ANSWER
@router.delete(
    "/questions/{question_id}/answers/{answer_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_answer(
    question_id: int,
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _require_instructor(current_user)
    question = _get_question_or_404(question_id, db)
    quiz = _get_quiz_or_404(question.quiz_id, db)
    course = _get_course_for_lesson(quiz.lesson_id, db)
    _require_course_ownership(course, current_user)

    answer = db.query(models.Answer).filter(
        models.Answer.id == answer_id,
        models.Answer.question_id == question_id
    ).first()
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Answer {answer_id} not found for question {question_id}")

    db.delete(answer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
