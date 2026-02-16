from fastapi import Depends, HTTPException, APIRouter, status, Response
from sqlalchemy.orm import Session
from .. database import get_db
from .. import schemas, utils, models, oauth2
from fastapi.security.oauth2 import OAuth2PasswordRequestForm

router = APIRouter(tags=['Authentication'])
UserRequest = schemas.UserCreate
UserResponse = schemas.UserResponse


# ----------------------------------------------------------------------------- CREATE A NEW USER
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user(user:UserRequest, db: Session = Depends(get_db)):
    hashed_password = utils.hashing(user.password)
    user.password = hashed_password
    user_data = user.dict()
    user_data['password'] = hashed_password

    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = models.User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# ----------------------------------------------------------------------------- LOGIN USER
@router.post("/login")
def login(user_credentials:OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f"Incorrect Credentials")

    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f"Incorrect Credentials")

    access_token = oauth2.create_access_token(data = {"user_id": user.id})
    return {"clp_access_token": access_token, "token_type": "bearer"}