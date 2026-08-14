import hashlib
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Device
from .software_deployment_model import (
    DeviceGroup,
    DeviceGroupMember,
    SoftwareDeployment,
    SoftwareDeploymentEvent,
    SoftwareDeploymentTarget,
)

PACKAGE_DIR = os.getenv(
    "SOFTWARE_PACKAGE_DIR",
    "/app/software_packages",
)

MAX_RETRY_ATTEMPTS = 3

TERMINAL_TARGET_STATUSES = {
    "completed",
    "failed",
    "cancelled",
}

ACTION_WHITELIST = {
    "install",
    "update",
    "uninstall",
    "enforce",
}

SCOPE_WHITELIST = {
    "all",
    "department",
    "lab",
    "location",
    "group",
    "selected",
}

ARCH_CANONICAL = {
    "x64": {"x64", "amd64", "x86_64", "x86-64"},
    "x86": {"x86", "i386", "i486", "i586", "i686", "32-bit"},
    "arm64": {"arm64", "aarch64"},
    "arm": {"arm", "armv7", "armv7l"},
}


def classify_os(raw):
    text = (raw or "").lower()

    if "windows" in text:
        return "windows"
    if "linux" in text:
        return "linux"
    if "darwin" in text or "macos" in text:
        return "macos"
    return ""


def classify_arch(raw):
    text = (raw or "").lower()

    for canonical, aliases in ARCH_CANONICAL.items():
        if text in aliases:
            return canonical

    if "64" in text:
        return "x64"
    if "86" in text:
        return "x86"

    return ""


def device_compatible(package, device):
    """Return (compatible, reason)."""

    if package.os:
        device_os = classify_os(device.os)
        if device_os != package.os:
            return (
                False,
                f"OS mismatch: package targets {package.os}, "
                f"device reports '{device.os or 'unknown'}'",
            )

    if package.architecture:
        device_arch = classify_arch(device.architecture)
        if device_arch != package.architecture:
            return (
                False,
                f"Architecture mismatch: package targets "
                f"{package.architecture}, device reports "
                f"'{device.architecture or 'unknown'}'",
            )

    return True, ""


def device_is_offline(device, timeout_seconds=60):
    if not device.last_seen:
        return True

    diff = (
        datetime.utcnow() - device.last_seen
    ).total_seconds()

    return diff > timeout_seconds


def _scope_devices(db: Session, scope, scope_ref, device_ids):
    query = db.query(Device)

    if scope == "all":
        pass

    elif scope in ("department", "lab", "location"):
        column = {
            "department": Device.department,
            "lab": Device.lab,
            "location": Device.location,
        }[scope]
        query = query.filter(column == scope_ref)

    elif scope == "group":
        group = (
            db.query(DeviceGroup)
            .filter(DeviceGroup.id == int(scope_ref))
            .first()
        )

        if not group:
            return []

        query = query.join(
            DeviceGroupMember,
            DeviceGroupMember.device_id == Device.id,
        ).filter(
            DeviceGroupMember.group_id == group.id
        )

    elif scope == "selected":
        if not device_ids:
            return []

        query = query.filter(Device.id.in_(device_ids))

    else:
        return []

    return query.all()


def resolve_targets(db: Session, package, scope, scope_ref, device_ids=None):
    """Resolve and validate target devices for a deployment."""

    from .settings_center_service import get_heartbeat_config

    timeout_seconds = get_heartbeat_config()["timeout_seconds"]

    devices = _scope_devices(db, scope, scope_ref, device_ids)

    targets = []
    summary = {
        "total": len(devices),
        "compatible": 0,
        "offline": 0,
        "incompatible": 0,
        "devices": [],
    }

    for device in devices:
        compatible, reason = device_compatible(package, device)

        offline = device_is_offline(device, timeout_seconds)

        entry = {
            "device_id": device.id,
            "hostname": device.hostname,
            "ip": device.ip,
            "os": device.os,
            "architecture": device.architecture,
            "compatible": compatible,
            "offline": offline,
            "reason": reason,
        }

        summary["devices"].append(entry)

        if not compatible:
            summary["incompatible"] += 1
            continue

        summary["compatible"] += 1

        if offline:
            summary["offline"] += 1

        targets.append(entry)

    return targets, summary


def broadcast_deployment_update(deployment_id):
    from .websocket_manager import manager

    try:
        manager.broadcast_from_thread(
            {
                "type": "software_deployment_update",
                "deployment_id": deployment_id,
            }
        )
    except Exception:
        pass


def add_event(
    db: Session,
    deployment_id,
    message,
    level="info",
    actor="",
    target_id=None,
    device_id=None,
):
    event = SoftwareDeploymentEvent(
        deployment_id=deployment_id,
        target_id=target_id,
        device_id=device_id,
        actor=actor,
        level=level,
        message=message,
    )

    db.add(event)
    db.commit()

    return event


def deployment_summary(db: Session, deployment_id):
    targets = (
        db.query(SoftwareDeploymentTarget)
        .filter(
            SoftwareDeploymentTarget.deployment_id == deployment_id
        )
        .all()
    )

    counts = {
        "pending": 0,
        "downloading": 0,
        "installing": 0,
        "completed": 0,
        "failed": 0,
        "offline": 0,
        "cancelled": 0,
        "total": len(targets),
    }

    for target in targets:
        status = (target.status or "pending").lower()

        if status in counts:
            counts[status] += 1

    return counts


def refresh_deployment_status(db: Session, deployment):
    counts = deployment_summary(db, deployment.id)

    active = sum(
        counts[status]
        for status in ("pending", "downloading", "installing", "offline")
    )

    if deployment.status == "cancelled":
        return deployment

    retryable = (
        db.query(SoftwareDeploymentTarget)
        .filter(
            SoftwareDeploymentTarget.deployment_id == deployment.id,
            SoftwareDeploymentTarget.status == "failed",
            SoftwareDeploymentTarget.attempt_count < MAX_RETRY_ATTEMPTS,
        )
        .count()
    )

    if active or retryable:
        deployment.status = "running"
    elif counts["failed"]:
        deployment.status = "failed"
    elif counts["completed"]:
        deployment.status = "completed"

    if deployment.status in ("completed", "failed", "cancelled"):
        deployment.completed_at = deployment.completed_at or datetime.utcnow()
    elif not deployment.started_at:
        deployment.started_at = datetime.utcnow()

    db.commit()

    return deployment


def package_file_path(package):
    return os.path.join(PACKAGE_DIR, f"{package.id}-{package.file_name}")


def sha256_file(path):
    digest = hashlib.sha256()

    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()
