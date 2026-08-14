from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .database import Base


class WebAccessPolicy(Base):

    __tablename__ = "web_access_policies"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    name = Column(
        String,
        unique=True,
        nullable=False
    )


    description = Column(
        Text,
        default=""
    )


    action = Column(
        String,
        default="blocklist"
    )


    enabled = Column(
        Boolean,
        default=True
    )


    version = Column(
        Integer,
        default=1
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


class WebAccessDomainEntry(Base):

    __tablename__ = "web_access_domain_entries"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    policy_id = Column(
        Integer,
        ForeignKey("web_access_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )


    domain = Column(
        String,
        nullable=False
    )


    include_subdomains = Column(
        Boolean,
        default=False
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "domain",
            name="uq_web_access_policy_domain"
        ),
    )


class WebAccessTarget(Base):

    __tablename__ = "web_access_targets"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    policy_id = Column(
        Integer,
        ForeignKey("web_access_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )


    target_type = Column(
        String,
        default="all"
    )


    target_ref = Column(
        String,
        default=""
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class WebAccessPolicyDevice(Base):

    __tablename__ = "web_access_policy_devices"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    policy_id = Column(
        Integer,
        ForeignKey("web_access_policies.id", ondelete="CASCADE"),
        nullable=False,
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
        default=""
    )


    status = Column(
        String,
        default="pending"
    )


    applied_version = Column(
        Integer,
        default=0
    )


    detail = Column(
        Text,
        default=""
    )


    applied_at = Column(
        DateTime,
        nullable=True
    )


    last_synced_at = Column(
        DateTime,
        nullable=True
    )


    __table_args__ = (
        UniqueConstraint(
            "policy_id",
            "device_id",
            name="uq_web_access_policy_device"
        ),
        Index(
            "ix_web_access_policy_devices_status",
            "policy_id",
            "status",
        ),
    )


class WebAccessSyncLog(Base):

    __tablename__ = "web_access_sync_logs"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    policy_id = Column(
        Integer,
        nullable=True,
        index=True
    )


    device_id = Column(
        Integer,
        nullable=True,
        index=True
    )


    hostname = Column(
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
