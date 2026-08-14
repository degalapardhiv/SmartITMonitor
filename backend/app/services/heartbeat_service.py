import threading
import time
from datetime import datetime

from app.database import SessionLocal
from app.models import Device
from app.websocket_manager import manager


def _device_payload(device):
    return {
        "id": device.id,
        "hostname": device.hostname,
        "ip": device.ip,
    }


def check_devices():

    from app.settings_center_service import get_heartbeat_config

    while True:

        config = get_heartbeat_config()

        timeout_seconds = config["timeout_seconds"]
        interval_seconds = config["check_interval_seconds"]

        db = SessionLocal()

        try:

            devices = db.query(Device).all()

            now = datetime.utcnow()

            for device in devices:

                if not device.last_seen:
                    continue

                diff = (
                    now - device.last_seen
                ).total_seconds()

                if diff <= timeout_seconds and device.status != "online":

                    device.status = "online"

                    try:
                        manager.broadcast_from_thread(
                            {
                                "type": "device_online",
                                "device": _device_payload(device),
                            }
                        )
                    except Exception:
                        pass

                elif diff > timeout_seconds and device.status != "offline":

                    device.status = "offline"

                    try:
                        manager.broadcast_from_thread(
                            {
                                "type": "device_offline",
                                "device": _device_payload(device),
                            }
                        )
                    except Exception:
                        pass

            db.commit()

        except Exception:
            db.rollback()

        finally:
            db.close()

        time.sleep(interval_seconds)


def start_heartbeat():

    thread = threading.Thread(
        target=check_devices,
        daemon=True
    )

    thread.start()
