import os
import sys
import threading
import time
import socket
import platform
import requests
import psutil

sys.path.insert(
    0,
    os.path.dirname(os.path.abspath(__file__)),
)

from network.network_monitor import run_discovery_once

API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000"
)

AGENT_TOKEN = os.getenv(
    "SMARTIT_AGENT_TOKEN",
    ""
)

DEVICE_ID = os.getenv("SMARTIT_DEVICE_ID", "")
INTERVAL = int(os.getenv("SMARTIT_INTERVAL", "5"))
NETWORK_DISCOVERY_INTERVAL = int(
    os.getenv("SMARTIT_NETWORK_DISCOVERY_INTERVAL", "300")
)


def collect_metrics():
    return {
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "cpu": round(psutil.cpu_percent(interval=1), 2),
        "ram": round(psutil.virtual_memory().percent, 2),
        "disk": round(
            psutil.disk_usage(os.path.abspath(os.sep)).percent,
            2
        ),
    }


def send_metrics():
    metrics = collect_metrics()

    url = f"{API_URL}/devices/{DEVICE_ID}/metrics"

    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    try:
        response = requests.post(
            url,
            params={
                "cpu": metrics["cpu"],
                "ram": metrics["ram"],
                "disk": metrics["disk"],
            },
            headers=headers,
            timeout=10,
        )

        print(
            f"[SmartIT] {metrics['hostname']} "
            f"CPU={metrics['cpu']}% "
            f"RAM={metrics['ram']}% "
            f"DISK={metrics['disk']}% "
            f"HTTP={response.status_code}"
        )

    except Exception as exc:
        print(f"[SmartIT] ERROR: {exc}")


def main():
    if not DEVICE_ID:
        raise SystemExit(
            "SMARTIT_DEVICE_ID is required"
        )

    print("[SmartIT] Agent started")
    print(f"[SmartIT] API: {API_URL}")
    print(f"[SmartIT] Device ID: {DEVICE_ID}")
    print(f"[SmartIT] Interval: {INTERVAL}s")

    try:
        network_thread = threading.Thread(
            target=_network_discovery_loop,
            daemon=True,
        )
        network_thread.start()
        print("[SmartIT] Network discovery thread started")
    except Exception as exc:
        print(f"[SmartIT] Network discovery unavailable: {exc}")

    while True:
        send_metrics()
        time.sleep(INTERVAL)


def _network_discovery_loop():
    while True:
        try:
            run_discovery_once()
        except Exception as exc:
            print(f"[SmartIT] Network discovery cycle error: {exc}")
        time.sleep(NETWORK_DISCOVERY_INTERVAL)


if __name__ == "__main__":
    main()
