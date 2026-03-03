from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from starlette.responses import Response

from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(prefix="/ratings", tags=["Course Ratings"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_course_or_404(course_id: int, db: Session) -> models.Course:
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Course {course_id} not found")
    return course


def _require_enrolled_student(course_id: int, current_user: models.User, db: Session) -> None:
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can rate courses")

    enrolled = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be enrolled in this course to rate it")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

# ----------------------------------------------------------------------------- RATE A COURSE
@router.post("/course/{course_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.CourseRatingResponse)
def rate_course(
    course_id: int,
    payload: schemas.CourseRatingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _get_course_or_404(course_id, db)
    _require_enrolled_student(course_id, current_user, db)

    existing = db.query(models.CourseRating).filter(
        models.CourseRating.user_id == current_user.id,
        models.CourseRating.course_id == course_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already rated this course. Use PUT to update your rating."
        )

    new_rating = models.CourseRating(
        user_id=current_user.id,
        course_id=course_id,
        rating=payload.rating,
        comment=payload.comment
    )
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    return new_rating

# ----------------------------------------------------------------------------- UPDATE MY RATING
@router.put("/course/{course_id}", response_model=schemas.CourseRatingResponse)
def update_my_rating(
    course_id: int,
    payload: schemas.CourseRatingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    _get_course_or_404(course_id, db)
    _require_enrolled_student(course_id, current_user, db)

    rating = db.query(models.CourseRating).filter(
        models.CourseRating.user_id == current_user.id,
        models.CourseRating.course_id == course_id
    ).first()
    if not rating:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="You have not rated this course yet. Use POST to add a rating.")

    rating.rating = payload.rating
    rating.comment = payload.comment
    db.commit()
    db.refresh(rating)
    return rating
