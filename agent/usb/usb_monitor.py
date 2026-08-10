import json
import platform
import subprocess
import time


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
            "device": parts[3].rstrip(":")
                if len(parts) > 3 else None,
            "description": parts[6]
                if len(parts) > 6 else line,
        })

    return devices


def get_usb_devices():
    system = platform.system().lower()

    if system == "linux":
        return linux_usb_devices()

    return []


def main():
    previous = {}

    print("[SmartIT USB] Monitor started")

    while True:
        current_devices = get_usb_devices()

        current = {
            item["raw"]: item
            for item in current_devices
        }

        added = [
            current[key]
            for key in current
            if key not in previous
        ]

        removed = [
            previous[key]
            for key in previous
            if key not in current
        ]

        for device in added:
            print(
                "[USB CONNECTED]",
                json.dumps(device)
            )

        for device in removed:
            print(
                "[USB REMOVED]",
                json.dumps(device)
            )

        previous = current
        time.sleep(2)


if __name__ == "__main__":
    main()
