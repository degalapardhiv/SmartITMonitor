import json
import os
import shutil
import sys
import tempfile
import threading
import time

import requests

API_URL = os.getenv(
    "SMARTIT_API_URL",
    "http://127.0.0.1:8000",
)

AGENT_TOKEN = os.getenv(
    "SMARTIT_AGENT_TOKEN",
    ""
)

WEB_ACCESS_POLL_INTERVAL = int(
    os.getenv("SMARTIT_WEB_ACCESS_POLL_INTERVAL", "15")
)

STATE_DIR = os.getenv(
    "SMARTIT_WEB_ACCESS_STATE",
    os.path.join(tempfile.gettempdir(), "smartit-web-access"),
)

STATE_FILE = os.path.join(STATE_DIR, "state.json")
ALLOWLIST_FILE = os.path.join(STATE_DIR, "allowlist.conf")

HOSTS_BANNER_START = "# >>> SmartIT Web Access Control"
HOSTS_BANNER_END = "# <<< SmartIT Web Access Control"


def _headers():
    headers = {}

    if AGENT_TOKEN:
        headers["x-agent-token"] = AGENT_TOKEN

    return headers


def _hosts_path():
    if sys.platform == "win32":
        return r"C:\Windows\System32\drivers\etc\hosts"

    return "/etc/hosts"


def _fetch_policy():
    response = requests.get(
        f"{API_URL}/web-access/agent/policy",
        headers=_headers(),
        timeout=15,
    )

    if response.status_code != 200:
        return None

    return response.json()


def _post_sync(applied, failed, device_version=0):
    try:
        response = requests.post(
            f"{API_URL}/web-access/agent/sync-result",
            json={
                "device_version": device_version,
                "applied": applied,
                "failed": failed,
            },
            headers=_headers(),
            timeout=15,
        )

        if response.status_code >= 400:
            print(
                f"[SmartIT] Web access sync rejected "
                f"HTTP={response.status_code}: {response.text[:200]}"
            )
    except Exception as exc:
        print(f"[SmartIT] Web access sync error: {exc}")


# ---------------------------------------------------------------------------
# Hosts file management
# ---------------------------------------------------------------------------


def _read_hosts_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except FileNotFoundError:
        return []


def _split_managed_block(lines):
    """Return (unmanaged_lines, managed_lines) around the banner."""
    clean = []
    managed = []
    in_block = False

    for line in lines:
        stripped = line.strip()

        if stripped == HOSTS_BANNER_START:
            in_block = True
            managed.append(line)
            continue

        if stripped == HOSTS_BANNER_END:
            in_block = False
            managed.append(line)
            continue

        if in_block:
            managed.append(line)
        else:
            clean.append(line)

    return clean, managed


def _blocklist_host_entries(policies):
    entries = []

    for policy in policies:
        if policy.get("action") != "blocklist":
            continue

        for domain in policy.get("domains", []):
            name = domain.get("domain", "").strip()

            if not name:
                continue

            entries.append(f"127.0.0.1 {name}")
            entries.append(f"::1 {name}")

    return entries


def _write_hosts(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.exists(path):
        backup = path + ".smartit.bak"

        try:
            shutil.copy2(path, backup)
        except Exception:
            pass

    content = "\n".join(lines)

    if not content.endswith("\n"):
        content += "\n"

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _apply_blocklist(policies):
    """Rewrite the managed hosts block to reflect current blocklist rules."""
    path = _hosts_path()
    lines = _read_hosts_lines(path)
    clean, _ = _split_managed_block(lines)

    entries = _blocklist_host_entries(policies)

    if not entries:
        _write_hosts(path, clean)
        return

    block = [HOSTS_BANNER_START] + entries + [HOSTS_BANNER_END]
    _write_hosts(path, clean + [""] + block)


# ---------------------------------------------------------------------------
# Allowlist rules (for a DNS proxy / firewall to consume)
# ---------------------------------------------------------------------------


def _write_allowlist_rules(policies):
    os.makedirs(STATE_DIR, exist_ok=True)

    lines = ["# SmartIT Web Access Control - allowlist rules"]
    lines.append("# Enforced by a forwarding DNS proxy / firewall.")
    lines.append("")

    for policy in policies:
        if policy.get("action") != "allowlist":
            continue

        for domain in policy.get("domains", []):
            name = domain.get("domain", "").strip()

            if not name:
                continue

            subdomains = "yes" if domain.get("include_subdomains") else "no"
            lines.append(f"allow {name} subdomains={subdomains}")

    lines.append("")

    with open(ALLOWLIST_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def _load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)

    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


# ---------------------------------------------------------------------------
# Apply cycle
# ---------------------------------------------------------------------------


def _cycle():
    data = _fetch_policy()

    if data is None:
        return

    state = _load_state()

    if not data.get("enabled"):
        # Globally disabled: clear everything we previously managed.
        _apply_blocklist([])
        _save_state({})
        return

    policies = data.get("policies", [])
    applied = []
    failed = []

    blocklist_rules = [
        p for p in policies if p.get("action") == "blocklist"
    ]
    allowlist_rules = [
        p for p in policies if p.get("action") == "allowlist"
    ]

    # Blocklist enforcement via hosts file (covers every blocklist policy).
    try:
        _apply_blocklist(blocklist_rules)
    except Exception as exc:
        for policy in blocklist_rules:
            failed.append(
                {
                    "policy_id": policy.get("id"),
                    "version": policy.get("version"),
                    "detail": f"Hosts file update failed: {exc}",
                }
            )
    else:
        for policy in blocklist_rules:
            applied.append(
                {
                    "policy_id": policy.get("id"),
                    "version": policy.get("version"),
                    "detail": "Blocked domains via hosts file",
                }
            )

    # Allowlist rules written for a DNS proxy / firewall to consume.
    try:
        _write_allowlist_rules(allowlist_rules)
    except Exception as exc:
        for policy in allowlist_rules:
            failed.append(
                {
                    "policy_id": policy.get("id"),
                    "version": policy.get("version"),
                    "detail": f"Allowlist rules failed: {exc}",
                }
            )
    else:
        for policy in allowlist_rules:
            applied.append(
                {
                    "policy_id": policy.get("id"),
                    "version": policy.get("version"),
                    "detail": (
                        "Allowlist written to "
                        f"{ALLOWLIST_FILE} (proxy/firewall must enforce)"
                    ),
                }
            )

    new_state = {}

    for policy in policies:
        new_state[str(policy.get("id"))] = policy.get("version")

    changed = new_state != state

    _save_state(new_state)

    if applied or failed:
        _post_sync(
            applied,
            failed,
            device_version=len(new_state),
        )


def _web_access_loop():
    while True:
        try:
            _cycle()
        except Exception as exc:
            print(f"[SmartIT] Web access cycle error: {exc}")

        time.sleep(WEB_ACCESS_POLL_INTERVAL)


def start_web_access():
    thread = threading.Thread(
        target=_web_access_loop,
        daemon=True,
        name="web_access",
    )
    thread.start()
    return thread
