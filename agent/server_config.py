"""Admin-pushed agent configuration.

The agent fetches GET /agent/config (the settings an administrator maintains
under Settings > Agent Configuration) and applies the values on top of the
local environment. Every value is optional: unset server values keep the
agent's local setting, so an admin can push just what they want (usually the
LAN API URL and discovery ranges) without a per-machine file edit.
"""

import os
import threading
import time

import requests

API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

AGENT_TOKEN = os.getenv("SMARTIT_AGENT_TOKEN", "")

CONFIG_REFRESH_INTERVAL = int(
    os.getenv("SMARTIT_CONFIG_REFRESH_INTERVAL", "60")
)

_lock = threading.Lock()
_config = {}
_refresh_callback = None


def get(key, default=None):
    with _lock:
        return _config.get(key, default)


def set_refresh_callback(callback):
    global _refresh_callback
    _refresh_callback = callback


def _apply_env(values):
    """Mirror server values into the environment so env-driven readers
    (e.g. network discovery) pick them up. Empty values leave the local
    environment untouched."""
    global API_URL

    mapping = {
        "agent_api_url": "SMARTIT_API_URL",
        "metrics_interval_seconds": "SMARTIT_INTERVAL",
        "request_timeout_seconds": "SMARTIT_REQUEST_TIMEOUT",
        "activity_interval_seconds": "SMARTIT_ACTIVITY_INTERVAL",
        "software_poll_interval_seconds": "SMARTIT_SOFTWARE_POLL_INTERVAL",
        "web_access_poll_interval_seconds": "SMARTIT_WEB_ACCESS_POLL_INTERVAL",
        "deployment_poll_interval_seconds": "SMARTIT_DEPLOYMENT_POLL_INTERVAL",
        "discovery_interval_seconds": "SMARTIT_NETWORK_DISCOVERY_INTERVAL",
        "agent_reboot_cmd": "SMARTIT_REBOOT_CMD",
        "agent_department": "SMARTIT_DEPARTMENT",
        "agent_lab": "SMARTIT_LAB",
        "agent_location": "SMARTIT_LOCATION",
    }

    api_url = values.get("agent_api_url")

    if api_url:
        API_URL = str(api_url).rstrip("/")
        os.environ["SMARTIT_API_URL"] = API_URL

    ranges = values.get("network_ranges")

    if isinstance(ranges, list) and ranges:
        os.environ["SMARTIT_NETWORK_RANGES"] = ",".join(
            str(item) for item in ranges
        )

    for key, env_name in mapping.items():
        value = values.get(key)

        if value in (None, ""):
            continue

        os.environ[env_name] = str(value)


def refresh():
    """Fetch the server config once and apply it. Returns True on success."""
    global _config

    if not AGENT_TOKEN:
        return False

    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    try:
        response = requests.get(
            f"{API_URL}/agent/config",
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            return False

        values = response.json()

        with _lock:
            _config = dict(values)

        _apply_env(_config)

        callback = _refresh_callback

        if callback:
            try:
                callback()
            except Exception as exc:
                print(f"[SmartIT] Config apply callback error: {exc}")

        return True

    except Exception as exc:
        print(f"[SmartIT] Config refresh error: {exc}")
        return False


def start_refresh_thread():
    thread = threading.Thread(
        target=_refresh_loop,
        daemon=True,
        name="agent_config",
    )
    thread.start()
    return thread


def _refresh_loop():
    while True:
        time.sleep(CONFIG_REFRESH_INTERVAL)

        try:
            refresh()
        except Exception as exc:
            print(f"[SmartIT] Config refresh loop error: {exc}")
