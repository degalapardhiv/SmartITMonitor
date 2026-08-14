import socket
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..camera_model import Camera
from ..alert_model import Alert
from ..database import SessionLocal
from ..websocket_manager import manager
from .telegram_service import send_telegram
from .email_service import send_email
from .settings_service import get_alert_thresholds

DEFAULT_CHECK_INTERVAL = 60


def _camera_port(camera):
    try:
        if camera.stream_url:
            parsed = urlparse(camera.stream_url)

            if parsed.port:
                return parsed.port

            if parsed.scheme == "rtsp":
                return 554

            if parsed.scheme in ("http", "https"):
                return 80 if parsed.scheme == "http" else 443

    except Exception:
        pass

    return 554


def probe_camera(camera, timeout=3):
    port = _camera_port(camera)

    try:
        with socket.create_connection(
            (camera.ip, port),
            timeout=timeout,
        ):
            return True
    except Exception:
        return False


def resolve_camera_alerts(db: Session, camera):
    open_alerts = (
        db.query(Alert)
        .filter(
            Alert.device_id == camera.id,
            Alert.alert_type == "CAMERA_OFFLINE",
            Alert.status == "OPEN",
        )
        .all()
    )

    if not open_alerts:
        return []

    now = datetime.utcnow()

    for alert in open_alerts:
        alert.status = "RESOLVED"
        alert.resolved_at = now
        alert.message = f"Camera back online: {camera.name}"

    db.commit()

    for alert in open_alerts:
        db.refresh(alert)

    try:
        manager.broadcast_from_thread(
            {
                "type": "alert_resolved",
                "alerts": [
                    {
                        "id": alert.id,
                        "device_id": alert.device_id,
                        "hostname": alert.hostname,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "message": alert.message,
                        "status": alert.status,
                        "value": alert.value,
                        "created_at": alert.created_at.isoformat()
                        if alert.created_at
                        else None,
                        "resolved_at": alert.resolved_at.isoformat()
                        if alert.resolved_at
                        else None,
                    }
                    for alert in open_alerts
                ],
            }
        )
    except Exception:
        pass

    return open_alerts


def create_camera_alert(db: Session, camera):
    thresholds = get_alert_thresholds(db)

    cooldown_minutes = thresholds["alert_cooldown_minutes"]

    cooldown_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)

    existing = (
        db.query(Alert)
        .filter(
            Alert.device_id == camera.id,
            Alert.alert_type == "CAMERA_OFFLINE",
            Alert.status == "OPEN",
            Alert.created_at >= cooldown_time
        )
        .first()
    )

    if existing:
        return None

    alert = Alert(
        device_id=camera.id,
        hostname=camera.name,
        alert_type="CAMERA_OFFLINE",
        value=None,
        severity="HIGH",
        message=f"Camera offline: {camera.name} ({camera.ip})",
        status="OPEN",
        created_at=datetime.utcnow(),
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    try:
        manager.broadcast_from_thread(
            {
                "type": "alert",
                "alert": {
                    "id": alert.id,
                    "device_id": alert.device_id,
                    "hostname": alert.hostname,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "status": alert.status,
                    "value": alert.value,
                    "created_at": alert.created_at.isoformat(),
                },
            }
        )
    except Exception:
        pass

    try:
        send_telegram(
            f"Smart IT Monitor Alert\n"
            f"Camera: {camera.name}\n"
            f"IP: {camera.ip}\n"
            f"Status: OFFLINE",
            alert_id=alert.id,
        )
    except Exception:
        pass

    try:
        send_email(
            f"Smart IT Monitor Alert: Camera Offline - {camera.name}",
            f"Camera: {camera.name}\n"
            f"IP: {camera.ip}\n"
            f"Location: {camera.location}\n"
            f"Status: OFFLINE",
            alert_id=alert.id,
        )
    except Exception:
        pass

    return alert


def check_camera(db: Session, camera, force=False, probe_timeout=3):
    was_online = camera.status == "online"

    online = probe_camera(camera, timeout=probe_timeout)

    if online:

        camera.status = "online"
        camera.last_seen = datetime.utcnow()

        db.commit()

        if not was_online:
            resolve_camera_alerts(db, camera)

        return None

    camera.status = "offline"
    db.commit()

    if was_online or force:
        return create_camera_alert(db, camera)

    return None


def monitor_cameras(interval=DEFAULT_CHECK_INTERVAL):
    from app.settings_center_service import get_camera_config

    while True:

        config = get_camera_config()

        interval = config["check_interval_seconds"]
        probe_timeout = config["probe_timeout_seconds"]

        db = SessionLocal()

        try:

            cameras = db.query(Camera).all()

            for camera in cameras:

                try:
                    check_camera(
                        db,
                        camera,
                        probe_timeout=probe_timeout,
                    )
                except Exception:
                    db.rollback()

        finally:

            db.close()

        time.sleep(interval)


def start_camera_monitor(interval=DEFAULT_CHECK_INTERVAL):
    thread = threading.Thread(
        target=monitor_cameras,
        kwargs={"interval": interval},
        daemon=True,
    )

    thread.start()