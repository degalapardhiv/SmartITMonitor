import json
import re
import threading
import time
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from .crypto_utils import (
    MASKED_VALUE,
    decrypt_secret,
    encrypt_secret,
    is_secret_set,
)
from .database import SessionLocal
from .monitor_settings_model import MonitorSetting
from .settings_audit_model import SettingsAudit


LOGIN_ROUTE_RE = re.compile(r"^/[a-zA-Z0-9/_-]*$")

URL_RE = re.compile(
    r"^https?://[^\s]+$",
    re.IGNORECASE,
)

INT_TYPES = {"int"}


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool(value, default):
    if isinstance(value, bool):
        return value

    return str(value).lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Section registry
# ---------------------------------------------------------------------------

SECTIONS = {
    "general": {
        "label": "General",
        "description": (
            "Site-wide display and integration URLs."
        ),
        "keys": [
            {
                "key": "site_name",
                "label": "Site Name",
                "type": "str",
                "default": "Smart IT Monitor",
                "max_length": 64,
            },
            {
                "key": "login_redirect_route",
                "label": "Post-Login Redirect Route",
                "type": "path",
                "default": "/dashboard",
                "help": (
                    "Relative application route used after login. "
                    "Must start with '/' and contain only "
                    "letters, numbers, '/', '_' or '-'."
                ),
            },
            {
                "key": "support_url",
                "label": "Support URL",
                "type": "url",
                "default": "",
                "optional": True,
                "help": "Absolute http(s) URL to your support portal.",
            },
            {
                "key": "status_page_url",
                "label": "Status Page URL",
                "type": "url",
                "default": "",
                "optional": True,
                "help": "Absolute http(s) URL to your status page.",
            },
        ],
    },
    "auth_security": {
        "label": "Auth & Security",
        "description": (
            "Session and token security settings."
        ),
        "keys": [
            {
                "key": "access_token_expire_minutes",
                "label": "Access Token Expiry (minutes)",
                "type": "int",
                "default": 60,
                "min": 1,
                "max": 1440,
                "help": (
                    "JWT session length in minutes. "
                    "Takes effect for tokens issued after saving."
                ),
            },
        ],
    },
    "telegram": {
        "label": "Telegram",
        "description": (
            "Telegram bot notifications for alerts."
        ),
        "keys": [
            {
                "key": "telegram_enabled",
                "label": "Enable Telegram Notifications",
                "type": "bool",
                "default": True,
            },
            {
                "key": "telegram_bot_token",
                "label": "Bot Token",
                "type": "secret",
                "default": "",
                "optional": True,
                "help": (
                    "Bot token from BotFather. Stored encrypted. "
                    "Falls back to the TELEGRAM_BOT_TOKEN "
                    "environment variable when empty."
                ),
            },
            {
                "key": "telegram_chat_id",
                "label": "Chat ID",
                "type": "str",
                "default": "",
                "optional": True,
                "help": (
                    "Numeric chat id the bot sends to. Falls back "
                    "to the TELEGRAM_CHAT_ID environment variable "
                    "when empty."
                ),
            },
        ],
    },
    "email": {
        "label": "Email / SMTP",
        "description": (
            "SMTP server used to send alert emails."
        ),
        "keys": [
            {
                "key": "smtp_server",
                "label": "SMTP Server",
                "type": "str",
                "default": "",
                "optional": True,
            },
            {
                "key": "smtp_port",
                "label": "SMTP Port",
                "type": "int",
                "default": 587,
                "min": 1,
                "max": 65535,
            },
            {
                "key": "username",
                "label": "Username",
                "type": "str",
                "default": "",
                "optional": True,
            },
            {
                "key": "receiver",
                "label": "Receiver",
                "type": "str",
                "default": "",
                "optional": True,
            },
            {
                "key": "password",
                "label": "Password",
                "type": "secret",
                "default": "",
                "optional": True,
                "help": (
                    "Leave blank to keep the current password. "
                    "The stored value is never returned by the API."
                ),
            },
        ],
    },
    "monitoring": {
        "label": "Monitoring",
        "description": (
            "Alert thresholds and monitor loop cadence."
        ),
        "keys": [
            {
                "key": "cpu_threshold",
                "label": "CPU Threshold (%)",
                "type": "int",
                "default": 80,
                "min": 1,
                "max": 1000,
            },
            {
                "key": "ram_threshold",
                "label": "RAM Threshold (%)",
                "type": "int",
                "default": 90,
                "min": 1,
                "max": 1000,
            },
            {
                "key": "disk_threshold",
                "label": "Disk Threshold (%)",
                "type": "int",
                "default": 90,
                "min": 1,
                "max": 1000,
            },
            {
                "key": "alert_cooldown_minutes",
                "label": "Alert Cooldown (minutes)",
                "type": "int",
                "default": 5,
                "min": 1,
                "max": 1000,
            },
            {
                "key": "alert_monitor_interval_seconds",
                "label": "Alert Monitor Interval (seconds)",
                "type": "int",
                "default": 15,
                "min": 5,
                "max": 3600,
            },
        ],
    },
    "heartbeat": {
        "label": "Heartbeat",
        "description": (
            "Agent heartbeat tracking for device status."
        ),
        "keys": [
            {
                "key": "heartbeat_timeout_seconds",
                "label": "Offline Timeout (seconds)",
                "type": "int",
                "default": 60,
                "min": 10,
                "max": 3600,
                "help": (
                    "Seconds without a heartbeat before a device "
                    "is marked offline."
                ),
            },
            {
                "key": "heartbeat_check_interval_seconds",
                "label": "Check Interval (seconds)",
                "type": "int",
                "default": 15,
                "min": 5,
                "max": 3600,
            },
        ],
    },
    "discovery": {
        "label": "Network Discovery",
        "description": (
            "Networks scanned for new devices."
        ),
        "keys": [
            {
                "key": "scan_ranges",
                "label": "Scan Ranges",
                "type": "list",
                "default": [],
                "item_label": "CIDR range",
                "help": (
                    "One CIDR range per entry, e.g. 192.168.1.0/24."
                ),
            },
        ],
    },
    "usb_security": {
        "label": "USB Security",
        "description": (
            "Default USB policy when Exam Mode is disabled."
        ),
        "keys": [
            {
                "key": "usb_default_policy",
                "label": "Default USB Policy",
                "type": "select",
                "choices": [
                    "approval_required",
                    "allow",
                    "block",
                ],
                "default": "approval_required",
            },
        ],
    },
    "exam_mode": {
        "label": "Exam Mode",
        "description": (
            "Exam Mode restricts USB and enforces lab policy."
        ),
        "keys": [
            {
                "key": "enabled",
                "label": "Enable Exam Mode",
                "type": "bool",
                "default": False,
            },
            {
                "key": "usb_policy",
                "label": "USB Policy",
                "type": "select",
                "choices": [
                    "approval_required",
                    "allow",
                    "block",
                ],
                "default": "approval_required",
            },
        ],
    },
    "endpoint_activity": {
        "label": "Endpoint Activity",
        "description": (
            "Endpoint activity collection and retention."
        ),
        "keys": [
            {
                "key": "endpoint_url_auditing",
                "label": "URL Auditing",
                "type": "bool",
                "default": False,
                "help": (
                    "Capture visited URLs. Keep disabled for "
                    "privacy unless auditing is required."
                ),
            },
            {
                "key": "endpoint_retention_days",
                "label": "Retention (days)",
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 365,
            },
            {
                "key": "endpoint_activity_interval_seconds",
                "label": "Upload Interval (seconds)",
                "type": "int",
                "default": 30,
                "min": 10,
                "max": 3600,
                "help": (
                    "How often agents upload activity batches. "
                    "Agents pick this up on their next config refresh."
                ),
            },
        ],
    },
    "endpoint_threat": {
        "label": "Endpoint Threat Protection",
        "description": (
            "Endpoint threat detection, blocking and quarantine policy."
        ),
        "keys": [
            {
                "key": "endpoint_threat_enabled",
                "label": "Threat Protection",
                "type": "bool",
                "default": True,
                "help": (
                    "Master switch. When disabled, agents still scan but "
                    "reported detections are recorded without enforcement."
                ),
            },
            {
                "key": "threat_scan_policy",
                "label": "Scan Mode",
                "type": "select",
                "choices": [
                    "real_time",
                    "scheduled",
                    "on_access",
                ],
                "default": "real_time",
                "help": "How often agents scan for threats.",
            },
            {
                "key": "threat_quarantine_policy",
                "label": "Quarantine Policy",
                "type": "select",
                "choices": [
                    "auto",
                    "review",
                ],
                "default": "auto",
                "help": (
                    "Quarantine confirmed files automatically or wait for "
                    "an administrator decision."
                ),
            },
            {
                "key": "threat_suspicious_handling",
                "label": "Suspicious File Handling",
                "type": "select",
                "choices": [
                    "block",
                    "review",
                    "notify",
                ],
                "default": "block",
                "help": (
                    "How unconfirmed/suspicious files are treated. "
                    "Blocking is recommended."
                ),
            },
            {
                "key": "threat_notify_critical",
                "label": "Critical Notifications",
                "type": "bool",
                "default": True,
                "help": (
                    "Send alerts (in-app, email, Telegram) when a "
                    "critical-threat event is detected."
                ),
            },
            {
                "key": "threat_retention_days",
                "label": "Retention (days)",
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 365,
            },
            {
                "key": "threat_scan_interval_seconds",
                "label": "Scan Interval (seconds)",
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 86400,
                "help": (
                    "How often agents should re-scan for new threats."
                ),
            },
        ],
    },
    "provisioning": {
        "label": "Software Deployment",
        "description": (
            "Deployment API integration for provisioning."
        ),
        "keys": [
            {
                "key": "provisioning_api_url",
                "label": "Provisioning API URL",
                "type": "url",
                "default": "",
                "optional": True,
                "help": (
                    "Absolute http(s) URL. Falls back to "
                    "SMARTIT_PROVISIONING_API_URL."
                ),
            },
            {
                "key": "provisioning_api_token",
                "label": "API Token",
                "type": "secret",
                "default": "",
                "optional": True,
                "help": (
                    "Bearer token for the provisioning API. "
                    "Stored encrypted. Falls back to "
                    "SMARTIT_PROVISIONING_API_TOKEN."
                ),
            },
            {
                "key": "provisioning_deploy_timeout_minutes",
                "label": "Deployment Timeout (minutes)",
                "type": "int",
                "default": 60,
                "min": 1,
                "max": 10080,
            },
        ],
    },
    "cctv": {
        "label": "CCTV / Cameras",
        "description": (
            "Camera offline monitoring."
        ),
        "keys": [
            {
                "key": "camera_check_interval_seconds",
                "label": "Check Interval (seconds)",
                "type": "int",
                "default": 30,
                "min": 10,
                "max": 3600,
            },
            {
                "key": "camera_probe_timeout_seconds",
                "label": "Probe Timeout (seconds)",
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 30,
            },
        ],
    },
    "retention": {
        "label": "Data Retention",
        "description": (
            "How long historical records are kept."
        ),
        "keys": [
            {
                "key": "notification_history_retention_days",
                "label": "Notification History (days)",
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 3650,
            },
            {
                "key": "email_history_retention_days",
                "label": "Email History (days)",
                "type": "int",
                "default": 30,
                "min": 1,
                "max": 3650,
            },
            {
                "key": "settings_audit_retention_days",
                "label": "Settings Audit Log (days)",
                "type": "int",
                "default": 180,
                "min": 1,
                "max": 3650,
            },
        ],
    },
    "websocket": {
        "label": "WebSocket / Realtime",
        "description": (
            "Realtime client connection tuning."
        ),
        "keys": [
            {
                "key": "ws_ping_interval_seconds",
                "label": "Ping Interval (seconds)",
                "type": "int",
                "default": 30,
                "min": 5,
                "max": 300,
                "help": (
                    "How often the server pings connected clients."
                ),
            },
        ],
    },
    "web_access": {
        "label": "Web Access Control",
        "description": (
            "Allow/block domain enforcement on managed devices."
        ),
        "keys": [
            {
                "key": "web_access_enabled",
                "label": "Enabled",
                "type": "bool",
                "default": True,
            },
            {
                "key": "web_access_poll_interval_seconds",
                "label": "Poll Interval (seconds)",
                "type": "int",
                "default": 15,
                "min": 10,
                "max": 3600,
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Low-level KV helpers
# ---------------------------------------------------------------------------


def get_setting(db: Session, key, default=None):
    row = (
        db.query(MonitorSetting)
        .filter(MonitorSetting.key == key)
        .first()
    )

    if row is not None:
        return row.value

    return default


def set_setting(db: Session, key, value):
    row = (
        db.query(MonitorSetting)
        .filter(MonitorSetting.key == key)
        .first()
    )

    if row is None:
        row = MonitorSetting(
            key=key,
            value=str(value),
        )
        db.add(row)
    else:
        row.value = str(value)

    db.commit()

    return row.value


def _secret_value(db, key, env_default=""):
    raw = get_setting(db, key)

    if raw:
        decrypted = decrypt_secret(raw)

        if decrypted is not None:
            return decrypted

    return env_default


# ---------------------------------------------------------------------------
# Section value rendering
# ---------------------------------------------------------------------------


def _render_value(spec, stored):
    if spec["type"] == "int":
        return _int(stored, spec["default"])

    if spec["type"] == "bool":
        return _bool(stored, spec["default"])

    if spec["type"] == "list":
        try:
            parsed = json.loads(stored) if stored else []
        except (TypeError, ValueError):
            parsed = []

        if not isinstance(parsed, list):
            parsed = []

        return [
            item
            for item in parsed
            if isinstance(item, str) and item.strip()
        ]

    if stored is None:
        return spec["default"]

    return stored


def get_section_snapshot(db: Session, section):
    """Values for a section, secrets masked."""

    meta = SECTIONS[section]

    if section == "email":
        from .email_settings_model import EmailSetting

        config = db.query(EmailSetting).first()

        values = {}

        for spec in meta["keys"]:
            key = spec["key"]

            if config is None:
                if spec["type"] == "secret":
                    values[key] = ""
                else:
                    values[key] = _render_value(spec, None)
                continue

            if key == "password":
                values[key] = "********" if config.password else ""
            else:
                values[key] = _render_value(
                    spec,
                    getattr(config, key, None),
                )

        return values

    if section == "exam_mode":
        row = db.execute(
            text("""
                SELECT enabled, usb_policy
                FROM exam_mode_settings
                WHERE id = 1
            """)
        ).mappings().first()

        if row is None:
            return {
                "enabled": False,
                "usb_policy": "approval_required",
            }

        return {
            "enabled": bool(row["enabled"]),
            "usb_policy": row["usb_policy"],
        }

    values = {}

    for spec in meta["keys"]:
        key = spec["key"]
        stored = get_setting(db, key)

        if spec["type"] == "secret":
            values[key] = "********" if is_secret_set(stored) else ""
        else:
            values[key] = _render_value(spec, stored)

    return values


# ---------------------------------------------------------------------------
# Validation & application
# ---------------------------------------------------------------------------


def _validate(spec, value):
    value_type = spec["type"]

    if value_type in ("str", "secret", "path", "url"):
        value = str(value or "").strip()

        if not value:
            if spec.get("optional"):
                return "", None

            raise ValueError(
                f"{spec['label']} cannot be empty."
            )

        if value_type == "path":
            if not LOGIN_ROUTE_RE.match(value):
                raise ValueError(
                    f"{spec['label']} must be a relative route "
                    "starting with '/' (letters, numbers, "
                    "'/', '_', '-' only)."
                )
        elif value_type == "url":
            if not URL_RE.match(value):
                raise ValueError(
                    f"{spec['label']} must be an absolute "
                    "http(s) URL."
                )

        if value_type == "str" and "max_length" in spec:
            if len(value) > spec["max_length"]:
                raise ValueError(
                    f"{spec['label']} must be at most "
                    f"{spec['max_length']} characters."
                )

        return value, value

    if value_type == "int":
        parsed = _int(value, None)

        if parsed is None:
            raise ValueError(
                f"{spec['label']} must be a number."
            )

        if parsed < spec["min"] or parsed > spec["max"]:
            raise ValueError(
                f"{spec['label']} must be between "
                f"{spec['min']} and {spec['max']}."
            )

        return parsed, str(parsed)

    if value_type == "bool":
        parsed = _bool(value, False)

        return parsed, "true" if parsed else "false"

    if value_type == "select":
        value = str(value or "")

        if value not in spec["choices"]:
            raise ValueError(
                f"{spec['label']} must be one of: "
                + ", ".join(spec["choices"]) + "."
            )

        return value, value

    if value_type == "list":
        if not isinstance(value, list):
            raise ValueError(
                f"{spec['label']} must be a list."
            )

        from ipaddress import ip_network

        clean = []

        for item in value:
            raw = str(item or "").strip()

            if not raw:
                continue

            try:
                ip_network(raw, strict=False)
            except ValueError:
                raise ValueError(
                    f"Invalid network range: {raw}"
                )

            clean.append(raw)

        return clean, json.dumps(clean)

    raise ValueError(
        f"Unsupported setting type: {value_type}"
    )


def _log_audit(
    db: Session,
    username,
    role,
    action,
    section,
    key,
    old_value,
    new_value,
    ip,
):
    row = SettingsAudit(
        username=username,
        role=role,
        action=action,
        section=section,
        key=key,
        old_value=old_value,
        new_value=new_value,
        ip=ip,
        created_at=datetime.utcnow().isoformat(),
    )

    db.add(row)
    db.commit()


def apply_section(db: Session, section, payload, actor):
    """Persist a section update and audit every change."""

    meta = SECTIONS[section]

    username = actor.get("username") or "admin"
    role = actor.get("role") or "admin"
    ip = actor.get("ip") or ""

    changed = []

    values = dict(payload)

    if section == "email":
        from .email_settings_model import EmailSetting

        config = db.query(EmailSetting).first()

        normalized = {}

        for spec in meta["keys"]:
            key = spec["key"]

            if key not in values:
                continue

            raw = values[key]

            if key == "password":
                if raw in ("", "********"):
                    continue

                normalized[key] = str(raw).strip()
                continue

            value, norm = _validate(spec, raw)

            if key == "smtp_port":
                if config and int(config.smtp_port) == value:
                    continue

                normalized[key] = value
                changed.append((key, getattr(config, "smtp_port", None) if config else None, norm))

                continue

            old = getattr(config, key, None) if config else None

            if old is not None and str(old) == norm:
                continue

            normalized[key] = value
            changed.append((key, old, norm))

        if "password" in normalized:
            old = config.password if config else None

            if old != normalized["password"]:
                changed.append(("password", old, "********"))

        if config is None:
            from .email_settings_model import EmailSetting

            config = EmailSetting(
                smtp_server=normalized.get("smtp_server", ""),
                smtp_port=normalized.get("smtp_port", 587),
                username=normalized.get("username", ""),
                receiver=normalized.get("receiver", ""),
                password=normalized.get("password", ""),
            )
            db.add(config)
        else:
            for key, value in normalized.items():
                setattr(config, key, value)

        db.commit()

        for key, old_value, new_value in changed:
            _log_audit(
                db,
                username,
                role,
                "UPDATE",
                section,
                key,
                old_value,
                new_value,
                ip,
            )

        return {
            "section": section,
            "updated": changed,
        }

    if section == "exam_mode":
        normalized = {}

        for spec in meta["keys"]:
            key = spec["key"]

            if key not in values:
                continue

            value, norm = _validate(spec, values[key])

            normalized[key] = value

        if "usb_policy" in normalized:
            if normalized["usb_policy"] not in {
                "approval_required",
                "allow",
                "block",
            }:
                raise ValueError(
                    "usb_policy must be approval_required, "
                    "allow, or block"
                )

        existing = db.execute(
            text("""
                SELECT enabled, usb_policy
                FROM exam_mode_settings
                WHERE id = 1
            """)
        ).mappings().first()

        if existing is not None:
            if "usb_policy" not in normalized:
                normalized["usb_policy"] = existing["usb_policy"]
            if "enabled" not in normalized:
                normalized["enabled"] = existing["enabled"]

        enabled = normalized.get("enabled", False)
        usb_policy = normalized.get(
            "usb_policy",
            "approval_required",
        )

        if existing is None:
            db.execute(
                text("""
                    INSERT INTO exam_mode_settings (
                        id, enabled, usb_policy, updated_at
                    )
                    VALUES (1, :enabled, :policy, NOW())
                """),
                {
                    "enabled": enabled,
                    "policy": usb_policy,
                },
            )
        else:
            db.execute(
                text("""
                    UPDATE exam_mode_settings
                    SET
                        enabled = :enabled,
                        usb_policy = :policy,
                        updated_at = NOW()
                    WHERE id = 1
                """),
                {
                    "enabled": enabled,
                    "policy": usb_policy,
                },
            )

        db.commit()

        for key, value in normalized.items():
            old = existing[key] if existing else None

            if old is not None and str(old) == str(value):
                continue

            _log_audit(
                db,
                username,
                role,
                "UPDATE",
                section,
                key,
                old,
                str(value),
                ip,
            )

        return {
            "section": section,
            "updated": [
                (key, str(value))
                for key, value in normalized.items()
            ],
        }

    # monitor_settings-backed sections

    if section == "telegram":
        from .settings_model import SystemSetting

    for spec in meta["keys"]:
        key = spec["key"]

        if key not in values:
            continue

        raw = values[key]

        if spec["type"] == "secret":
            if raw in ("", MASKED_VALUE):
                continue

            value = str(raw).strip()

            if not value:
                raise ValueError(
                    f"{spec['label']} cannot be empty."
                )

            stored = encrypt_secret(value)
            new_text = MASKED_VALUE
        else:
            value, new_text = _validate(spec, raw)
            stored = new_text if new_text is not None else value

        old = get_setting(db, key)

        if new_text is None:
            if old is None or str(old) == "":
                continue

        if old is not None and spec["type"] != "secret":
            if str(old) == str(new_text):
                continue

        if old is None and new_text == str(spec["default"]):
            continue

        set_setting(db, key, stored)

        _log_audit(
            db,
            username,
            role,
            "UPDATE",
            section,
            key,
            old,
            new_text,
            ip,
        )

        changed.append((key, old, new_text))

        if section == "telegram" and key == "telegram_enabled":
            from .settings_model import SystemSetting

            toggle = (
                db.query(SystemSetting)
                .filter(SystemSetting.key == "telegram")
                .first()
            )

            if toggle is None:
                toggle = SystemSetting(
                    key="telegram",
                    value=value,
                )
                db.add(toggle)
            else:
                toggle.value = value

            db.commit()

    return {
        "section": section,
        "updated": changed,
    }


# ---------------------------------------------------------------------------
# Consumer helpers (DB-first with environment fallback)
# ---------------------------------------------------------------------------


def get_token_expire_minutes():
    db = SessionLocal()

    try:
        return _int(
            get_setting(db, "access_token_expire_minutes"),
            _int(
                __import__(
                    "app.config",
                    fromlist=["ACCESS_TOKEN_EXPIRE_MINUTES"],
                ).ACCESS_TOKEN_EXPIRE_MINUTES,
                60,
            ),
        )
    finally:
        db.close()


def get_telegram_config():
    """DB-first telegram config with env fallbacks."""

    import os

    from app.config import TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

    db = SessionLocal()

    try:
        from app.settings_model import SystemSetting

        toggle = (
            db.query(SystemSetting)
            .filter(SystemSetting.key == "telegram")
            .first()
        )

        if toggle is not None:
            enabled = bool(toggle.value)
        else:
            enabled = _bool(
                get_setting(db, "telegram_enabled"),
                TELEGRAM_ENABLED,
            )

        token = _secret_value(
            db,
            "telegram_bot_token",
            os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
        )

        chat_id = (
            get_setting(db, "telegram_chat_id")
            or os.getenv("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)
        )

        return {
            "enabled": enabled,
            "bot_token": token,
            "chat_id": chat_id,
        }
    finally:
        db.close()


def get_heartbeat_config():
    db = SessionLocal()

    try:
        return {
            "timeout_seconds": _int(
                get_setting(db, "heartbeat_timeout_seconds"),
                60,
            ),
            "check_interval_seconds": _int(
                get_setting(db, "heartbeat_check_interval_seconds"),
                15,
            ),
        }
    finally:
        db.close()


def get_alert_monitor_interval():
    db = SessionLocal()

    try:
        return _int(
            get_setting(db, "alert_monitor_interval_seconds"),
            15,
        )
    finally:
        db.close()


def get_camera_config():
    db = SessionLocal()

    try:
        return {
            "check_interval_seconds": _int(
                get_setting(db, "camera_check_interval_seconds"),
                30,
            ),
            "probe_timeout_seconds": _int(
                get_setting(db, "camera_probe_timeout_seconds"),
                3,
            ),
        }
    finally:
        db.close()


def get_provisioning_config():
    import os

    db = SessionLocal()

    try:
        url = (
            get_setting(db, "provisioning_api_url")
            or os.getenv("SMARTIT_PROVISIONING_API_URL", "").strip()
        )

        token = _secret_value(
            db,
            "provisioning_api_token",
            os.getenv("SMARTIT_PROVISIONING_API_TOKEN", "").strip(),
        )

        timeout = _int(
            get_setting(db, "provisioning_deploy_timeout_minutes"),
            _int(
                os.getenv("SMARTIT_DEPLOY_TIMEOUT_MINUTES", "60"),
                60,
            ),
        )

        return {
            "api_url": url,
            "api_token": token,
            "deploy_timeout_minutes": timeout,
        }
    finally:
        db.close()


def get_ws_ping_interval():
    db = SessionLocal()

    try:
        return _int(
            get_setting(db, "ws_ping_interval_seconds"),
            30,
        )
    finally:
        db.close()


def get_activity_upload_interval():
    db = SessionLocal()

    try:
        return _int(
            get_setting(db, "endpoint_activity_interval_seconds"),
            30,
        )
    finally:
        db.close()


def get_usb_default_policy():
    db = SessionLocal()

    try:
        policy = get_setting(
            db,
            "usb_default_policy",
            "approval_required",
        )

        if policy not in {"approval_required", "allow", "block"}:
            return "approval_required"

        return policy
    finally:
        db.close()


def get_retention_config():
    db = SessionLocal()

    try:
        return {
            "notification_history_days": _int(
                get_setting(db, "notification_history_retention_days"),
                30,
            ),
            "email_history_days": _int(
                get_setting(db, "email_history_retention_days"),
                30,
            ),
            "audit_days": _int(
                get_setting(db, "settings_audit_retention_days"),
                180,
            ),
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Retention cleanup thread
# ---------------------------------------------------------------------------


def _cleanup_once():
    db = SessionLocal()

    try:
        from app.email_history_model import EmailHistory
        from app.notification_history_model import NotificationHistory
        from app.settings_audit_model import SettingsAudit

        config = get_retention_config()

        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(
            days=config["notification_history_days"]
        )

        db.execute(
            text(
                "DELETE FROM notification_history "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff.isoformat()},
        )

        cutoff = datetime.utcnow() - timedelta(
            days=config["email_history_days"]
        )

        db.execute(
            text(
                "DELETE FROM email_history "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff.isoformat()},
        )

        cutoff = datetime.utcnow() - timedelta(
            days=config["audit_days"]
        )

        db.execute(
            text(
                "DELETE FROM settings_audit "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff.isoformat()},
        )

        db.commit()
    finally:
        db.close()


def start_settings_retention_cleanup():
    def _loop():
        while True:
            try:
                _cleanup_once()
            except Exception:
                pass

            time.sleep(24 * 60 * 60)

    thread = threading.Thread(
        target=_loop,
        daemon=True,
    )

    thread.start()
