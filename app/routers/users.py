from typing import List
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from .. database import get_db
from .. import schemas, models, oauth2, utils
from starlette import status
from starlette.responses import Response

router = APIRouter(
    prefix="/users",
    tags= ["Users"]
)
UserResponse = schemas.UserResponse

# ----------------------------------------------------------------------------- GET ALL USERS
@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db),     current_user: int = Depends(oauth2.get_current_user)):
    users = db.query(models.User).all()
    return users

# ----------------------------------------------------------------------------- GET USER BY ID
@router.get("/{id}", response_model=UserResponse)
def get_user(id: int, db: Session = Depends(get_db),     current_user: int = Depends(oauth2.get_current_user) ):
    user = db.query(models.User).filter(models.User.id == id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail = f"User with id: {id} was not found")

    return user


# ----------------------------------------------------------------------------- UPDATE POST BASED ON ID
@router.put("/{id}", response_model=UserResponse)
def update_user(
    id: int,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    updated_user_query = db.query(models.User).filter(models.User.id == id)
    updated_user = updated_user_query.first()

    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id: {id} was not found")

    # Only admin or the user themselves can update
    if current_user.role != "admin" and updated_user.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    # Convert the request to dict and hash password if provided
    user_data = user.dict()
    if "password" in user_data and user_data["password"]:
        user_data["password"] = utils.hashing(user_data["password"])

    updated_user_query.update(user_data, synchronize_session=False)
    db.commit()
    db.refresh(updated_user)

    return updated_user


# ----------------------------------------------------------------------------- DELETE A POST BASED  ON ID
@router.delete("/{id}")
def delete_user(id: int,  db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    deleted_user_query = db.query(models.User).filter(models.User.id == id)

    deleted_user = deleted_user_query.first()

    if deleted_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"user with id: {id} was not found")

    # Only admin or the user themselves can delete
    if current_user.role != "admin" and deleted_user.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    deleted_user_query.delete(synchronize_session=False)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)