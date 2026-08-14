"""SmartIT Agent — endpoint activity collectors.

Collects real activity events from the host:

  * app_launched / app_closed          - psutil process snapshot diffs
  * browser_opened / browser_closed    - browser process diffs
  * url_visited                        - browser history (only when URL
                                         auditing is enabled by the server)
  * user_login / user_logout           - psutil.users snapshot diffs
  * usb_connected / usb_removed        - sysfs USB snapshot diffs
  * software_installed / software_removed - dpkg.log tail
  * system_boot                        - boot time change detection
  * network_connected / network_disconnected - interface snapshot diffs
  * security_failed_auth / security_privilege_escalation - auth.log tail

Every collector is best-effort: failures are swallowed so the agent never
crashes because of a missing log file or permission error.
"""

import os
import shutil
import sqlite3
import tempfile
import time

import psutil

try:
    from usb.usb_monitor import get_usb_devices
except Exception:
    get_usb_devices = None


# ---------------------------------------------------------------------------
# State (module level, one collector per agent process)
# ---------------------------------------------------------------------------

_state = {
    "processes": {},
    "browsers": {},
    "users": {},
    "usb": {},
    "boot_time": None,
    "dpkg_offset": 0,
    "auth_offset": 0,
    "interfaces": {},
    "url_cursor": 0,
    "url_auditing": False,
}

BROWSER_NAMES = {
    "firefox",
    "chrome",
    "chromium",
    "chromium-browser",
    "brave",
    "brave-browser",
    "opera",
    "edge",
    "safari",
}

HISTORY_PATHS = [
    "~/.config/google-chrome/Default/History",
    "~/.config/google-chrome-beta/Default/History",
    "~/.config/chromium/Default/History",
    "~/.config/brave-browser/Default/History",
    "~/.config/microsoft-edge/Default/History",
]

AUTH_LOGS = ["/var/log/auth.log", "/var/log/secure"]
DPKG_LOGS = ["/var/log/dpkg.log", "/var/log/dpkg.log.1"]


def _username():
    try:
        users = psutil.users()
        if users:
            return users[0].name
    except Exception:
        pass
    return os.environ.get("USER", os.environ.get("LOGNAME", ""))


def _read_tail(path, offset, max_bytes=512 * 1024):
    """Return (new_text, new_offset) reading a growing log file by offset."""

    try:
        size = os.path.getsize(path)
    except OSError:
        return "", offset

    if size < offset:
        offset = 0

    try:
        with open(path, "r", errors="replace") as handle:
            handle.seek(offset)
            text = handle.read(max_bytes)
            return text, handle.tell()
    except OSError:
        return "", offset


def _is_kernel_thread(name):
    """Kernel threads have names like 'kworker/0:1' or trailing ':'."""

    if ":" in name:
        return True

    for prefix in (
        "kworker",
        "kthread",
        "ksoftirqd",
        "kcompactd",
        "khugepaged",
        "kswapd",
        "migration/",
        "watchdog/",
    ):
        if name.startswith(prefix):
            return True

    return False


def _process_snapshot():
    snapshot = {}

    for proc in psutil.process_iter(
        ["pid", "name", "create_time", "username"]
    ):
        try:
            name = (proc.info["name"] or "unknown").lower()

            if _is_kernel_thread(name):
                continue

            snapshot[proc.info["pid"]] = {
                "pid": proc.info["pid"],
                "name": name,
                "create_time": proc.info["create_time"],
                "username": proc.info["username"] or "",
            }
        except Exception:
            continue

    return snapshot


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------


def collect_process_events():
    """App launch/close events via process snapshot diffs."""

    events = []

    try:
        current = _process_snapshot()
    except Exception:
        return events

    previous = _state["processes"]

    if previous:
        for pid, info in current.items():
            if pid not in previous:
                events.append({
                    "event_type": "app_launched",
                    "application": info["name"],
                    "username": info["username"] or _username(),
                    "description": f"Application started: {info['name']}",
                    "metadata": {"pid": pid},
                })

        for pid, info in previous.items():
            if pid not in current:
                events.append({
                    "event_type": "app_closed",
                    "application": info["name"],
                    "username": info["username"] or _username(),
                    "description": f"Application exited: {info['name']}",
                    "metadata": {"pid": pid},
                })

    _state["processes"] = current

    return events


def collect_browser_events():
    """Browser open/close events + URL visits (when enabled)."""

    events = []
    snapshot = _state["processes"]

    if not snapshot:
        return events

    current = {
        pid: info
        for pid, info in snapshot.items()
        if info["name"] in BROWSER_NAMES
    }

    previous = _state["browsers"]

    if previous:
        for pid, info in current.items():
            if pid not in previous:
                events.append({
                    "event_type": "browser_opened",
                    "application": info["name"],
                    "username": info["username"] or _username(),
                    "description": f"Browser opened: {info['name']}",
                })

        for pid, info in previous.items():
            if pid not in current:
                events.append({
                    "event_type": "browser_closed",
                    "application": info["name"],
                    "username": info["username"] or _username(),
                    "description": f"Browser closed: {info['name']}",
                })

    _state["browsers"] = current

    if _state["url_auditing"]:
        events.extend(collect_url_events())

    return events


def collect_url_events():
    """Recent visited URLs from browser history databases."""

    events = []

    for pattern in HISTORY_PATHS:
        path = os.path.expanduser(pattern)

        if not os.path.exists(path):
            continue

        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                prefix="smartit-history-", suffix=".sqlite", delete=False
            ) as tmp:
                tmp_path = tmp.name

            shutil.copy2(path, tmp_path)

            conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("PRAGMA query_only = ON")
            cursor.execute(
                """
                SELECT url, title, last_visit_time
                FROM urls
                WHERE last_visit_time > ?
                ORDER BY last_visit_time ASC
                LIMIT 100
                """,
                (int(_state["url_cursor"]),),
            )

            for url, title, visit_time in cursor.fetchall():
                # Chrome time: microseconds since 1601-01-01.
                unix_time = visit_time / 1_000_000 - 11644473600

                events.append({
                    "event_type": "url_visited",
                    "application": os.path.basename(
                        os.path.dirname(os.path.dirname(path))
                    ).lower(),
                    "url": url,
                    "description": (
                        f"Visited: {title or url}"
                    )[:500],
                    "timestamp": (
                        time.strftime(
                            "%Y-%m-%dT%H:%M:%S",
                            time.localtime(unix_time),
                        )
                        if unix_time > 0
                        else None
                    ),
                })

                if visit_time > _state["url_cursor"]:
                    _state["url_cursor"] = visit_time

            conn.close()

        except Exception:
            pass

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    return events


def collect_user_events():
    """Login/logout events via psutil.users diffs."""

    events = []

    try:
        current = {
            (user.name, user.terminal, user.started)
            for user in psutil.users()
        }
    except Exception:
        return events

    previous = _state["users"]

    if previous:
        for name, terminal, started in current - previous:
            events.append({
                "event_type": "user_login",
                "username": name,
                "description": (
                    f"User logged in on {terminal or 'console'}"
                ),
            })

        for name, terminal, started in previous - current:
            events.append({
                "event_type": "user_logout",
                "username": name,
                "description": (
                    f"User logged out of {terminal or 'console'}"
                ),
            })

    _state["users"] = current

    return events


def collect_usb_events():
    """USB connect/disconnect events via sysfs snapshot diffs."""

    events = []

    if get_usb_devices is None:
        return events

    try:
        current = {
            (device["usb_id"], device["vendor"], device["product"])
            for device in get_usb_devices()
        }
    except Exception:
        return events

    previous = _state["usb"]

    if previous:
        for usb_id, vendor, product in current - previous:
            events.append({
                "event_type": "usb_connected",
                "username": _username(),
                "description": (
                    f"USB device connected: {vendor} {product}"
                ).strip(),
                "metadata": {"usb_id": usb_id},
            })

        for usb_id, vendor, product in previous - current:
            events.append({
                "event_type": "usb_removed",
                "username": _username(),
                "description": (
                    f"USB device removed: {vendor} {product}"
                ).strip(),
                "metadata": {"usb_id": usb_id},
            })

    _state["usb"] = current

    return events


def _parse_dpkg_line(line, events):
    parts = line.split()

    if len(parts) < 4:
        return

    timestamp = " ".join(parts[:2])
    action = parts[2]
    package = parts[3].split(":")[0]

    if action == "install":
        events.append({
            "event_type": "software_installed",
            "application": package,
            "username": _username(),
            "description": f"Package installed: {package}",
            "timestamp": timestamp,
        })

    elif action in ("remove", "purge"):
        events.append({
            "event_type": "software_removed",
            "application": package,
            "username": _username(),
            "description": f"Package removed: {package}",
            "timestamp": timestamp,
        })


def collect_software_events():
    """Package install/remove events from dpkg.log tail."""

    events = []

    for path in DPKG_LOGS:
        if not os.path.exists(path):
            continue

        had_baseline = _state["dpkg_offset"] > 0

        text, new_offset = _read_tail(path, _state["dpkg_offset"])

        _state["dpkg_offset"] = new_offset

        if had_baseline:
            for line in text.splitlines():
                if line.strip():
                    _parse_dpkg_line(line, events)

        break  # only the newest dpkg.log

    return events


def collect_system_events():
    """Boot events via boot time change detection."""

    events = []

    try:
        boot_time = int(psutil.boot_time())
    except Exception:
        return events

    previous = _state["boot_time"]

    if previous is not None and boot_time != previous:
        events.append({
            "event_type": "system_boot",
            "username": _username(),
            "description": (
                "System booted "
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(boot_time))}"
            ),
            "metadata": {"boot_time": boot_time},
        })

    _state["boot_time"] = boot_time

    return events


def collect_network_events():
    """Interface up/down events via interface snapshot diffs."""

    events = []

    try:
        stats = psutil.net_if_stats()
    except Exception:
        return events

    current = {
        name: {"up": bool(stat.isup)}
        for name, stat in stats.items()
    }

    previous = _state["interfaces"]

    if previous:
        for name, info in current.items():
            if name not in previous and info["up"]:
                events.append({
                    "event_type": "network_connected",
                    "username": _username(),
                    "description": f"Network interface connected: {name}",
                    "metadata": {"interface": name},
                })

            elif (
                name in previous
                and previous[name]["up"]
                and not info["up"]
            ):
                events.append({
                    "event_type": "network_disconnected",
                    "username": _username(),
                    "description": (
                        f"Network interface disconnected: {name}"
                    ),
                    "metadata": {"interface": name},
                })

        for name in previous:
            if name not in current:
                events.append({
                    "event_type": "network_disconnected",
                    "username": _username(),
                    "description": f"Network interface removed: {name}",
                    "metadata": {"interface": name},
                })

    _state["interfaces"] = current

    return events


def _parse_auth_line(line, events):
    lowered = line.lower()

    if "failed password" in lowered:
        username = ""
        for marker in ("for ", "for invalid user "):
            if marker in line:
                username = (
                    line.split(marker, 1)[1].split()[0].strip()
                )
                break

        events.append({
            "event_type": "security_failed_auth",
            "username": username or _username(),
            "description": "Failed authentication attempt",
            "metadata": {"detail": line.strip()[:300]},
        })

    elif " sudo" in line.lower() or "\tsudo" in lowered:
        command = ""
        if "COMMAND=" in line:
            command = line.split("COMMAND=", 1)[1].strip()[:200]

        events.append({
            "event_type": "security_privilege_escalation",
            "username": _username(),
            "description": "Privilege escalation via sudo",
            "metadata": {"command": command or line.strip()[:200]},
        })

    elif line.lower().startswith("su["):
        events.append({
            "event_type": "security_privilege_escalation",
            "username": _username(),
            "description": "User switched via su",
            "metadata": {"detail": line.strip()[:200]},
        })


def collect_security_events():
    """Failed logins and privilege escalations from auth.log tail."""

    events = []

    for path in AUTH_LOGS:
        if not os.path.exists(path):
            continue

        had_baseline = _state["auth_offset"] > 0

        text, new_offset = _read_tail(path, _state["auth_offset"])

        _state["auth_offset"] = new_offset

        if had_baseline:
            for line in text.splitlines():
                if line.strip():
                    _parse_auth_line(line, events)

        break  # only the newest auth log

    return events


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def set_url_auditing(enabled):
    """Enable/disable browser URL collection."""

    _state["url_auditing"] = bool(enabled)

    if not _state["url_auditing"]:
        _state["url_cursor"] = 0


def collect_all(url_auditing=None):
    """Run every collector and return the combined event list."""

    if url_auditing is not None:
        set_url_auditing(url_auditing)

    events = []

    events.extend(collect_process_events())
    events.extend(collect_browser_events())
    events.extend(collect_user_events())
    events.extend(collect_usb_events())
    events.extend(collect_software_events())
    events.extend(collect_system_events())
    events.extend(collect_network_events())
    events.extend(collect_security_events())

    return events
