from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

SUPPORTED_SCHEMES = (
    "postgresql://",
    "postgresql+psycopg2://",
    "postgresql+psycopg://",
    "postgresql+asyncpg://",
)

if not DATABASE_URL.startswith(SUPPORTED_SCHEMES):
    raise RuntimeError(
        "DATABASE_URL must start with a supported scheme "
        "(postgresql:// or postgresql+<driver>://). "
        f"Got: {DATABASE_URL.split('://', 1)[0]}://..."
    )

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
