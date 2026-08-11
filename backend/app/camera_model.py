from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from .database import Base


class Camera(Base):

    __tablename__ = "cameras"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    name = Column(
        String,
        nullable=False
    )


    ip = Column(
        String,
        index=True,
        nullable=False
    )


    stream_url = Column(
        String,
        default=""
    )


    location = Column(
        String,
        default=""
    )


    status = Column(
        String,
        default="unknown"
    )


    last_seen = Column(
        DateTime,
        nullable=True
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )