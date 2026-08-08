from sqlalchemy import Column, Integer, String, Boolean

from .database import Base


class SystemSetting(Base):

    __tablename__ = "system_settings"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    key = Column(
        String,
        unique=True
    )


    value = Column(
        Boolean,
        default=True
    )
