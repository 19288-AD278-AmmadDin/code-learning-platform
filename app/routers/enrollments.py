from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from starlette.responses import Response
from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(prefix="/enrollments", tags=["Enrollments"])

EnrollmentResponse = schemas.EnrollmentResponse

# ----------------------------------------------------------------------------- CREATE ENROLLMENTS
@router.post("/course/{course_id}", status_code=status.HTTP_201_CREATED, response_model=EnrollmentResponse)
def enroll_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can enroll in courses")

    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    if course.published is False:
        raise HTTPException(status_code=403, detail="This course is not published yet")

    existing = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="You are already enrolled in this course")

    new_enrollment = models.Enrollment(
        user_id=current_user.id,
        course_id=course_id
    )
    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)

    return new_enrollment

# ----------------------------------------------------------------------------- CURRENT USERS' ENROLLMENTS
@router.get("/my", response_model=List[EnrollmentResponse])
def get_my_enrollments(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    if current_user.role != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can view their own enrollments. Instructors see enrollments via course endpoints."
        )

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.user_id == current_user.id)
        .order_by(models.Enrollment.enrolled_at.desc())
        .all()
    )

    return enrollments

# ----------------------------------------------------------------------------- GET ENROLLMENTS FOR CURRENT COURSE
@router.get("/course/{course_id}", response_model=List[EnrollmentResponse])
def get_enrollments_for_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view enrollments")

    enrollments = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.course_id == course_id)
        .order_by(models.Enrollment.enrolled_at.desc())
        .all()
    )
    return enrollments

# ----------------------------------------------------------------------------- DELETE ENROLLMENT FOR COURSE
@router.delete("/course/{course_id}")
def unenroll_from_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user)
):
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="You are not enrolled in this course")

    db.delete(enrollment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)