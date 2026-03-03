from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(prefix="/certificates", tags=["Certificates"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_course_or_404(course_id: int, db: Session) -> models.Course:
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Course {course_id} not found")
    return course

# ----------------------------------------------------------------------------- ISSUE CERTIFICATE (student self-claims after completing course)
@router.post("/course/{course_id}", status_code=status.HTTP_201_CREATED, response_model=schemas.CertificateResponse)
def issue_certificate(course_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can claim certificates")

    # Must be enrolled
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == current_user.id,
        models.Enrollment.course_id == course_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not enrolled in this course")

    # Must have completed the enrollment
    if not enrollment.completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have not completed this course yet. Complete all lessons to claim your certificate."
        )

    # No duplicate certificates
    existing = db.query(models.Certificate).filter(
        models.Certificate.user_id == current_user.id,
        models.Certificate.course_id == course_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certificate already issued for this course")

    certificate = models.Certificate(user_id=current_user.id, course_id=course_id)
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


# ----------------------------------------------------------------------------- GET MY CERTIFICATES
@router.get("/my", response_model=List[schemas.CertificateResponse])
def get_my_certificates(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students have certificates")

    certs = (
        db.query(models.Certificate)
        .filter(models.Certificate.user_id == current_user.id)
        .order_by(models.Certificate.issued_at.desc())
        .all()
    )
    if not certs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No certificates found")
    return certs