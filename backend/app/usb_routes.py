from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from .database import SessionLocal
from .auth_dependency import get_current_user
from .agent_auth import get_agent_device
from .services.lab_alert_service import create_lab_alert

router = APIRouter(prefix="/usb", tags=["USB Approval"])


class USBEvent(BaseModel):
    device_id: int
    usb_id: Optional[str] = None
    vendor: Optional[str] = None
    product: Optional[str] = None
    description: Optional[str] = None


class USBDecision(BaseModel):
    decision: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/events")
def create_usb_event(
    event: USBEvent,
    agent_device=Depends(get_agent_device),
    db=Depends(get_db),
):
    if int(agent_device["id"]) != int(event.device_id):
        raise HTTPException(
            status_code=403,
            detail="Agent cannot submit events for another device",
        )

    device = db.execute(
        text("""
            SELECT id, hostname
            FROM devices
            WHERE id = :device_id
        """),
        {"device_id": event.device_id},
    ).mappings().first()

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    policy = db.execute(
        text("""
            SELECT enabled, usb_policy
            FROM exam_mode_settings
            WHERE id = 1
        """)
    ).mappings().first()

    exam_enabled = bool(policy["enabled"]) if policy else False
    usb_policy = (
        policy["usb_policy"]
        if policy
        else "approval_required"
    )

    if exam_enabled and usb_policy == "allow":
        request_status = "approved"
    elif exam_enabled and usb_policy == "block":
        request_status = "rejected"
    else:
        request_status = "pending"

    result = db.execute(
        text("""
            INSERT INTO usb_requests (
                device_id,
                usb_id,
                vendor,
                product,
                description,
                status
            )
            VALUES (
                :device_id,
                :usb_id,
                :vendor,
                :product,
                :description,
                :status
            )
            RETURNING
                id,
                device_id,
                usb_id,
                vendor,
                product,
                description,
                status,
                requested_at,
                reviewed_at,
                reviewed_by
        """),
        {
            "device_id": event.device_id,
            "usb_id": event.usb_id,
            "vendor": event.vendor,
            "product": event.product,
            "description": event.description,
            "status": request_status,
        },
    )

    request = dict(result.mappings().first())
    db.commit()


    if request_status == "pending":
        create_lab_alert(
            db,
            device_id=event.device_id,
            hostname=device["hostname"],
            alert_type="USB_PENDING",
            severity="HIGH",
            message=(
                f"USB approval required on {device['hostname']}: "
                f"{event.description or event.usb_id or 'Unknown USB'}"
            ),
        )

    elif request_status == "rejected":
        create_lab_alert(
            db,
            device_id=event.device_id,
            hostname=device["hostname"],
            alert_type="USB_REJECTED",
            severity="HIGH",
            message=(
                f"USB rejected by Exam Mode policy on "
                f"{device['hostname']}: "
                f"{event.description or event.usb_id or 'Unknown USB'}"
            ),
        )

    return request


@router.get("/requests")
def get_usb_requests(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    result = db.execute(
        text("""
            SELECT
                id,
                device_id,
                usb_id,
                vendor,
                product,
                description,
                status,
                requested_at,
                reviewed_at,
                reviewed_by
            FROM usb_requests
            ORDER BY requested_at DESC
        """)
    )

    return [dict(row) for row in result.mappings().all()]


@router.post("/requests/{request_id}/decision")
def decide_usb_request(
    request_id: int,
    decision: USBDecision,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    value = decision.decision.strip().lower()

    if value not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be approved or rejected",
        )

    request = db.execute(
        text("""
            SELECT id, status
            FROM usb_requests
            WHERE id = :request_id
        """),
        {"request_id": request_id},
    ).mappings().first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="USB request not found",
        )

    if request["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail="USB request has already been reviewed",
        )

    username = (
        current_user.get("username")
        or current_user.get("sub")
        or "admin"
    )

    reviewed_at = datetime.now(timezone.utc)

    result = db.execute(
        text("""
            UPDATE usb_requests
            SET
                status = :status,
                reviewed_at = :reviewed_at,
                reviewed_by = :reviewed_by
            WHERE id = :request_id
            RETURNING
                id,
                device_id,
                usb_id,
                vendor,
                product,
                description,
                status,
                requested_at,
                reviewed_at,
                reviewed_by
        """),
        {
            "status": value,
            "reviewed_at": reviewed_at,
            "reviewed_by": username,
            "request_id": request_id,
        },
    )

    updated = dict(result.mappings().first())
    db.commit()

    return updated
