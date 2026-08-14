from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from .database import Base


class EndpointActivity(Base):

    __tablename__ = "endpoint_activity"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    device_id = Column(
        Integer,
        index=True,
        nullable=False
    )

    hostname = Column(
        String,
        index=True,
        default=""
    )

    username = Column(
        String,
        index=True,
        default=""
    )

    event_type = Column(
        String,
        index=True,
        default=""
    )

    application = Column(
        String,
        default=""
    )

    domain = Column(
        String,
        default=""
    )

    url = Column(
        Text,
        default=""
    )

    description = Column(
        Text,
        default=""
    )

    details_json = Column(
        "metadata",
        Text,
        default=""
    )

    timestamp = Column(
        DateTime,
        index=True,
        default=datetime.utcnow
    )


class ActivityAudit(Base):

    __tablename__ = "activity_audit"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        default=""
    )

    action = Column(
        String,
        default=""
    )

    detail = Column(
        Text,
        default=""
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
