from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .agent_auth import get_agent_device
from .auth_dependency import get_current_user
from .database import SessionLocal
from .deployment_model import Deployment, DeploymentAudit
from .models import Device
from .os_image_model import OSImage
from .role_dependency import require_admin


router = APIRouter(
    prefix="/deployments",
    tags=["OS Deployment"],
)


class DeployPayload(BaseModel):
    os_image_id: int
    target_type: str = "all"
    target_value: str = ""
    device_ids: list[int] = []


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def audit_to_dict(entry):
    return {
        "id": entry.id,
        "deployment_id": entry.deployment_id,
        "action": entry.action,
        "actor": entry.actor,
        "detail": entry.detail,
        "created_at": (
            entry.created_at.isoformat()
            if entry.created_at
            else None
        ),
    }


def _resolve_target_devices(db, payload):
    query = db.query(Device)

    target_type = payload.target_type or "all"

    if target_type == "department":
        if not payload.target_value:
            raise HTTPException(
                status_code=400,
                detail="Department is required",
            )
        query = query.filter(
            Device.department == payload.target_value
        )

    elif target_type == "lab":
        if not payload.target_value:
            raise HTTPException(
                status_code=400,
                detail="Lab is required",
            )
        query = query.filter(Device.lab == payload.target_value)

    elif target_type == "location":
        if not payload.target_value:
            raise HTTPException(
                status_code=400,
                detail="Location is required",
            )
        query = query.filter(
            Device.location == payload.target_value
        )

    elif target_type == "selected":
        if not payload.device_ids:
            raise HTTPException(
                status_code=400,
                detail="Select at least one computer",
            )
        query = query.filter(Device.id.in_(payload.device_ids))

    elif target_type != "all":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target type: {target_type}",
        )

    return query.all()


@router.get("")
def list_deployments(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from .services.deployment_service import deployment_to_dict

    deployments = (
        db.query(Deployment)
        .order_by(Deployment.created_at.desc())
        .limit(200)
        .all()
    )

    return [deployment_to_dict(db, d) for d in deployments]


@router.get("/summary")
def deployment_summary(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Deployment.status,
        )
        .all()
    )

    counts = {
        "PENDING": 0,
        "INSTALLING": 0,
        "COMPLETED": 0,
        "FAILED": 0,
        "OFFLINE": 0,
    }

    for (status,) in rows:
        counts[status] = counts.get(status, 0) + 1

    return counts


@router.get("/audit")
def deployment_audit_log(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = (
        db.query(DeploymentAudit)
        .order_by(DeploymentAudit.created_at.desc())
        .limit(100)
        .all()
    )

    return [audit_to_dict(entry) for entry in entries]


@router.post("")
def create_deployment(
    payload: DeployPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    image = (
        db.query(OSImage)
        .filter(OSImage.id == payload.os_image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=404,
            detail="OS image not found",
        )

    if not image.approved:
        raise HTTPException(
            status_code=400,
            detail="Only approved OS images can be deployed",
        )

    devices = _resolve_target_devices(db, payload)

    if not devices:
        raise HTTPException(
            status_code=400,
            detail="No target computers matched the selection",
        )

    from .services.deployment_service import create_deployments

    result = create_deployments(
        db,
        image,
        devices,
        current_user["username"],
    )

    db.rollback()

    return result


@router.post("/{deployment_id}/retry")
def retry_deployment(
    deployment_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    from .services.deployment_service import (
        deployment_to_dict,
        perform_handoff,
        record_audit,
    )

    deployment = (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id)
        .first()
    )

    if not deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    device = (
        db.query(Device)
        .filter(Device.id == deployment.device_id)
        .first()
    )

    if device is None or not device.agent_token:
        raise HTTPException(
            status_code=400,
            detail="Device is not enrolled with an agent",
        )

    if device.status != "online":
        raise HTTPException(
            status_code=400,
            detail="Device is offline — retry when it is back online",
        )

    deployment.status = "PENDING"
    deployment.progress = 0
    deployment.error = ""
    deployment.updated_at = None
    deployment.completed_at = None
    deployment.verified_agent = False
    deployment.verified_heartbeat = False
    deployment.verified_metrics = False
    deployment.verified_os = False
    deployment.verified_at = None

    db.commit()

    record_audit(
        db,
        deployment.id,
        "DEPLOYMENT_RETRIED",
        current_user["username"],
        f"Retried deployment for {deployment.hostname}",
    )

    perform_handoff(db, deployment)

    db.refresh(deployment)

    return deployment_to_dict(db, deployment)


@router.get("/agent/pending")
def agent_pending_deployment(
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    deployment = (
        db.query(Deployment)
        .filter(
            Deployment.device_id == agent_device["id"],
            Deployment.status == "PENDING",
        )
        .order_by(Deployment.created_at.asc())
        .first()
    )

    if not deployment:
        return None

    image = (
        db.query(OSImage)
        .filter(OSImage.id == deployment.os_image_id)
        .first()
    )

    return {
        "id": deployment.id,
        "hostname": deployment.hostname,
        "image": {
            "name": image.name if image else "",
            "version": image.version if image else "",
            "edition": image.edition if image else "",
            "architecture": image.architecture if image else "",
        },
    }


@router.post("/{deployment_id}/agent-ack")
def agent_ack_deployment(
    deployment_id: int,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    deployment = (
        db.query(Deployment)
        .filter(
            Deployment.id == deployment_id,
            Deployment.device_id == agent_device["id"],
        )
        .first()
    )

    if not deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found for this device",
        )

    from .services.deployment_service import (
        deployment_to_dict,
        perform_handoff,
        record_audit,
    )

    if deployment.status == "PENDING":
        record_audit(
            db,
            deployment.id,
            "AGENT_ACCEPTED",
            agent_device["hostname"],
            "Agent accepted deployment and will reboot into provisioning",
        )

        perform_handoff(db, deployment)

    return deployment_to_dict(db, deployment)