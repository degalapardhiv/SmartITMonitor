from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from app.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# -----------------------------
# Configuration
# -----------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# -----------------------------
# Password Hashing
# -----------------------------

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )

# -----------------------------
# JWT Token
# -----------------------------

def create_access_token(data: dict):

    to_encode = data.copy()

    expire = (
        datetime.utcnow()
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )