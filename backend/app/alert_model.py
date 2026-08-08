from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from .database import Base


class Alert(Base):

    __tablename__ = "alerts"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    device_id = Column(
        Integer
    )


    hostname = Column(
        String
    )


    alert_type = Column(
        String
    )


    value = Column(
        Float
    )


    message = Column(
        String
    )


    severity = Column(
        String
    )


    status = Column(
        String,
        default="OPEN"
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
