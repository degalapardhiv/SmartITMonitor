from datetime import datetime

from sqlalchemy import (
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


class SoftwarePackage(Base):

    __tablename__ = "software_packages"


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
        nullable=False
    )


    publisher = Column(
        String,
        default=""
    )


    os = Column(
        String,
        default="windows"
    )


    architecture = Column(
        String,
        default=""
    )


    file_name = Column(
        String,
        default=""
    )


    file_size = Column(
        Integer,
        default=0
    )


    checksum = Column(
        String,
        default=""
    )


    checksum_type = Column(
        String,
        default="sha256"
    )


    install_command = Column(
        String,
        default=""
    )


    uninstall_command = Column(
        String,
        default=""
    )


    verify_command = Column(
        String,
        default=""
    )


    install_timeout_seconds = Column(
        Integer,
        default=600
    )


    approval_status = Column(
        String,
        default="pending"
    )


    approved_by = Column(
        String,
        default=""
    )


    notes = Column(
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


    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            name="uq_software_package_name_version"
        ),
        Index(
            "ix_software_packages_approval",
            "approval_status",
        ),
    )


class SoftwareInventory(Base):

    __tablename__ = "software_inventory"


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


    name = Column(
        String,
        nullable=False
    )


    version = Column(
        String,
        default=""
    )


    publisher = Column(
        String,
        default=""
    )


    install_date = Column(
        DateTime,
        default=datetime.utcnow
    )


    updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "name",
            name="uq_software_inventory_device_name"
        ),
    )


class SoftwareDeployment(Base):

    __tablename__ = "software_deployments"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    package_id = Column(
        Integer,
        ForeignKey("software_packages.id"),
        nullable=False,
        index=True
    )


    action = Column(
        String,
        default="install"
    )


    scope = Column(
        String,
        default="all"
    )


    scope_ref = Column(
        String,
        default=""
    )


    status = Column(
        String,
        default="pending"
    )


    created_by = Column(
        String,
        default=""
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


    started_at = Column(
        DateTime,
        nullable=True
    )


    completed_at = Column(
        DateTime,
        nullable=True
    )


class SoftwareDeploymentTarget(Base):

    __tablename__ = "software_deployment_targets"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    deployment_id = Column(
        Integer,
        ForeignKey("software_deployments.id", ondelete="CASCADE"),
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


    progress = Column(
        Integer,
        default=0
    )


    detail = Column(
        Text,
        default=""
    )


    attempt_count = Column(
        Integer,
        default=0
    )


    next_retry_at = Column(
        DateTime,
        nullable=True
    )


    started_at = Column(
        DateTime,
        nullable=True
    )


    completed_at = Column(
        DateTime,
        nullable=True
    )


    __table_args__ = (
        Index(
            "ix_software_targets_device_status",
            "device_id",
            "status",
        ),
    )


class SoftwareDeploymentEvent(Base):

    __tablename__ = "software_deployment_events"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    deployment_id = Column(
        Integer,
        ForeignKey("software_deployments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )


    target_id = Column(
        Integer,
        nullable=True
    )


    device_id = Column(
        Integer,
        nullable=True
    )


    actor = Column(
        String,
        default=""
    )


    level = Column(
        String,
        default="info"
    )


    message = Column(
        Text,
        default=""
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class DeviceGroup(Base):

    __tablename__ = "device_groups"


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


    created_by = Column(
        String,
        default=""
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class DeviceGroupMember(Base):

    __tablename__ = "device_group_members"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    group_id = Column(
        Integer,
        ForeignKey("device_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )


    device_id = Column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )


    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "device_id",
            name="uq_device_group_member",
        ),
    )
