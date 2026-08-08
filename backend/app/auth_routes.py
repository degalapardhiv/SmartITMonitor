from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from passlib.context import CryptContext

from .database import get_db
from .user_model import User
from .security import create_token


router = APIRouter()


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


@router.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    role: str = "viewer",
    db: Session = Depends(get_db)
):

    existing = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )


    if existing:

        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )


    hashed = pwd_context.hash(
        password
    )


    user = User(
        username=username,
        password_hash=hashed,
        role=role
    )


    db.add(user)
    db.commit()
    db.refresh(user)


    return {
        "message": "User created",
        "username": user.username,
        "role": user.role
    }



@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )


    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username"
        )


    if not pwd_context.verify(
        password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid password"
        )


    token = create_token(
        {
            "username": user.username,
            "role": user.role
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role
    }
