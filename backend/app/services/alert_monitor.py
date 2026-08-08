from app.database import SessionLocal
from app.models import Device
from app.alert_model import Alert
from app.services.telegram_service import send_telegram

import threading
import time
from datetime import datetime, timedelta


CPU_LIMIT = 90
RAM_LIMIT = 90
DISK_LIMIT = 90


def check_alerts():

    while True:

        db = SessionLocal()

        try:

            devices = db.query(Device).all()

            for device in devices:


                if device.cpu and device.cpu > CPU_LIMIT:
                    create_alert(
                        db,
                        device,
                        "CPU",
                        device.cpu
                    )


                if device.ram and device.ram > RAM_LIMIT:
                    create_alert(
                        db,
                        device,
                        "RAM",
                        device.ram
                    )


                if device.disk and device.disk > DISK_LIMIT:
                    create_alert(
                        db,
                        device,
                        "DISK",
                        device.disk
                    )


        finally:
            db.close()


        time.sleep(30)



def create_alert(db, device, alert_type, value):

    cooldown_time = datetime.utcnow() - timedelta(minutes=5)

    existing = (
        db.query(Alert)
        .filter(
            Alert.device_id == device.id,
            Alert.alert_type == alert_type,
            Alert.created_at >= cooldown_time
        )
        .first()
    )

    if existing:
        return


    alert = Alert(

        device_id=device.id,
        hostname=device.hostname,
        alert_type=alert_type,
        value=value,
        message=f"{alert_type} usage high: {value}%",
        severity="HIGH"

    )


    db.add(alert)
    db.commit()

    send_telegram(
        f"Smart IT Monitor Alert\n"
        f"Device: {device.hostname}\n"
        f"Type: {alert_type}\n"
        f"Value: {value}%\n"
        f"Severity: HIGH"
    )


def start_alert_monitor():

    thread = threading.Thread(
        target=check_alerts,
        daemon=True
    )

    thread.start()
