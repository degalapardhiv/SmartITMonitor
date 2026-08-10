import os

from dotenv import load_dotenv


load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

TELEGRAM_ENABLED = (
    os.getenv("TELEGRAM_ENABLED", "true").lower()
    in ("1", "true", "yes")
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")