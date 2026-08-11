from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .database import Base


class OSImage(Base):

    __tablename__ = "os_images"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    name = Column(
        String,
        nullable=False
    )


    version = Column(
        String,
        default=""
    )


    edition = Column(
        String,
        default=""
    )


    architecture = Column(
        String,
        default="x86_64"
    )


    checksum = Column(
        String,
        default=""
    )


    checksum_type = Column(
        String,
        default="sha256"
    )


    kernel_path = Column(
        String,
        default=""
    )


    initrd_path = Column(
        String,
        default=""
    )


    kickstart_url = Column(
        String,
        default=""
    )


    approved = Column(
        Boolean,
        default=False
    )


    created_by = Column(
        String,
        default=""
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )