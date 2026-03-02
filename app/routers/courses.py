from typing import List
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from .. database import get_db
from .. import schemas, models, oauth2
from starlette import status
from starlette.responses import Response
from .. import utils

router = APIRouter(
    prefix="/courses",
    tags= ["Courses"]
)
CourseResponse = schemas.CourseResponse
CourseRequest = schemas.CourseCreate

# ----------------------------------------------------------------------------- GET ALL COURSES
@router.get("/", response_model=List[schemas.CourseResponse])
def get_courses(db: Session = Depends(get_db)):
    courses = utils.get_courses_with_counts(db)
    return courses

# ----------------------------------------------------------------------------- GET COURSES OF CURRENT USER (instructor's own courses)
@router.get("/my", response_model=List[schemas.CourseResponse])
def get_my_courses(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    if current_user.role != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can view their own courses"
        )

    courses = utils.get_courses_with_counts(db, instructor_id=current_user.id,)
    if not courses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No courses found for current user"
        )

    return courses

# ----------------------------------------------------------------------------- GET CURRENT USER COURSES
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CourseResponse)
def create_course(course: CourseRequest, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    new_course = models.Course(**course.dict(), instructor_id = current_user.id)
    existing_course = (db.query(models.Course).filter(models.Course.instructor_id == current_user.id, models.Course.title == course.title).first())

    if (current_user.role != "instructor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "Students can't add Courses. Only instructors can add courses")

    if existing_course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already created a course with this title." )

    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

# ----------------------------------------------------------------------------- UPDATE COURSE
@router.put("/{id}", response_model=CourseResponse)
def update_post(id: int, course: CourseRequest, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    updated_course_query =  db.query(models.Course).filter(models.Course.id == id)
    updated_course = updated_course_query.first()

    if updated_course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"course with id: {id} was not found")

    if updated_course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail = f"Not authorized to update this course")

    updated_course_query.update(course.dict(), synchronize_session=False)
    db.commit()

    return updated_course

# ----------------------------------------------------------------------------- DELETE A COURSE BASED  ON ID
@router.delete("/{id}")
def delete_course(id: int,  db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    deleted_course_query = db.query(models.Course).filter(models.Course.id == id)

    deleted_course = deleted_course_query.first()
    if deleted_course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"course with id: {id} was not found")

    if deleted_course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail = f"Not authorized to delete this course")

    deleted_course_query.delete(synchronize_session=False)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)
