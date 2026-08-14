import hashlib
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

import requests

API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000"
)

AGENT_TOKEN = os.getenv(
    "SMARTIT_AGENT_TOKEN",
    ""
)

SOFTWARE_POLL_INTERVAL = int(
    os.getenv("SMARTIT_SOFTWARE_POLL_INTERVAL", "30")
)

CACHE_DIR = os.getenv(
    "SMARTIT_SOFTWARE_CACHE",
    os.path.join(tempfile.gettempdir(), "smartit-software"),
)

MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024

VERSION_RE = re.compile(
    r"(\d+\.\d+(?:\.\d+)*[a-zA-Z0-9._\-]*)"
)


def _headers():
    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    return headers


def _report_device_info():
    import platform

    try:
        response = requests.post(
            f"{API_URL}/software/agent/device-info",
            json={
                "os": platform.platform(),
                "architecture": platform.machine(),
            },
            headers=_headers(),
            timeout=10,
        )

        return response.status_code == 200

    except Exception as exc:
        print(f"[SmartIT] Software device-info error: {exc}")
        return False


def _fetch_work():
    response = requests.get(
        f"{API_URL}/software/agent/work",
        headers=_headers(),
        timeout=15,
    )

    if response.status_code != 200:
        return []

    return response.json().get("jobs", [])


def _post_status(target_id, status, progress, detail):
    try:
        requests.post(
            f"{API_URL}/software/agent/status",
            json={
                "target_id": target_id,
                "status": status,
                "progress": progress,
                "detail": detail,
            },
            headers=_headers(),
            timeout=15,
        )
    except Exception as exc:
        print(f"[SmartIT] Software status error: {exc}")


def _post_result(target_id, success, version, detail):
    try:
        requests.post(
            f"{API_URL}/software/agent/result",
            json={
                "target_id": target_id,
                "success": success,
                "version": version,
                "detail": detail,
            },
            headers=_headers(),
            timeout=15,
        )
    except Exception as exc:
        print(f"[SmartIT] Software result error: {exc}")


def _download_package(job):
    os.makedirs(CACHE_DIR, exist_ok=True)

    target_id = job["target_id"]
    package = job["package"]

    file_name = os.path.basename(package["file_name"] or package["name"])

    if not file_name:
        file_name = "installer.bin"

    path = os.path.join(CACHE_DIR, f"{target_id}-{file_name}")

    _post_status(target_id, "downloading", 5, "Downloading package")

    digest = hashlib.sha256()

    try:
        response = requests.get(
            f"{API_URL}/software/agent/download/{target_id}",
            headers=_headers(),
            stream=True,
            timeout=60,
        )

        if response.status_code != 200:
            _post_result(
                target_id,
                False,
                "",
                f"Download rejected HTTP={response.status_code}",
            )
            return

        downloaded = 0

        with open(path, "wb") as out:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue

                out.write(chunk)
                downloaded += len(chunk)
                digest.update(chunk)

                if downloaded > MAX_DOWNLOAD_BYTES:
                    out.close()
                    os.remove(path)
                    _post_result(
                        target_id,
                        False,
                        "",
                        "Package download exceeds size limit",
                    )
                    return

        actual = digest.hexdigest().lower()
        expected = (package.get("checksum") or "").lower()

        if expected and actual != expected:
            os.remove(path)
            _post_result(
                target_id,
                False,
                "",
                f"Checksum mismatch: expected {expected}, got {actual}",
            )
            return

        _post_status(
            target_id,
            "installing",
            40,
            "Package verified",
        )

        return path

    except Exception as exc:
        _post_result(
            target_id,
            False,
            "",
            f"Download error: {exc}",
        )
        return None


def _run_command(job, command, cwd, timeout):
    _post_status(
        job["target_id"],
        "installing",
        60,
        "Running installer",
    )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")

        return result.returncode == 0, output.strip()[:1500]

    except subprocess.TimeoutExpired:
        return False, "Installer timed out"
    except Exception as exc:
        return False, str(exc)


def _extract_version(text):
    if not text:
        return ""

    match = VERSION_RE.search(text)

    if not match:
        return ""

    return match.group(1)


def _verify_install(job, cwd):
    package = job["package"]
    verify_command = package.get("verify_command", "").strip()

    if not verify_command:
        return True, "", ""

    try:
        result = subprocess.run(
            verify_command,
            shell=True,
            cwd=cwd,
            timeout=60,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        return False, "", f"Verification error: {exc}"

    output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()

    if result.returncode != 0:
        return False, "", f"Verification failed: {output[:300]}"

    return True, output, ""


def _run_job(job):
    target_id = job["target_id"]
    action = job["action"]
    package = job["package"]

    print(
        f"[SmartIT] Software job {target_id}: "
        f"{package['name']} {package['version']} ({action})"
    )

    if action == "enforce":
        _post_status(target_id, "installing", 30, "Checking version")
        _post_result(
            target_id,
            True,
            package["version"],
            "Version enforced",
        )
        return

    path = _download_package(job)

    if path is None:
        return

    try:
        if action == "uninstall":
            command = package.get("uninstall_command", "").strip()
        else:
            command = package.get("install_command", "").strip()

        if not command:
            _post_result(
                target_id,
                False,
                "",
                f"No predefined {'uninstall' if action == 'uninstall' else 'install'} command",
            )
            return

        cwd = os.path.dirname(path)

        timeout = int(
            package.get("install_timeout_seconds", 600)
            or 600
        )

        _post_status(target_id, "installing", 55, "Starting installer")

        ok, output = _run_command(job, command, cwd, timeout)

        if not ok:
            _post_result(
                target_id,
                False,
                "",
                f"Installer failed: {output[:300]}",
            )
            return

        _post_status(target_id, "installing", 85, "Verifying installation")

        verified, verify_output, verify_error = _verify_install(job, cwd)

        if not verified:
            _post_result(
                target_id,
                False,
                "",
                verify_error or "Verification failed",
            )
            return

        version = _extract_version(verify_output) or package["version"]

        _post_result(
            target_id,
            True,
            version,
            f"Installed {package['name']} {version}",
        )

        _post_inventory(package, version)

    finally:
        try:
            os.remove(path)
        except Exception:
            pass


def _post_inventory(package, version):
    try:
        requests.post(
            f"{API_URL}/software/agent/inventory",
            json={
                "items": [
                    {
                        "name": package["name"],
                        "version": version,
                        "publisher": package.get("publisher", ""),
                    }
                ]
            },
            headers=_headers(),
            timeout=15,
        )
    except Exception as exc:
        print(f"[SmartIT] Software inventory error: {exc}")


def _software_loop():
    while True:
        try:
            _report_device_info()

            jobs = _fetch_work()

            for job in jobs:
                try:
                    _run_job(job)
                except Exception as exc:
                    print(f"[SmartIT] Software job error: {exc}")

                    try:
                        _post_result(
                            job["target_id"],
                            False,
                            "",
                            f"Agent error: {exc}",
                        )
                    except Exception:
                        pass

        except Exception as exc:
            print(f"[SmartIT] Software deployment cycle error: {exc}")

        time.sleep(SOFTWARE_POLL_INTERVAL)


def start_software_deployment():
    thread = threading.Thread(
        target=_software_loop,
        daemon=True,
        name="software_deployment",
    )
    thread.start()
    return thread
