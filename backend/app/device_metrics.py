import threading
import time

from app.database import SessionLocal
from app.models import Device

from app.metrics import (
    DEVICE_COUNT,
    ONLINE_DEVICES,
    CPU_USAGE,
    RAM_USAGE,
    DISK_USAGE
)


def collect_device_metrics():

    while True:

        db = SessionLocal()

        try:

            devices = db.query(Device).all()

            DEVICE_COUNT.set(len(devices))

            online = 0
            cpu_total = 0
            ram_total = 0
            disk_total = 0

            for device in devices:

                if str(device.status).lower() in ["up", "online"]:
                    online += 1

                cpu_total += device.cpu or 0
                ram_total += device.ram or 0
                disk_total += device.disk or 0


            count = len(devices) or 1

            ONLINE_DEVICES.set(online)

            CPU_USAGE.set(cpu_total / count)

            RAM_USAGE.set(ram_total / count)

            DISK_USAGE.set(disk_total / count)


        finally:

            db.close()


        time.sleep(15)



def start_device_metrics():

    thread = threading.Thread(
        target=collect_device_metrics,
        daemon=True
    )

    thread.start()
