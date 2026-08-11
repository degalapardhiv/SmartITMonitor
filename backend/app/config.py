import logging
import os

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger("app.config")


WEAK_SECRET_KEYS = {
    "",
    "change-me-in-production",
    "change_this_secret_key",
    "change-me",
    "your-secret-key",
    "secret",
    "secret-key",
}


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-key")

if SECRET_KEY in WEAK_SECRET_KEYS or not SECRET_KEY:
    logger.warning(
        "SECRET_KEY is missing or set to a known placeholder value. "
        "Set a strong, unique SECRET_KEY in your environment or .env file "
        "before deploying to production."
    )

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

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
