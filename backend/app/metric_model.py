from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from datetime import datetime

from .database import Base


class DeviceMetric(Base):
    __tablename__ = "device_metrics"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False
    )

    cpu = Column(
        Float,
        nullable=False
    )

    ram = Column(
        Float,
        nullable=False
    )

    disk = Column(
        Float,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
