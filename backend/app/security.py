from datetime import datetime, timedelta

from jose import jwt

from app.config import SECRET_KEY, ALGORITHM


def create_token(data: dict):

    payload = data.copy()

    expire = datetime.utcnow() + timedelta(
        hours=24
    )

    payload["exp"] = expire

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token