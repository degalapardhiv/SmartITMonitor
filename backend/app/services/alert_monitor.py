from app.database import SessionLocal
from app.models import Device
from app.services.alert_service import check_device_alert

import threading
import time


def check_alerts():

    while True:

        db = SessionLocal()

        try:

            devices = db.query(Device).all()

            for device in devices:

                try:
                    check_device_alert(device, db)
                except Exception:
                    db.rollback()

        finally:
            db.close()

        time.sleep(30)


def start_alert_monitor():

    thread = threading.Thread(
        target=check_alerts,
        daemon=True
    )

    thread.start()
