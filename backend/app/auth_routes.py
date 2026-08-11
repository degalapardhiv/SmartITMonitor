from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .database import get_db
from .user_model import User
from .security import create_token
from .auth_dependency import get_current_user


router = APIRouter()


ALLOWED_ROLES = {"admin", "viewer"}

MIN_PASSWORD_LENGTH = 8


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# Credentials are optional here so the very first user can bootstrap
# the system before any admin account exists.
optional_security = HTTPBearer(auto_error=False)


def require_admin_or_bootstrap(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
):
    if db.query(User).count() == 0:
        return {"role": "admin"}

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    payload = get_current_user(credentials)

    if payload.get("role", "").lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return payload


@router.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    role: str = "viewer",
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_bootstrap),
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

    role = role.lower().strip()
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Role must be 'admin' or 'viewer'"
        )

    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
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

    role = user.role.lower() if user.role else "viewer"

    token = create_token(
        {
            "username": user.username,
            "role": role
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role
    }


@router.post("/change-password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    username = current_user.get("username")

    if not username:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not pwd_context.verify(
        current_password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )

    user.password_hash = pwd_context.hash(new_password)

    db.commit()

    return {
        "message": "Password updated"
    }
