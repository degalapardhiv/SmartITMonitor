from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .agent_auth import get_agent_device
from .auth_dependency import get_current_user
from .database import SessionLocal
from .network_device_model import NetworkDevice
from .role_dependency import require_admin


router = APIRouter(
    prefix="/network",
    tags=["Network Discovery"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DiscoveredDevice(BaseModel):
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    interface: Optional[str] = None
    network: Optional[str] = None


class DiscoveryPayload(BaseModel):
    devices: list[DiscoveredDevice]


@router.post("/discovery")
def submit_discovery(
    payload: DiscoveryPayload,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    """
    Receive discovery results from an enrolled SmartITMonitor agent.

    Discovery is associated with the authenticated agent's device.
    """

    now = datetime.now(timezone.utc)
    results = []

    for item in payload.devices:
        device = None

        if item.mac:
            device = (
                db.query(NetworkDevice)
                .filter(
                    NetworkDevice.mac == item.mac
                )
                .first()
            )

        if device is None:
            device = (
                db.query(NetworkDevice)
                .filter(
                    NetworkDevice.ip == item.ip
                )
                .first()
            )

        if device is None:
            device = NetworkDevice(
                ip=item.ip,
                mac=item.mac,
                hostname=item.hostname,
                vendor=item.vendor,
                interface=item.interface,
                network=item.network,
                managed=False,
                status="online",
                first_seen=now,
                last_seen=now,
            )

            db.add(device)

        else:
            device.ip = item.ip
            device.mac = item.mac or device.mac
            device.hostname = (
                item.hostname or device.hostname
            )
            device.vendor = (
                item.vendor or device.vendor
            )
            device.interface = (
                item.interface or device.interface
            )
            device.network = (
                item.network or device.network
            )
            device.status = "online"
            device.last_seen = now

        results.append(device)

    db.commit()

    for device in results:
        db.refresh(device)

    return {
        "success": True,
        "agent_device_id": int(agent_device["id"]),
        "discovered": len(results),
        "devices": [
            {
                "id": device.id,
                "ip": device.ip,
                "mac": device.mac,
                "hostname": device.hostname,
                "vendor": device.vendor,
                "interface": device.interface,
                "network": device.network,
                "managed": device.managed,
                "status": device.status,
                "last_seen": device.last_seen,
            }
            for device in results
        ],
    }


@router.get("/devices")
def get_network_devices(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = (
        db.query(NetworkDevice)
        .order_by(NetworkDevice.last_seen.desc())
        .all()
    )

    return [
        {
            "id": device.id,
            "ip": device.ip,
            "mac": device.mac,
            "hostname": device.hostname,
            "vendor": device.vendor,
            "interface": device.interface,
            "network": device.network,
            "managed": device.managed,
            "status": device.status,
            "first_seen": device.first_seen,
            "last_seen": device.last_seen,
        }
        for device in devices
    ]


@router.get("/summary")
def network_summary(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(NetworkDevice).all()

    return {
        "total": len(devices),
        "online": sum(
            1
            for device in devices
            if device.status == "online"
        ),
        "managed": sum(
            1
            for device in devices
            if device.managed
        ),
        "unknown": sum(
            1
            for device in devices
            if not device.managed
        ),
    }


@router.post("/devices/{device_id}/managed")
def set_managed(
    device_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    device = (
        db.query(NetworkDevice)
        .filter(NetworkDevice.id == device_id)
        .first()
    )

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Network device not found",
        )

    device.managed = True

    db.commit()
    db.refresh(device)

    return {
        "success": True,
        "id": device.id,
        "managed": device.managed,
    }
