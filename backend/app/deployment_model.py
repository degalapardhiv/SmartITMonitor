from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from .database import Base


class Deployment(Base):

    __tablename__ = "deployments"


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


    os_image_id = Column(
        Integer,
        index=True,
        nullable=False
    )


    hostname = Column(
        String,
        default=""
    )


    ip = Column(
        String,
        default=""
    )


    status = Column(
        String,
        default="PENDING"
    )


    progress = Column(
        Integer,
        default=0
    )


    error = Column(
        Text,
        default=""
    )


    created_by = Column(
        String,
        default=""
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    completed_at = Column(
        DateTime,
        nullable=True
    )


    verified_agent = Column(
        Boolean,
        default=False
    )


    verified_heartbeat = Column(
        Boolean,
        default=False
    )


    verified_metrics = Column(
        Boolean,
        default=False
    )


    verified_os = Column(
        Boolean,
        default=False
    )


    verified_at = Column(
        DateTime,
        nullable=True
    )


class DeploymentAudit(Base):

    __tablename__ = "deployment_audit"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    deployment_id = Column(
        Integer,
        index=True
    )


    action = Column(
        String,
        default=""
    )


    actor = Column(
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