from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..alert_model import Alert
from ..websocket_manager import manager
from .telegram_service import send_telegram
from .email_service import send_email
from .settings_service import get_alert_thresholds


def create_alert(db: Session, device, alert_type, value, severity, message):

    thresholds = get_alert_thresholds(db)

    cooldown_minutes = thresholds["alert_cooldown_minutes"]

    cooldown_time = datetime.utcnow() - timedelta(
        minutes=cooldown_minutes
    )

    existing = (
        db.query(Alert)
        .filter(
            Alert.device_id == device.id,
            Alert.alert_type == alert_type,
            Alert.status == "OPEN",
            Alert.created_at >= cooldown_time
        )
        .first()
    )

    if existing:
        return None

    alert = Alert(
        device_id=device.id,
        hostname=device.hostname,
        alert_type=alert_type,
        value=value,
        severity=severity.upper(),
        message=message,
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
            f"Device: {device.hostname}\n"
            f"Type: {alert_type}\n"
            f"Value: {value}%\n"
            f"Severity: {severity.upper()}",
            alert_id=alert.id,
        )
    except Exception:
        pass

    try:
        send_email(
            f"Smart IT Monitor Alert: {alert_type} - {device.hostname}",
            f"Device: {device.hostname}\n"
            f"Type: {alert_type}\n"
            f"Value: {value}%\n"
            f"Severity: {severity.upper()}\n"
            f"Message: {message}",
            alert_id=alert.id,
        )
    except Exception:
        pass

    return alert


def resolve_recovered_alert(db: Session, device, alert_type, value, message):
    """Auto-resolve OPEN alerts once the metric drops back below threshold."""

    open_alerts = (
        db.query(Alert)
        .filter(
            Alert.device_id == device.id,
            Alert.alert_type == alert_type,
            Alert.status == "OPEN",
        )
        .all()
    )

    if not open_alerts:
        return None

    now = datetime.utcnow()

    for alert in open_alerts:
        alert.status = "RESOLVED"
        alert.resolved_at = now
        alert.message = message

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
                        "created_at": alert.created_at.isoformat(),
                        "resolved_at": alert.resolved_at.isoformat(),
                    }
                    for alert in open_alerts
                ],
            }
        )
    except Exception:
        pass

    return open_alerts


def check_device_alert(device, db: Session):

    alerts = []

    thresholds = get_alert_thresholds(db)

    cpu_threshold = thresholds["cpu_threshold"]
    ram_threshold = thresholds["ram_threshold"]
    disk_threshold = thresholds["disk_threshold"]

    if device.cpu and device.cpu > cpu_threshold:
        alert = create_alert(
            db,
            device,
            "CPU",
            device.cpu,
            "HIGH",
            f"High CPU usage: {device.cpu}%",
        )
        if alert:
            alerts.append(alert)
    elif device.cpu:
        resolved_alerts = resolve_recovered_alert(
            db,
            device,
            "CPU",
            device.cpu,
            f"CPU usage recovered: {device.cpu}%",
        )
        if resolved_alerts:
            alerts.extend(resolved_alerts)

    if device.ram and device.ram > ram_threshold:
        alert = create_alert(
            db,
            device,
            "RAM",
            device.ram,
            "HIGH",
            f"High RAM usage: {device.ram}%",
        )
        if alert:
            alerts.append(alert)
    elif device.ram:
        resolved_alerts = resolve_recovered_alert(
            db,
            device,
            "RAM",
            device.ram,
            f"RAM usage recovered: {device.ram}%",
        )
        if resolved_alerts:
            alerts.extend(resolved_alerts)

    if device.disk and device.disk > disk_threshold:
        alert = create_alert(
            db,
            device,
            "DISK",
            device.disk,
            "HIGH",
            f"High DISK usage: {device.disk}%",
        )
        if alert:
            alerts.append(alert)
    elif device.disk:
        resolved_alerts = resolve_recovered_alert(
            db,
            device,
            "DISK",
            device.disk,
            f"Disk usage recovered: {device.disk}%",
        )
        if resolved_alerts:
            alerts.extend(resolved_alerts)

    return alerts
