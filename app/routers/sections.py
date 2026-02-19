from typing import List
from fastapi import HTTPException, Depends, APIRouter, status
from sqlalchemy.orm import Session
from starlette.responses import Response

from .. import schemas, models, oauth2
from ..database import get_db

router = APIRouter(
    prefix="/sections",
    tags=["Sections"]
)

SectionResponse = schemas.SectionResponse
SectionCreate = schemas.SectionCreate


# ----------------------------------------------------------------------------- CREATE SECTIONS
@router.post("/course/{course_id}", status_code=status.HTTP_201_CREATED, response_model=SectionResponse)
def create_section(course_id: int, section: SectionCreate, db: Session = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()

    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Course with id {course_id} not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add sections to this course")

    existing = (db.query(models.Section).filter(models.Section.course_id == course_id, models.Section.title == section.title).first())

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A section with title '{section.title}' already exists in this course")

    new_section = models.Section(**section.dict(), course_id=course_id)
    db.add(new_section)
    db.commit()
    db.refresh(new_section)
    return new_section

# ----------------------------------------------------------------------------- GET ALL SECTIONS
@router.get("/", response_model=List[SectionResponse])
def get_sections_of_course(db: Session = Depends(get_db)):
    sections = (db.query(models.Section).all())

    if not sections:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No sections found")

    return sections

# ----------------------------------------------------------------------------- GET ALL SECTIONS OF A COURSE
@router.get("/course/{course_id}", response_model=List[SectionResponse])
def get_sections_of_course(course_id: int, db: Session = Depends(get_db)):
    sections = (db.query(models.Section).filter(models.Section.course_id == course_id).order_by(models.Section.order_index.asc()).all())

    if not sections:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No sections found for course {course_id}")

    return sections



# ----------------------------------------------------------------------------- UPDATE A SECTION
@router.put("/{section_id}", response_model=SectionResponse)
def update_section(section_id: int, section_update: SectionCreate, db: Session = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    section_query = db.query(models.Section).filter(models.Section.id == section_id)
    section = section_query.first()

    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Section with id {section_id} not found")

    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this section")

    section_query.update(section_update.dict(), synchronize_session=False)
    db.commit()
    db.refresh(section)
    return section


# ----------------------------------------------------------------------------- DELETE A SECTION
@router.delete("/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db), current_user = Depends(oauth2.get_current_user)):
    section_query = db.query(models.Section).filter(models.Section.id == section_id)
    section = section_query.first()

    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Section with id {section_id} not found")

    course = db.query(models.Course).filter(models.Course.id == section.course_id).first()
    if not course or course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this section")

    section_query.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)