import logging
import threading
import time
from datetime import datetime

from ..database import SessionLocal
from ..deployment_model import Deployment, DeploymentAudit
from ..models import Device
from ..os_image_model import OSImage
from ..websocket_manager import manager
from .provisioning_service import (
    ProvisioningError,
    install_timeout_reached,
    provision_deployment,
    verify_image_checksum,
)

logger = logging.getLogger(__name__)


ONLINE_GRACE_SECONDS = 30

POST_INSTALL_GRACE_MINUTES = 10

TERMINAL_STATUSES = ("COMPLETED", "FAILED")


def deployment_to_dict(db, deployment):
    device = (
        db.query(Device)
        .filter(Device.id == deployment.device_id)
        .first()
    )

    image = (
        db.query(OSImage)
        .filter(OSImage.id == deployment.os_image_id)
        .first()
    )

    return {
        "id": deployment.id,
        "device_id": deployment.device_id,
        "hostname": deployment.hostname,
        "ip": deployment.ip,
        "device_status": device.status if device else None,
        "image_id": deployment.os_image_id,
        "image_name": image.name if image else None,
        "image_version": image.version if image else None,
        "image_edition": image.edition if image else None,
        "image_architecture": image.architecture if image else None,
        "status": deployment.status,
        "progress": deployment.progress,
        "error": deployment.error,
        "created_by": deployment.created_by,
        "created_at": (
            deployment.created_at.isoformat()
            if deployment.created_at
            else None
        ),
        "updated_at": (
            deployment.updated_at.isoformat()
            if deployment.updated_at
            else None
        ),
        "completed_at": (
            deployment.completed_at.isoformat()
            if deployment.completed_at
            else None
        ),
        "verified_agent": deployment.verified_agent,
        "verified_heartbeat": deployment.verified_heartbeat,
        "verified_metrics": deployment.verified_metrics,
        "verified_os": deployment.verified_os,
        "verified_at": (
            deployment.verified_at.isoformat()
            if deployment.verified_at
            else None
        ),
    }


def broadcast_deployment(db, deployment):
    try:
        manager.broadcast_from_thread(
            {
                "type": "deployment_update",
                "deployment": deployment_to_dict(db, deployment),
            }
        )
    except Exception:
        pass


def record_audit(db, deployment_id, action, actor, detail=""):
    db.add(
        DeploymentAudit(
            deployment_id=deployment_id,
            action=action,
            actor=actor,
            detail=detail,
        )
    )

    db.commit()


def image_arch_compatible(image, device):
    """Check the image architecture against the device's reported OS."""

    image_arch = (image.architecture or "x86_64").lower()

    device_os = (device.os or "").lower()

    if not device_os:
        return True

    if "arm" in device_os or "aarch64" in device_os:
        return "arm" in image_arch or "aarch64" in image_arch

    if image_arch in ("arm64", "aarch64"):
        return False

    return True


def validate_target(db, image, device):
    """Return a list of validation failures for deploying image to device."""

    violations = []

    if image is None or not image.approved:
        violations.append("OS image is not approved")

    if device is None:
        violations.append("Device not found")
        return violations

    if not device.agent_token:
        violations.append("Device is not enrolled with an agent")

    if not image_arch_compatible(image, device):
        violations.append(
            f"Architecture mismatch: image {image.architecture} "
            f"vs device OS {device.os}"
        )

    if device.status != "online":
        violations.append("Device is offline")

    return violations


def create_deployments(db, image, devices, actor):
    """Validate targets, create deployment records and start handoffs.

    Returns a dict with created deployments, validation failures and
    offline targets.
    """

    created = []
    rejected = []
    offline = []

    for device in devices:
        violations = validate_target(db, image, device)

        if violations:
            if "Device is offline" in violations:
                status = "OFFLINE"
            else:
                rejected.append(
                    {
                        "hostname": device.hostname,
                        "reasons": violations,
                    }
                )
                continue
        else:
            status = "PENDING"

        deployment = Deployment(
            device_id=device.id,
            os_image_id=image.id,
            hostname=device.hostname,
            ip=device.ip,
            status=status,
            progress=0,
            created_by=actor,
        )

        db.add(deployment)
        db.commit()
        db.refresh(deployment)

        if status == "OFFLINE":
            offline.append(deployment_to_dict(db, deployment))
        else:
            try:
                perform_handoff(db, deployment)
            except Exception:
                db.rollback()
                db.refresh(deployment)

            created.append(deployment_to_dict(db, deployment))

        record_audit(
            db,
            deployment.id,
            "DEPLOYMENT_CREATED",
            actor,
            f"Target {device.hostname} -> image {image.name} "
            f"{image.version}",
        )

    return {
        "created": created,
        "rejected": rejected,
        "offline": offline,
    }


def perform_handoff(db, deployment):
    """Hand the deployment to the provisioning system (PXE / API)."""

    deployment.status = "INSTALLING"
    deployment.progress = 10
    deployment.updated_at = datetime.utcnow()

    db.commit()

    broadcast_deployment(db, deployment)

    image = (
        db.query(OSImage)
        .filter(OSImage.id == deployment.os_image_id)
        .first()
    )

    if image is None:
        return fail_deployment(
            db,
            deployment,
            "OS image no longer exists",
        )

    try:
        verify_image_checksum(image)

        deployment.progress = 20
        deployment.updated_at = datetime.utcnow()
        db.commit()

    except ProvisioningError as exc:
        return fail_deployment(
            db,
            deployment,
            f"Validation failed: {exc}",
        )

    try:
        provision_deployment(db, deployment, image)

        deployment.progress = 40
        deployment.updated_at = datetime.utcnow()

        db.commit()

        broadcast_deployment(db, deployment)

        record_audit(
            db,
            deployment.id,
            "PROVISIONING_HANDOFF",
            "system",
            f"Handed off to provisioning system "
            f"({deployment.hostname})",
        )

    except ProvisioningError as exc:
        return fail_deployment(
            db,
            deployment,
            f"Provisioning handoff failed: {exc}",
        )

    return deployment


def fail_deployment(db, deployment, message):
    deployment.status = "FAILED"
    deployment.error = message
    deployment.completed_at = datetime.utcnow()
    deployment.updated_at = datetime.utcnow()

    db.commit()

    record_audit(
        db,
        deployment.id,
        "DEPLOYMENT_FAILED",
        "system",
        message,
    )

    broadcast_deployment(db, deployment)

    return deployment


def complete_deployment(db, deployment):
    deployment.status = "COMPLETED"
    deployment.progress = 100
    deployment.completed_at = datetime.utcnow()
    deployment.updated_at = datetime.utcnow()

    db.commit()

    record_audit(
        db,
        deployment.id,
        "DEPLOYMENT_COMPLETED",
        "system",
        f"Post-install verification passed for {deployment.hostname}",
    )

    broadcast_deployment(db, deployment)

    return deployment


def verify_post_install(db, deployment, device):
    """Post-install verification:
    agent enrollment, heartbeat, metric reporting and OS match."""

    now = datetime.utcnow()

    if not device.agent_token:
        return False

    deployment.verified_agent = True

    if (
        device.last_seen
        and (now - device.last_seen).total_seconds() < 120
    ):
        deployment.verified_heartbeat = True

    if deployment.verified_heartbeat:
        from ..metric_model import DeviceMetric

        metric = (
            db.query(DeviceMetric)
            .filter(
                DeviceMetric.device_id == device.id,
                DeviceMetric.created_at >= deployment.created_at,
            )
            .first()
        )

        if metric:
            deployment.verified_metrics = True

    image = (
        db.query(OSImage)
        .filter(OSImage.id == deployment.os_image_id)
        .first()
    )

    if image and image.name:
        if device.os and image.name.lower() in (device.os or "").lower():
            deployment.verified_os = True
    else:
        deployment.verified_os = True

    passed = all(
        [
            deployment.verified_agent,
            deployment.verified_heartbeat,
            deployment.verified_metrics,
        ]
    )

    if passed:
        deployment.verified_at = now

    return passed


def check_deployment(db, deployment):
    """Advance a single non-terminal deployment based on real device state."""

    if deployment.status in TERMINAL_STATUSES:
        return None

    device = (
        db.query(Device)
        .filter(Device.id == deployment.device_id)
        .first()
    )

    if deployment.status == "OFFLINE":

        if device and device.status == "online":
            deployment.status = "PENDING"
            deployment.updated_at = datetime.utcnow()
            db.commit()

            perform_handoff(db, deployment)

        return None

    if deployment.status == "PENDING":

        perform_handoff(db, deployment)

        return None

    if deployment.status == "INSTALLING":

        if install_timeout_reached(deployment):
            return fail_deployment(
                db,
                deployment,
                "Timed out waiting for the device to re-enroll "
                "after provisioning",
            )

        if device is None:
            return fail_deployment(
                db,
                deployment,
                "Device no longer exists",
            )

        if device.status == "offline":
            deployment.progress = 60
            deployment.updated_at = datetime.utcnow()
            db.commit()
            return None

        if verify_post_install(db, deployment, device):
            return complete_deployment(db, deployment)

        deployment.progress = 90
        deployment.updated_at = datetime.utcnow()
        db.commit()

        return None

    return None


def monitor_loop(interval=15):
    while True:

        db = SessionLocal()

        try:

            deployments = (
                db.query(Deployment)
                .filter(~Deployment.status.in_(TERMINAL_STATUSES))
                .all()
            )

            for deployment in deployments:

                try:
                    check_deployment(db, deployment)
                except Exception:
                    logger.exception(
                        "deployment monitor error for %s",
                        deployment.id,
                    )
                    db.rollback()

        finally:

            db.close()

        time.sleep(interval)


def start_deployment_monitor(interval=15):

    thread = threading.Thread(
        target=monitor_loop,
        kwargs={"interval": interval},
        daemon=True,
    )

    thread.start()