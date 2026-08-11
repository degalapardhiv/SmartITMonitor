from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.alert_model import Alert
from app.websocket_manager import manager


def create_lab_alert(
    db: Session,
    *,
    device_id: int,
    hostname: str,
    alert_type: str,
    severity: str,
    message: str,
    value=None,
):
    alert = Alert(
        device_id=device_id,
        hostname=hostname,
        alert_type=alert_type,
        value=value,
        severity=severity.upper(),
        message=message,
        status="OPEN",
        created_at=datetime.now(timezone.utc),
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
    except Exception as exc:
        print(
            "[LabAlert] WebSocket broadcast failed:",
            exc,
        )

    return alert


def resolve_lab_alert(
    db: Session,
    *,
    device_id: int,
    alert_type: str,
    message: str,
):
    """Resolve OPEN lab alerts matching the device/type/message when a USB
    request is decided (approved or rejected)."""

    open_alerts = (
        db.query(Alert)
        .filter(
            Alert.device_id == device_id,
            Alert.alert_type == alert_type,
            Alert.status == "OPEN",
            Alert.message == message,
        )
        .all()
    )

    if not open_alerts:
        return None

    now = datetime.now(timezone.utc)

    for alert in open_alerts:
        alert.status = "RESOLVED"
        alert.resolved_at = now

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
    except Exception as exc:
        print(
            "[LabAlert] WebSocket resolve broadcast failed:",
            exc,
        )

    return open_alerts
