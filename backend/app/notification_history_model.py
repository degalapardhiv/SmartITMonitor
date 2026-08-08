from sqlalchemy import Column, Integer, String, DateTime

from datetime import datetime

from .database import Base



class NotificationHistory(Base):

    __tablename__ = "notification_history"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    alert_id = Column(
        Integer
    )


    channel = Column(
        String
    )


    status = Column(
        String
    )


    message = Column(
        String
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
