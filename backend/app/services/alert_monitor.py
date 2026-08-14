from app.database import SessionLocal
from app.models import Device
from app.services.alert_service import check_device_alert

import threading
import time


def check_alerts():

    from app.settings_center_service import get_alert_monitor_interval

    while True:

        interval = get_alert_monitor_interval()

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

        time.sleep(interval)


def start_alert_monitor():

    thread = threading.Thread(
        target=check_alerts,
        daemon=True
    )

    thread.start()
