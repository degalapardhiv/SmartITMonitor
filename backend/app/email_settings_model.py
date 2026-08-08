from sqlalchemy import Column, Integer, String

from .database import Base


class EmailSetting(Base):

    __tablename__ = "email_settings"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    smtp_server = Column(
        String
    )


    smtp_port = Column(
        Integer
    )


    username = Column(
        String
    )


    password = Column(
        String
    )


    receiver = Column(
        String
    )
