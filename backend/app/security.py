from datetime import datetime, timedelta

from jose import jwt

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def create_token(data: dict) -> str:

    payload = data.copy()

    expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES

    try:
        from app.settings_center_service import get_token_expire_minutes

        expire_minutes = get_token_expire_minutes()
    except Exception:
        pass

    expire = datetime.utcnow() + timedelta(
        minutes=expire_minutes
    )

    payload["exp"] = expire

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token
