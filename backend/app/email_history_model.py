from sqlalchemy import Column, Integer, String, DateTime

from datetime import datetime

from .database import Base


class EmailHistory(Base):

    __tablename__ = "email_history"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    receiver = Column(
        String
    )


    subject = Column(
        String
    )


    status = Column(
        String
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
