from passlib.context import CryptContext
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from app import models

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hashing(password: str):
    return pwd_context.hash(password)

def verify(password: str, hashed_password: str):
    return pwd_context.verify(password, hashed_password)

def get_courses_with_counts(
    db: Session,
    *,
    instructor_id: Optional[int] = None,
) -> List[models.Course]:
    stmt = (
        select(models.Course)
        .options(
            selectinload(models.Course.sections),
        )
    )

    if instructor_id is not None:
        stmt = stmt.where(models.Course.instructor_id == instructor_id)

    result = db.execute(stmt).scalars().all()

    if not result:
        return []

    course_ids = [c.id for c in result]
    count_stmt = (
        select(
            models.Enrollment.course_id,
            func.count(models.Enrollment.id).label("enroll_count")
        )
        .where(models.Enrollment.course_id.in_(course_ids))
        .group_by(models.Enrollment.course_id)
    )
    counts_result = db.execute(count_stmt).all()
    count_map = {row.course_id: row.enroll_count for row in counts_result}

    for course in result:
        course.enrollments_count = count_map.get(course.id, 0)

    return result