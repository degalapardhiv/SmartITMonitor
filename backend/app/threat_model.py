from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Boolean,
)

from .database import Base


class ThreatEvent(Base):

    __tablename__ = "threat_events"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    hostname = Column(
        String,
        index=True
    )

    file_name = Column(
        String,
        default=""
    )

    file_path = Column(
        String,
        default=""
    )

    file_type = Column(
        String,
        default=""
    )

    file_hash = Column(
        String,
        index=True,
        default=""
    )

    detection_name = Column(
        String,
        default=""
    )

    category = Column(
        String,
        index=True,
        default=""
    )

    severity = Column(
        String,
        index=True,
        default="INFO"
    )

    detection_source = Column(
        String,
        default=""
    )

    action = Column(
        String,
        default=""
    )

    status = Column(
        String,
        index=True,
        default="DETECTED"
    )

    username = Column(
        String,
        default=""
    )

    source = Column(
        String,
        default=""
    )

    usb_request_id = Column(
        Integer,
        nullable=True
    )

    quarantine_path = Column(
        String,
        default=""
    )

    quarantine_method = Column(
        String,
        default=""
    )

    escalated = Column(
        Boolean,
        default=False
    )

    reviewed_by = Column(
        String,
        default=""
    )

    reviewed_at = Column(
        DateTime,
        nullable=True
    )

    action_required = Column(
        Boolean,
        default=False
    )

    notes = Column(
        Text,
        default=""
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    detected_at = Column(
        DateTime,
        index=True,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "ix_threat_device_status",
            "device_id",
            "status"
        ),
        Index(
            "ix_threat_category_severity",
            "category",
            "severity"
        ),
        Index(
            "ix_threat_file_hash_device",
            "file_hash",
            "device_id"
        ),
        Index(
            "ix_threat_detected_at",
            "detected_at"
        ),
    )


class ThreatAudit(Base):

    __tablename__ = "threat_audit"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    threat_id = Column(
        Integer,
        ForeignKey("threat_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    username = Column(
        String,
        nullable=False
    )

    action = Column(
        String,
        nullable=False
    )

    detail = Column(
        Text,
        default=""
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )