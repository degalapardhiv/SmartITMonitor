from sqlalchemy import Column, Integer, String

from .database import Base


class SettingsAudit(Base):

    __tablename__ = "settings_audit"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    username = Column(
        String,
        nullable=False
    )


    role = Column(
        String,
        nullable=False
    )


    action = Column(
        String,
        nullable=False
    )


    section = Column(
        String,
        nullable=False
    )


    key = Column(
        String,
        nullable=False
    )


    old_value = Column(
        String,
        nullable=True
    )


    new_value = Column(
        String,
        nullable=True
    )


    ip = Column(
        String,
        nullable=True
    )


    created_at = Column(
        String,
        nullable=False
    )
