import json
import os
import platform
import socket
import subprocess
import time

import requests


API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000",
)

DEVICE_ID = os.getenv("SMARTIT_DEVICE_ID", "")

AGENT_TOKEN = os.getenv(
    "SMARTIT_AGENT_TOKEN",
    "",
)


def linux_usb_devices():
    try:
        output = subprocess.check_output(
            ["lsusb"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []

    devices = []

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split(" ", 6)

        devices.append({
            "raw": line,
            "bus": parts[1] if len(parts) > 1 else None,
            "device": (
                parts[3].rstrip(":")
                if len(parts) > 3
                else None
            ),
            "description": (
                parts[6]
                if len(parts) > 6
                else line
            ),
        })

    return devices


def get_usb_devices():
    if platform.system().lower() == "linux":
        return linux_usb_devices()

    return []


def send_usb_event(device):
    if not DEVICE_ID:
        print("[SmartIT USB] DEVICE_ID not configured")
        return

    payload = {
        "device_id": int(DEVICE_ID),
        "usb_id": device.get("raw"),
        "vendor": device.get("description"),
        "product": device.get("description"),
        "description": device.get("description"),
    }

    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    try:
        response = requests.post(
            f"{API_URL}/usb/events",
            json=payload,
            headers=headers,
            timeout=10,
        )

        print(
            "[SmartIT USB] Event sent:",
            response.status_code,
        )

        if response.ok:
            try:
                print(
                    "[SmartIT USB] Request:",
                    json.dumps(response.json()),
                )
            except Exception:
                pass

    except requests.RequestException as exc:
        print(
            "[SmartIT USB] Backend error:",
            exc,
        )


def main():
    previous = {}

    print("[SmartIT USB] Monitor started")
    print("[SmartIT USB] Hostname:", socket.gethostname())

    while True:
        current_devices = {
            item["raw"]: item
            for item in get_usb_devices()
        }

        added = [
            current_devices[key]
            for key in current_devices
            if key not in previous
        ]

        removed = [
            previous[key]
            for key in previous
            if key not in current_devices
        ]

        for device in added:
            print(
                "[USB CONNECTED]",
                json.dumps(device),
            )
            send_usb_event(device)

        for device in removed:
            print(
                "[USB REMOVED]",
                json.dumps(device),
            )

        previous = current_devices
        time.sleep(2)


if __name__ == "__main__":
    main()
