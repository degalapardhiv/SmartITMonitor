from datetime import datetime
import secrets
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Header,
)

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Device
from .metric_model import DeviceMetric
from .schemas import DeviceCreate, DeviceResponse, AgentRegister
from .websocket_manager import manager
from .services.alert_service import check_device_alert
from .services.network_scanner import scan_network
from .metrics import update_device_metrics as refresh_metrics_gauges
from .auth_dependency import get_current_user
from .role_dependency import require_admin
from .agent_auth import get_agent_device

router = APIRouter()


# ==========================================
# Database Session
# ==========================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ==========================================
# Home
# ==========================================

@router.get("/")
def home():

    return {
        "message": "Smart IT Monitor API Running",
        "version": "2.0.0"
    }


# ==========================================
# Dashboard
# ==========================================

@router.get("/dashboard")
def dashboard(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    devices = db.query(Device).all()

    total = len(devices)

    online = len(
        [
            d
            for d in devices
            if d.status and d.status.lower() == "online"
        ]
    )

    offline = total - online

    from .alert_model import Alert

    alerts = (
        db.query(Alert)
        .count()
    )

    departments = len(
        set(
            d.department
            for d in devices
            if d.department
        )
    )

    labs = len(
        set(
            d.lab
            for d in devices
            if d.lab
        )
    )


    total_alerts = db.query(Alert).count()


    open_alerts = (
        db.query(Alert)
        .filter(
            Alert.status == "OPEN"
        )
        .count()
    )


    resolved_alerts = (
        db.query(Alert)
        .filter(
            Alert.status == "RESOLVED"
        )
        .count()
    )


    critical_alerts = (
        db.query(Alert)
        .filter(
            Alert.severity == "HIGH"
        )
        .count()
    )

    from .threat_model import ThreatEvent

    threat_items = (
        db.query(ThreatEvent)
        .filter(
            ThreatEvent.status.in_(
                ("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")
            )
        )
        .count()
    )

    critical_threats = (
        db.query(ThreatEvent)
        .filter(
            ThreatEvent.severity == "CRITICAL",
            ThreatEvent.status.in_(
                ("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")
            ),
        )
        .count()
    )

    quarantined_threats = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.status == "QUARANTINED")
        .count()
    )

    threat_devices = len(
        set(
            t.device_id
            for t in db.query(ThreatEvent.device_id)
            .filter(
                ThreatEvent.status.in_(
                    ("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")
                )
            )
            .all()
        )
    )

    recent_threats = (
        db.query(ThreatEvent)
        .filter(
            ThreatEvent.status.in_(
                ("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")
            )
        )
        .order_by(ThreatEvent.detected_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "alerts": alerts,
        "total_alerts": total_alerts,
        "open_alerts": open_alerts,
        "resolved_alerts": resolved_alerts,
        "critical_alerts": critical_alerts,
        "departments": departments,
        "labs": labs,
        "threat_stats": {
            "active_threats": threat_items,
            "critical_threats": critical_threats,
            "quarantined_threats": quarantined_threats,
            "devices_affected": threat_devices,
        },
        "recent_threats": [
            {
                "id": t.id,
                "hostname": t.hostname,
                "file_name": t.file_name,
                "category": t.category,
                "severity": t.severity,
                "status": t.status,
                "detected_at": t.detected_at.isoformat()
                if t.detected_at
                else None,
            }
            for t in recent_threats
        ],
    }

# ==========================================
# Get All Devices
# ==========================================

@router.get("/devices", response_model=list[DeviceResponse])
def get_devices(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return (
        db.query(Device)
        .order_by(Device.hostname)
        .all()
    )

# ==========================================
# Get One Device
# ==========================================

@router.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    return device


# ==========================================
# Add or Update Device
# ==========================================

@router.post("/devices")
async def add_device(
    device: DeviceCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    existing = (
        db.query(Device)
        .filter(Device.hostname == device.hostname)
        .first()
    )

    # -----------------------------
    # Update Existing Device
    # -----------------------------

    if existing:

        existing.ip = device.ip

        existing.cpu = device.cpu
        existing.ram = device.ram
        existing.disk = device.disk

        existing.status = device.status.lower()

        existing.department = device.department
        existing.lab = device.lab
        existing.location = device.location
        existing.os = device.os

        db.commit()
        db.refresh(existing)

        metric = DeviceMetric(
            device_id=existing.id,
            cpu=existing.cpu,
            ram=existing.ram,
            disk=existing.disk
        )

        db.add(metric)
        db.commit()

        await manager.broadcast(
            {
                "type": "device_update",
                "device": {
                    "id": existing.id,
                    "hostname": existing.hostname,
                    "ip": existing.ip,
                    "cpu": existing.cpu,
                    "ram": existing.ram,
                    "disk": existing.disk,
                    "status": existing.status
                }
            }
        )

        return existing

    # -----------------------------
    # Create New Device
    # -----------------------------

    new_device = Device(
        hostname=device.hostname,
        ip=device.ip,

        cpu=device.cpu,
        ram=device.ram,
        disk=device.disk,

        status=device.status.lower(),

        department=device.department,
        lab=device.lab,
        location=device.location,
        os=device.os
    )

    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    metric = DeviceMetric(
        device_id=new_device.id,
        cpu=new_device.cpu,
        ram=new_device.ram,
        disk=new_device.disk
    )

    db.add(metric)
    db.commit()

    await manager.broadcast(
        {
            "type": "device_update",
            "device": {
                "id": new_device.id,
                "hostname": new_device.hostname,
                "ip": new_device.ip,
                "cpu": new_device.cpu,
                "ram": new_device.ram,
                "disk": new_device.disk,
                "status": new_device.status
            }
        }
    )


    check_device_alert(
        new_device,
        db
    )


    return new_device


# ==========================================
# Update Device
# ==========================================

@router.put("/devices/{device_id}")
async def update_device(
    device_id: int,
    updated: DeviceCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    device.hostname = updated.hostname
    device.ip = updated.ip

    device.cpu = updated.cpu
    device.ram = updated.ram
    device.disk = updated.disk

    device.status = updated.status.lower()

    device.department = updated.department
    device.lab = updated.lab
    device.location = updated.location
    device.os = updated.os

    db.commit()
    db.refresh(device)

    metric = DeviceMetric(
        device_id=device.id,
        cpu=device.cpu,
        ram=device.ram,
        disk=device.disk
    )

    db.add(metric)
    db.commit()

    await manager.broadcast(
        {
            "type": "device_update",
            "device": {
                "id": device.id,
                "hostname": device.hostname,
                "ip": device.ip,
                "cpu": device.cpu,
                "ram": device.ram,
                "disk": device.disk,
                "status": device.status
            }
        }
    )


    check_device_alert(
        device,
        db
    )


    return device


# ==========================================
# Delete Device
# ==========================================

@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    hostname = device.hostname

    from sqlalchemy import text as sa_text
    for child_table in (
        "alerts",
        "deployments",
        "endpoint_activity",
        "software_deployment_events",
        "usb_requests",
        "web_access_sync_logs",
    ):
        db.execute(
            sa_text(f"DELETE FROM {child_table} WHERE device_id = :device_id"),
            {"device_id": device_id},
        )

    db.delete(device)
    db.commit()

    await manager.broadcast(
        {
            "type": "device_deleted",
            "hostname": hostname
        }
    )

    return {
        "message": "Device deleted successfully"
    }

# ==========================================
# Device Metrics History
# ==========================================

@router.get("/devices/{device_id}/metrics")
def get_device_metrics(
    device_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )

    metrics = (
        db.query(DeviceMetric)
        .filter(DeviceMetric.device_id == device_id)
        .order_by(DeviceMetric.created_at.desc())
        .limit(100)
        .all()
    )

    return metrics


# ==========================================
# Device Metrics Update (Agent)
# ==========================================

@router.post("/devices/{device_id}/metrics")
async def update_device_metrics(
    device_id: int,
    cpu: float,
    ram: float,
    disk: float,
    x_agent_token: str = Header(...),
    db: Session = Depends(get_db)
):

    device = (
        db.query(Device)
        .filter(Device.id == device_id)
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )


    if device.agent_token is None or device.agent_token != x_agent_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid agent token"
        )


    device.cpu = cpu
    device.ram = ram
    device.disk = disk
    device.last_seen = datetime.utcnow()
    device.status = "online"


    metric = DeviceMetric(
        device_id=device_id,
        cpu=cpu,
        ram=ram,
        disk=disk
    )


    db.add(metric)
    db.commit()


    await manager.broadcast(
        {
            "type": "device_update",
            "device": {
                "id": device.id,
                "hostname": device.hostname,
                "ip": device.ip,
                "status": device.status,
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "last_seen": device.last_seen.isoformat()
            }
        }
    )


    return {
        "status": "updated",
        "device_id": device_id
    }



# ==========================================
# Agent Registration
# ==========================================

@router.post("/agent/register")
def agent_register(
    data: AgentRegister,
    db: Session = Depends(get_db)
):

    existing = (
        db.query(Device)
        .filter(Device.hostname == data.hostname)
        .first()
    )


    if existing:

        if not existing.agent_token:
            existing.agent_token = secrets.token_hex(16)
            db.commit()

        return {
            "device_id": existing.id,
            "agent_token": existing.agent_token
        }


    # Adopt a scan-discovered device with the same IP instead of creating
    # a duplicate record (prevents dupes when a scan ran before the agent).
    by_ip = (
        db.query(Device)
        .filter(
            Device.ip == data.ip,
            Device.agent_token.is_(None),
        )
        .first()
    )

    if by_ip:

        by_ip.hostname = data.hostname
        by_ip.os = data.os
        by_ip.agent_token = secrets.token_hex(16)

        if data.department:
            by_ip.department = data.department
        if data.lab:
            by_ip.lab = data.lab
        if data.location:
            by_ip.location = data.location

        db.commit()
        db.refresh(by_ip)

        return {
            "device_id": by_ip.id,
            "agent_token": by_ip.agent_token
        }


    token = secrets.token_hex(16)


    device = Device(
        hostname=data.hostname,
        ip=data.ip,
        os=data.os,
        status="online",
        cpu=0,
        ram=0,
        disk=0,
        department=data.department or "Unknown",
        lab=data.lab or "Unknown",
        location=data.location or "Unknown",
        agent_token=token
    )


    db.add(device)
    db.commit()
    db.refresh(device)


    return {
        "device_id": device.id,
        "agent_token": token
    }


# ==========================================
# Agent Configuration (admin-pushed settings)
# ==========================================

@router.get("/agent/config")
def agent_config(
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    """Agent endpoint: admin-configured settings for all agents.

    Administrators set these in Settings > Agent Configuration. Agents poll
    this endpoint and apply the returned values (server URL, network ranges,
    polling intervals, etc.) automatically.
    """
    from app.settings_center_service import get_agent_config

    return get_agent_config(db)


@router.post("/agent/attributes")
def agent_attributes(
    payload: dict,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    """Agent endpoint: apply admin-pushed device attributes.

    Agents send department/lab/location from the Agent Configuration section
    so endpoints inherit the site's defaults without per-machine edits.
    """
    device = (
        db.query(Device)
        .filter(Device.id == agent_device["id"])
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    updated = {}

    for field in ("department", "lab", "location"):
        value = (payload or {}).get(field)

        if not value:
            continue

        value = str(value).strip()

        if value and getattr(device, field, None) != value:
            setattr(device, field, value)
            updated[field] = value

    if updated:
        db.commit()
        db.refresh(device)

    return {"device_id": device.id, "updated": updated}


# ==========================================
# WebSocket
# ==========================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    from app.settings_center_service import get_ws_ping_interval

    import asyncio

    await manager.connect(websocket)

    try:

        await websocket.send_json({
            "type": "connected"
        })

        while True:

            ping_interval = get_ws_ping_interval()

            try:

                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=ping_interval,
                )

            except asyncio.TimeoutError:

                await websocket.send_json({
                    "type": "ping"
                })

    except WebSocketDisconnect:

        manager.disconnect(websocket)


    except Exception:

        manager.disconnect(websocket)




@router.post("/scan")
def scan_devices(
    network: str = "",
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    if not network:

        from .services.settings_service import get_scan_ranges

        ranges = get_scan_ranges(db)

        if ranges:

            network = ranges[0]

        else:

            network = "192.168.1.0/24"

    devices = scan_network(network)

    saved = []

    for item in devices:

        device = db.query(Device).filter(
            Device.ip == item["ip"]
        ).first()


        if device:

            device.status = item["status"].lower()
            device.hostname = item["hostname"]
            device.os = item["os"]

        else:

            device = Device(
                hostname=item["hostname"],
                ip=item["ip"],
                status=item["status"].lower(),
                os=item["os"]
            )

            db.add(device)


        saved.append(item)


    db.commit()

    all_devices = db.query(Device).all()

    refresh_metrics_gauges(all_devices)

    return {
        "scanned": len(saved),
        "devices": saved
    }



# ==========================================
# Telegram Notification Settings
# ==========================================

from app.notification_config import TELEGRAM_ENABLED
from .settings_model import SystemSetting
import app.notification_config as notification_config


@router.get("/settings/telegram")
def telegram_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    setting = (
        db.query(SystemSetting)
        .filter(
            SystemSetting.key == "telegram"
        )
        .first()
    )


    if setting is None:

        setting = SystemSetting(
            key="telegram",
            value=True
        )

        db.add(setting)
        db.commit()

        enabled = True

    else:

        enabled = setting.value


    return {
        "telegram_enabled": enabled
    }



@router.post("/settings/telegram")
def update_telegram_status(
    enabled: bool,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    setting = (
        db.query(SystemSetting)
        .filter(
            SystemSetting.key == "telegram"
        )
        .first()
    )


    if setting:

        setting.value = enabled

    else:

        setting = SystemSetting(
            key="telegram",
            value=enabled
        )

        db.add(setting)


    db.commit()


    return {
        "telegram_enabled": enabled
    }


# ==========================================
# Email Notification Settings
# ==========================================

@router.get("/settings/email")
def email_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    setting = (
        db.query(SystemSetting)
        .filter(
            SystemSetting.key == "email"
        )
        .first()
    )


    if setting:

        enabled = setting.value

    else:

        enabled = False


    return {
        "email_enabled": enabled
    }



@router.post("/settings/email")
def update_email_status(
    enabled: bool,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    setting = (
        db.query(SystemSetting)
        .filter(
            SystemSetting.key == "email"
        )
        .first()
    )


    if setting:

        setting.value = enabled

    else:

        setting = SystemSetting(
            key="email",
            value=enabled
        )

        db.add(setting)


    db.commit()


    return {
        "email_enabled": enabled
    }


# ==========================================
# SMTP Email Configuration
# ==========================================

from .email_settings_model import EmailSetting
from pydantic import BaseModel


class EmailConfigPayload(BaseModel):
    smtp_server: str
    smtp_port: int
    username: str
    receiver: str
    password: str = ""


@router.get("/settings/email/config")
def get_email_config(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    config = db.query(
        EmailSetting
    ).first()


    if not config:

        return {
            "configured": False
        }


    return {
        "configured": True,
        "smtp_server": config.smtp_server,
        "smtp_port": config.smtp_port,
        "username": config.username,
        "receiver": config.receiver
    }



@router.post("/settings/email/config")
def save_email_config(
    payload: EmailConfigPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    config = db.query(
        EmailSetting
    ).first()


    password = payload.password


    if config:

        if not password:

            password = config.password

        config.smtp_server = payload.smtp_server
        config.smtp_port = payload.smtp_port
        config.username = payload.username
        config.password = password
        config.receiver = payload.receiver

    else:

        config = EmailSetting(
            smtp_server=payload.smtp_server,
            smtp_port=payload.smtp_port,
            username=payload.username,
            password=password,
            receiver=payload.receiver
        )

        db.add(config)


    db.commit()


    return {
        "status":"saved"
    }


@router.delete("/settings/email/config")
def reset_email_config(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    config = db.query(
        EmailSetting
    ).first()


    if config:

        db.delete(config)

        db.commit()


    return {
        "status": "reset",
        "configured": False
    }


from app.services.email_service import send_email


# ==========================================
# Email History
# ==========================================

from app.email_history_model import EmailHistory


@router.get("/settings/email/history")
def email_history(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return (
        db.query(EmailHistory)
        .order_by(
            EmailHistory.created_at.desc()
        )
        .limit(100)
        .all()
    )


@router.post("/settings/test-telegram")
def test_telegram(
    current_user=Depends(require_admin),
):

    from app.services.telegram_service import send_telegram

    send_telegram(
        "Smart IT Monitor Telegram Test Alert"
    )

    return {
        "status":"telegram test sent"
    }



@router.post("/settings/test-email")
def test_email(
    current_user=Depends(require_admin),
):

    from app.services.email_service import send_email

    sent = send_email(
        "Smart IT Monitor Test",
        "Email test notification"
    )

    if not sent:

        raise HTTPException(
            status_code=502,
            detail="Email sending failed. Check SMTP configuration.",
        )

    return {
        "status":"email test sent"
    }


# ==========================================
# Monitor Settings (thresholds, scan ranges)
# ==========================================

from .services.settings_service import (
    get_alert_thresholds,
    save_alert_thresholds,
    get_scan_ranges,
    save_scan_ranges,
)


class ThresholdPayload(BaseModel):
    cpu_threshold: int
    ram_threshold: int
    disk_threshold: int
    alert_cooldown_minutes: int
    scan_ranges: list = None


class ScanRangesPayload(BaseModel):
    ranges: list


@router.get("/settings/monitor")
def get_monitor_settings(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    thresholds = get_alert_thresholds(db)

    return {
        "cpu_threshold": thresholds["cpu_threshold"],
        "ram_threshold": thresholds["ram_threshold"],
        "disk_threshold": thresholds["disk_threshold"],
        "alert_cooldown_minutes": thresholds["alert_cooldown_minutes"],
        "scan_ranges": get_scan_ranges(db),
    }


@router.put("/settings/monitor")
def update_monitor_settings(
    payload: ThresholdPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    for name, value in {
        "cpu_threshold": payload.cpu_threshold,
        "ram_threshold": payload.ram_threshold,
        "disk_threshold": payload.disk_threshold,
        "alert_cooldown_minutes": payload.alert_cooldown_minutes,
    }.items():

        if value < 1 or value > 1000:

            raise HTTPException(
                status_code=400,
                detail=f"{name} must be between 1 and 1000",
            )

    save_alert_thresholds(
        db,
        payload.cpu_threshold,
        payload.ram_threshold,
        payload.disk_threshold,
        payload.alert_cooldown_minutes,
    )

    ranges = payload.scan_ranges

    if ranges is not None:

        from ipaddress import ip_network

        clean = []

        for item in ranges:

            raw = item.strip() if isinstance(item, str) else ""

            if not raw:
                continue

            try:
                ip_network(raw, strict=False)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid network range: {raw}",
                )

            clean.append(raw)

        save_scan_ranges(db, clean)

    return {
        "thresholds": get_alert_thresholds(db),
        "scan_ranges": get_scan_ranges(db),
    }


@router.put("/settings/monitor/ranges")
def update_scan_ranges(
    payload: ScanRangesPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):

    from ipaddress import ip_network

    clean = []

    for item in payload.ranges:

        raw = item.strip() if isinstance(item, str) else ""

        if not raw:
            continue

        try:
            ip_network(raw, strict=False)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid network range: {raw}",
            )

        clean.append(raw)

    saved = save_scan_ranges(db, clean)

    return {
        "scan_ranges": saved,
    }


@router.get("/notifications/analytics")
def notification_analytics(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    from app.notification_history_model import NotificationHistory
    from sqlalchemy import func


    total = (
        db.query(NotificationHistory)
        .count()
    )


    sent = (
        db.query(NotificationHistory)
        .filter(
            NotificationHistory.status=="SENT"
        )
        .count()
    )


    failed = (
        db.query(NotificationHistory)
        .filter(
            NotificationHistory.status=="FAILED"
        )
        .count()
    )


    telegram = (
        db.query(NotificationHistory)
        .filter(
            NotificationHistory.channel=="Telegram"
        )
        .count()
    )


    email = (
        db.query(NotificationHistory)
        .filter(
            NotificationHistory.channel=="Email"
        )
        .count()
    )


    return {

        "total": total,
        "sent": sent,
        "failed": failed,
        "telegram": telegram,
        "email": email

    }
