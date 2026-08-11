from sqlalchemy import Column, Integer, String

from .database import Base


class MonitorSetting(Base):

    __tablename__ = "monitor_settings"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    key = Column(
        String,
        unique=True,
        nullable=False
    )


    value = Column(
        String,
        nullable=False
    )