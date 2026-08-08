import psutil
import threading
import time

from app.metrics import (
    CPU_USAGE,
    RAM_USAGE,
)


def collect_system_metrics():

    while True:

        CPU_USAGE.set(
            psutil.cpu_percent(interval=1)
        )

        RAM_USAGE.set(
            psutil.virtual_memory().percent
        )

        time.sleep(10)



def start_metrics_thread():

    thread = threading.Thread(
        target=collect_system_metrics,
        daemon=True
    )

    thread.start()
