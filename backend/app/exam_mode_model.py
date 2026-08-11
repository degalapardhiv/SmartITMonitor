from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from .database import Base


class USBRequest(Base):
    __tablename__ = "usb_requests"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(Integer, nullable=False)

    usb_id = Column(String, nullable=True)
    vendor = Column(String, nullable=True)
    product = Column(String, nullable=True)
    description = Column(String, nullable=True)

    status = Column(String, nullable=False)

    requested_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)


class ExamModeSetting(Base):
    __tablename__ = "exam_mode_settings"

    id = Column(Integer, primary_key=True, index=True)

    enabled = Column(
        Boolean,
        default=False,
        nullable=False,
    )
    usb_policy = Column(
        String,
        default="approval_required",
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
