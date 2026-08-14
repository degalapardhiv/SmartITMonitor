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
    os.getenv("SMARTIT_NETWORK_DISCOVERY_INTERVAL", "60")
)
REBOOT_CMD = os.getenv(
    "SMARTIT_REBOOT_CMD",
    "",
).strip()
DEPLOYMENT_POLL_INTERVAL = int(
    os.getenv("SMARTIT_DEPLOYMENT_POLL_INTERVAL", "15")
)

ACTIVITY_INTERVAL = int(os.getenv("SMARTIT_ACTIVITY_INTERVAL", "30"))

ACTIVITY_CONFIG_REFRESH_INTERVAL = int(
    os.getenv("SMARTIT_ACTIVITY_CONFIG_INTERVAL", "300")
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


def poll_pending_deployment():
    """Check for a pending OS deployment and hand off to provisioning.

    The backend marks the deployment INSTALLING once the agent accepts.
    When SMARTIT_REBOOT_CMD is configured (e.g. "systemctl reboot"),
    the agent performs the real reboot so the machine net-boots into
    the provisioning system. Without it, the agent only acknowledges
    the handoff and the backend will fail the deployment on timeout.
    """

    url = f"{API_URL}/deployments/agent/pending"

    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return

        pending = response.json()

        if not pending:
            return

        deployment_id = pending.get("id")

        image = pending.get("image", {})

        print(
            f"[SmartIT] Deployment {deployment_id} pending: "
            f"{image.get('name', '')} {image.get('version', '')}"
        )

        ack_url = f"{API_URL}/deployments/{deployment_id}/agent-ack"

        ack = requests.post(ack_url, headers=headers, timeout=10)

        print(
            f"[SmartIT] Deployment {deployment_id} acknowledged "
            f"HTTP={ack.status_code}"
        )

        if not REBOOT_CMD:
            print(
                f"[SmartIT] Deployment {deployment_id}: "
                "reboot disabled (set SMARTIT_REBOOT_CMD to enable). "
                "Machine will not net-boot into provisioning."
            )
            return

        import subprocess

        result = subprocess.run(
            REBOOT_CMD,
            shell=True,
            timeout=30,
        )

        print(
            f"[SmartIT] Reboot command exit code: {result.returncode}"
        )

    except Exception as exc:
        print(f"[SmartIT] Deployment poll error: {exc}")


def _deployment_loop():
    while True:
        try:
            poll_pending_deployment()
        except Exception as exc:
            print(f"[SmartIT] Deployment poll cycle error: {exc}")
        time.sleep(DEPLOYMENT_POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Endpoint activity collection
# ---------------------------------------------------------------------------

_activity_config = {
    "url_auditing": False,
    "interval_seconds": ACTIVITY_INTERVAL,
    "fetched_at": 0.0,
}


def _refresh_activity_config():
    global ACTIVITY_INTERVAL

    now = time.time()

    if now - _activity_config["fetched_at"] < ACTIVITY_CONFIG_REFRESH_INTERVAL:
        return _activity_config

    url = f"{API_URL}/endpoint-activity/agent/config"

    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            _activity_config["url_auditing"] = bool(
                data.get("url_auditing", False)
            )
            interval = int(data.get("interval_seconds", ACTIVITY_INTERVAL) or 60)
            _activity_config["interval_seconds"] = max(10, interval)
            ACTIVITY_INTERVAL = _activity_config["interval_seconds"]
            _activity_config["fetched_at"] = now
    except Exception as exc:
        print(f"[SmartIT] Activity config refresh error: {exc}")

    return _activity_config


def _activity_loop():
    from activity import collectors

    while True:
        try:
            config = _refresh_activity_config()

            collectors.set_url_auditing(config["url_auditing"])

            events = collectors.collect_all()

            if events:
                url = f"{API_URL}/endpoint-activity"

                headers = {}

                if AGENT_TOKEN:
                    headers["x-agent-token"] = AGENT_TOKEN

                response = requests.post(
                    url,
                    json={"events": events},
                    headers=headers,
                    timeout=15,
                )

                if response.status_code >= 400:
                    print(
                        f"[SmartIT] Activity submit HTTP={response.status_code} "
                        f"{response.text[:200]}"
                    )
        except Exception as exc:
            print(f"[SmartIT] Activity cycle error: {exc}")

        time.sleep(ACTIVITY_INTERVAL)


def start_activity_collector():
    thread = threading.Thread(
        target=_activity_loop,
        daemon=True,
        name="endpoint_activity",
    )
    thread.start()
    return thread


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

    try:
        deployment_thread = threading.Thread(
            target=_deployment_loop,
            daemon=True,
        )
        deployment_thread.start()
        print("[SmartIT] Deployment poll thread started")
    except Exception as exc:
        print(f"[SmartIT] Deployment poll unavailable: {exc}")

    try:
        activity_thread = start_activity_collector()
        print("[SmartIT] Endpoint activity thread started")
    except Exception as exc:
        print(f"[SmartIT] Endpoint activity unavailable: {exc}")

    try:
        from software_deployment import start_software_deployment

        start_software_deployment()
        print("[SmartIT] Software deployment thread started")
    except Exception as exc:
        print(f"[SmartIT] Software deployment unavailable: {exc}")

    try:
        from web_access import start_web_access

        start_web_access()
        print("[SmartIT] Web access control thread started")
    except Exception as exc:
        print(f"[SmartIT] Web access control unavailable: {exc}")

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
