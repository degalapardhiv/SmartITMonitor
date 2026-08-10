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
        severity=severity,
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
                    "type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "status": alert.status,
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
