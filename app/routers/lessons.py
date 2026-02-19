from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from starlette.responses import Response
from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/lessons",
    tags=["Lessons"]
)

LessonResponse = schemas.LessonResponse
LessonCreate = schemas.LessonCreate

# ----------------------------------------------------------------------------- CREATE LESSONS FOR A SPECIFIC SECTION
@router.post("/section/{section_id}", status_code=status.HTTP_201_CREATED, response_model=LessonResponse)
def create_lesson(section_id: int, lesson: LessonCreate, db: Session = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Section with id {section_id} not found")

    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add lessons to this section")

    existing = (db.query(models.Lesson).filter(models.Lesson.section_id == section_id, models.Lesson.title == lesson.title).first())

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A lesson with title '{lesson.title}' already exists in this section")
    new_lesson = models.Lesson(**lesson.model_dump(by_alias=True, exclude={"section_id"}), section_id=section_id)
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    return new_lesson

# ----------------------------------------------------------------------------- GET LESSONS OF SPECIFIC SECTION
@router.get("/section/{section_id}", response_model=List[LessonResponse])
def get_lessons_of_section(
    section_id: int,
    db: Session = Depends(get_db)
):
    lessons = (
        db.query(models.Lesson)
        .filter(models.Lesson.section_id == section_id)
        .order_by(models.Lesson.order_index.asc())
        .all()
    )

    if not lessons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lessons found for section {section_id}"
        )

    return lessons


# -----------------------------------------------------------------------------
# Get all lessons created by the current instructor (across their courses)
# -----------------------------------------------------------------------------
@router.get("/my", response_model=List[LessonResponse])
def get_my_lessons(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view their lessons"
        )

    lessons = (
        db.query(models.Lesson)
        .join(models.Section)
        .join(models.Course)
        .filter(models.Course.instructor_id == current_user.id)
        .order_by(models.Lesson.section_id, models.Lesson.order_index)
        .all()
    )

    if not lessons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No lessons found for the current instructor"
        )

    return lessons


# -----------------------------------------------------------------------------
# Update a lesson (only the course owner)
# -----------------------------------------------------------------------------
@router.put("/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: int,
    lesson_update: LessonCreate,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    lesson_query = db.query(models.Lesson).filter(models.Lesson.id == lesson_id)
    lesson = lesson_query.first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with id {lesson_id} not found"
        )

    # Check course ownership
    section = db.query(models.Section).filter(models.Section.id == lesson.section_id).first()
    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()

    if not course or course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this lesson"
        )

    # Update (exclude section_id from payload)
    update_data = lesson_update.dict(exclude_unset=True)
    lesson_query.update(update_data, synchronize_session=False)
    db.commit()
    db.refresh(lesson)

    return lesson


# -----------------------------------------------------------------------------
# Delete a lesson (only the course owner)
# -----------------------------------------------------------------------------
@router.delete("/{lesson_id}")
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    lesson_query = db.query(models.Lesson).filter(models.Lesson.id == lesson_id)
    lesson = lesson_query.first()

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson with id {lesson_id} not found"
        )

    section = db.query(models.Section).filter(models.Section.id == lesson.section_id).first()
    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()

    if not course or course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this lesson"
        )

    lesson_query.delete(synchronize_session=False)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)