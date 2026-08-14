import json
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import SessionLocal
from .threat_model import ThreatAudit, ThreatEvent
from .websocket_manager import manager

# ---------------------------------------------------------------------------
# Canonical vocabulary
# ---------------------------------------------------------------------------

CATEGORY_DISPLAY = {
    "trojan": "Trojan",
    "ransomware": "Ransomware",
    "spyware": "Spyware",
    "malware": "Malware",
    "malicious_script": "Malicious Script",
    "suspicious_file": "Suspicious File",
    "pua": "Potentially Unwanted Application",
    "safe_file": "Safe File",
}

CONFIRMED_CATEGORIES = {
    "trojan",
    "ransomware",
    "spyware",
    "malware",
    "malicious_script",
}

SUSPICIOUS_CATEGORIES = {
    "suspicious_file",
    "pua",
}

VALID_SEVERITIES = {"CRITICAL", "HIGH", "WARNING", "INFO"}

VALID_STATUSES = {
    "DETECTED",
    "BLOCKED",
    "QUARANTINED",
    "UNDER_REVIEW",
    "ALLOWED",
    "RESTORED",
    "RESOLVED",
}

ADMIN_ACTIONS = {
    "keep_blocked": "BLOCKED",
    "quarantine": "QUARANTINED",
    "mark_safe": "ALLOWED",
    "restore": "RESTORED",
    "resolve": "RESOLVED",
}

# Default severity when an agent does not specify one.
SEVERITY_BY_CATEGORY = {
    "trojan": "CRITICAL",
    "ransomware": "CRITICAL",
    "spyware": "HIGH",
    "malware": "HIGH",
    "malicious_script": "HIGH",
    "suspicious_file": "WARNING",
    "pua": "WARNING",
    "safe_file": "INFO",
}

ALERT_TYPE_BY_CATEGORY = {
    "trojan": "TROJAN_DETECTED",
    "ransomware": "RANSOMWARE_DETECTED",
    "spyware": "SPYWARE_DETECTED",
    "malware": "MALWARE_DETECTED",
    "malicious_script": "MALICIOUS_SCRIPT",
    "suspicious_file": "SUSPICIOUS_FILE",
    "pua": "POTENTIALLY_UNWANTED_APP",
}

# ---------------------------------------------------------------------------
# Settings keys
# ---------------------------------------------------------------------------

ENABLED_KEY = "endpoint_threat_enabled"
SCAN_POLICY_KEY = "threat_scan_policy"
QUARANTINE_POLICY_KEY = "threat_quarantine_policy"
SUSPICIOUS_HANDLING_KEY = "threat_suspicious_handling"
NOTIFY_CRITICAL_KEY = "threat_notify_critical"
RETENTION_DAYS_KEY = "threat_retention_days"
SCAN_INTERVAL_KEY = "threat_scan_interval_seconds"


def get_threat_settings(db: Session):
    """Return the endpoint-threat policy read from monitor_settings."""

    from .monitor_settings_model import MonitorSetting

    def _get(key, default):
        row = (
            db.query(MonitorSetting)
            .filter(MonitorSetting.key == key)
            .first()
        )
        if row is None:
            return default
        return row.value

    return {
        "enabled": str(_get(ENABLED_KEY, "true")).lower() in ("1", "true", "yes", "on"),
        "scan_policy": _get(SCAN_POLICY_KEY, "real_time"),
        "quarantine_policy": _get(QUARANTINE_POLICY_KEY, "auto"),
        "suspicious_handling": _get(SUSPICIOUS_HANDLING_KEY, "block"),
        "notify_critical": str(_get(NOTIFY_CRITICAL_KEY, "true")).lower() in ("1", "true", "yes", "on"),
        "retention_days": _int(_get(RETENTION_DAYS_KEY, "30"), 30),
        "scan_interval_seconds": _int(_get(SCAN_INTERVAL_KEY, "30"), 30),
    }


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def serialize_threat(threat, audit=None):
    return {
        "id": threat.id,
        "device_id": threat.device_id,
        "hostname": threat.hostname,
        "file_name": threat.file_name,
        "file_path": threat.file_path,
        "file_type": threat.file_type,
        "file_hash": threat.file_hash,
        "detection_name": threat.detection_name,
        "category": threat.category,
        "severity": threat.severity,
        "detection_source": threat.detection_source,
        "action": threat.action,
        "status": threat.status,
        "username": threat.username,
        "source": threat.source,
        "usb_request_id": threat.usb_request_id,
        "quarantine_path": threat.quarantine_path,
        "quarantine_method": threat.quarantine_method,
        "escalated": bool(threat.escalated),
        "action_required": bool(threat.action_required),
        "reviewed_by": threat.reviewed_by,
        "reviewed_at": _iso(threat.reviewed_at),
        "notes": threat.notes,
        "created_at": _iso(threat.created_at),
        "detected_at": _iso(threat.detected_at),
        "updated_at": _iso(threat.updated_at),
        "audit": audit or [],
    }


# ---------------------------------------------------------------------------
# Threat submission from the agent
# ---------------------------------------------------------------------------

SAFE_HANDLING_ACTION = "allowed"
SUSPICIOUS_HANDLING_ACTIONS = {"block", "review", "notify"}


def _category_key(raw):
    """Map a category string (display or key form) to a canonical key."""

    text_val = str(raw or "").strip()

    if text_val.lower() in CATEGORY_DISPLAY:
        return text_val.lower()

    for key, display in CATEGORY_DISPLAY.items():
        if text_val.lower() == display.lower():
            return key

    return "suspicious_file"


def ingest_threat(db: Session, agent_device, payload):
    """Record a detected/safe file event reported by an enrolled agent.

    Applies the site policy to decide the resulting status:
    - confirmed malicious -> automatically blocked & quarantined
    - suspicious/unknown   -> blocked / held for admin review per policy
    - safe                 -> allowed (no alert)

    Returns the serialized threat.
    """

    from .models import Device

    device = (
        db.query(Device)
        .filter(Device.id == int(agent_device["id"]))
        .first()
    )

    if device is None:
        device = Device(
            id=int(agent_device["id"]),
            hostname=agent_device.get("hostname") or "unknown-agent",
        )
        # Best effort: the device normally exists because the agent is
        # authenticated against the devices table.

    category = _category_key(payload.get("category"))
    display = CATEGORY_DISPLAY.get(category, category)

    file_name = str(payload.get("file_name") or "")[:255]
    file_path = str(payload.get("file_path") or "")[:1024]
    file_hash = str(payload.get("file_hash") or "").lower()[:64]
    detection_name = str(payload.get("detection_name") or "")[:255]
    detection_source = str(payload.get("detection_source") or "")[:128]
    username = str(payload.get("username") or "")[:128]
    source = str(payload.get("source") or "").strip()[:32]
    file_type = str(payload.get("file_type") or "")[:64]

    if not file_name:
        file_name = file_hash[:16] or "unknown-file"

    # Per-status dedup: ignore an identical active detection that the agent
    # is re-reporting on the next poll cycle.
    existing = (
        db.query(ThreatEvent)
        .filter(
            ThreatEvent.device_id == int(agent_device["id"]),
            ThreatEvent.file_hash == file_hash,
            ThreatEvent.category == display,
            ThreatEvent.status.in_(
                ("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW", "ALLOWED")
            ),
        )
        .first()
    )

    if existing is not None:
        return serialize_threat(existing)

    settings = get_threat_settings(db)

    severity = str(payload.get("severity") or SEVERITY_BY_CATEGORY.get(category, "WARNING")).upper()
    if severity not in VALID_SEVERITIES:
        severity = SEVERITY_BY_CATEGORY.get(category, "WARNING")

    quarantine_policy = settings["quarantine_policy"]
    suspicious_handling = settings["suspicious_handling"]

    action_from_agent = str(payload.get("action") or "").strip().lower()
    quarantine_path = str(payload.get("quarantine_path") or "")[:1024]
    quarantine_method = str(payload.get("quarantine_method") or "")[:128]

    status = "DETECTED"
    action = action_from_agent or "none"
    action_required = False
    alert_created = ""

    detected_at = _parse_event_time(payload.get("detected_at"))

    if category == "safe_file":
        status = "ALLOWED"
        action = action or "allowed"

    elif category in CONFIRMED_CATEGORIES:
        # Confirmed malicious files are never held for approval.
        status = "QUARANTINED"
        action = action or "block_and_quarantine"
        quarantine_path = quarantine_path or ""
        quarantine_method = quarantine_method or "agent_isolated"
        action_required = False
        alert_type = ALERT_TYPE_BY_CATEGORY.get(category, "MALWARE_DETECTED")
        alert_created = _raise_threat_alert(
            db,
            device,
            settings,
            alert_type,
            severity,
            file_name,
            display,
            detected_at,
            _iso(detected_at),
            level="admin",
        )
    elif category in SUSPICIOUS_CATEGORIES:
        if suspicious_handling == "review":
            status = "UNDER_REVIEW"
            action_required = True
        elif suspicious_handling == "notify":
            status = "DETECTED"
            action_required = False
        else:  # "block"
            status = "BLOCKED"
            action_required = True

        action = action or (
            "quarantined"
            if quarantine_policy == "auto" and action_from_agent in ("", "quarantined")
            else "blocked"
        )
        alert_created = _raise_threat_alert(
            db,
            device,
            settings,
            "SUSPICIOUS_FILE",
            severity,
            file_name,
            display,
            detected_at,
            _iso(detected_at),
            level="warn",
        )

    threat = ThreatEvent(
        device_id=int(agent_device["id"]),
        hostname=agent_device.get("hostname") or device.hostname,
        file_name=file_name,
        file_path=file_path,
        file_type=file_type,
        file_hash=file_hash,
        detection_name=detection_name,
        category=display,
        severity=severity,
        detection_source=detection_source,
        action=action,
        status=status,
        username=username,
        source=source,
        usb_request_id=_optional_int(payload.get("usb_request_id")),
        quarantine_path=quarantine_path,
        quarantine_method=quarantine_method,
        escalated=False,
        action_required=action_required,
        notes=str(payload.get("notes") or "")[:2000],
        detected_at=detected_at,
    )

    db.add(threat)
    db.commit()
    db.refresh(threat)

    if status == "QUARANTINED":
        _record_endpoint_activity(
            db,
            agent_device,
            "threat_quarantined",
            file_name,
            "Threat quarantined",
        )
    elif status == "BLOCKED":
        _record_endpoint_activity(
            db,
            agent_device,
            "threat_blocked",
            file_name,
            "Threat blocked",
        )
    elif status == "ALLOWED":
        _record_endpoint_activity(
            db,
            agent_device,
            "threat_allowed",
            file_name,
            "File allowed",
        )
    else:
        _record_endpoint_activity(
            db,
            agent_device,
            "threat_detected",
            file_name,
            f"Threat detected: {display}",
        )

    _broadcast_threat("threat_detected", threat)

    if source == "usb":
        _handle_usb_threat(
            db,
            agent_device,
            threat,
            status,
            settings,
        )

    return serialize_threat(threat)


def _optional_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_event_time(raw):
    if raw:
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except ValueError:
            pass

    return datetime.utcnow()


def _raise_threat_alert(db, device, settings, alert_type, severity, file_name, category, detected_at, detected_iso, level="admin"):
    """Create an alert through the existing alert pipeline (deduped).

    The alert service owns cooldown/deduplication and also forwards the
    notification to Telegram and email when configured.
    """

    from .services.alert_service import create_alert

    if not settings["enabled"]:
        return ""

    # Only alert on real threats (never on safe files).
    alert = create_alert(
        db,
        device,
        alert_type,
        None,
        severity if severity in ("CRITICAL", "HIGH", "WARNING") else "WARNING",
        (
            f"{category} detected on {device.hostname}: {file_name} "
            f"({detected_iso})"
        ),
    )

    request_status = ""
    if alert is not None:
        try:
            request_status = str(alert.id)
        except Exception:
            request_status = ""

    return request_status


def _record_endpoint_activity(db, agent_device, event_type, application, description):
    """Best-effort record of a threat event in the endpoint activity feed."""

    try:
        from .services.endpoint_activity_service import ingest_endpoint_events

        ingest_endpoint_events(
            db,
            agent_device,
            {
                "events": [
                    {
                        "event_type": event_type,
                        "application": application,
                        "description": description,
                        "metadata": {},
                    }
                ]
            },
        )
    except Exception:
        db.rollback()


def _broadcast_threat(event_type, threat):
    try:
        manager.broadcast_from_thread(
            {
                "type": event_type,
                "threat": serialize_threat(threat),
            }
        )
    except Exception:
        pass


def _handle_usb_threat(db, agent_device, threat, status, settings):
    """Associate a USB-sourced threat with its USB request and alert."""

    usb_request_id = threat.usb_request_id
    if not usb_request_id:
        return

    try:
        row = db.execute(
            text("""
                SELECT id, status
                FROM usb_requests
                WHERE id = :usb_request_id
            """),
            {"usb_request_id": usb_request_id},
        ).mappings().first()

        if row is not None:
            db.execute(
                text("""
                    UPDATE usb_requests
                    SET status = 'threat_blocked'
                    WHERE id = :usb_request_id
                      AND status NOT IN ('approved')
                """),
                {"usb_request_id": usb_request_id},
            )
            db.commit()
    except Exception:
        db.rollback()


def _serialize_usb_event(event, threat):
    return {}


# ---------------------------------------------------------------------------
# Admin review / status changes
# ---------------------------------------------------------------------------


def apply_admin_action(db: Session, threat_id, action, username, note=""):
    """Apply an administrator decision to a threat and audit it.

    Supported actions: keep_blocked, quarantine, mark_safe, restore, resolve.
    """

    if action not in ADMIN_ACTIONS:
        raise ValueError(f"Unsupported admin action: {action}")

    threat = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.id == int(threat_id))
        .first()
    )

    if threat is None:
        raise ValueError("Threat not found")

    new_status = ADMIN_ACTIONS[action]

    old_status = threat.status
    threat.status = new_status
    threat.escalated = True
    threat.action_required = False
    threat.reviewed_by = username
    threat.reviewed_at = datetime.utcnow()

    if action == "restore":
        threat.quarantine_path = ""
        threat.quarantine_method = ""

    if note:
        threat.notes = f"{threat.notes}\n[{username}] {note}".strip()[:4000]

    threat.updated_at = datetime.utcnow()
    db.commit()

    audit_entry = ThreatAudit(
        threat_id=threat.id,
        username=username,
        action=action,
        detail=_action_detail(action, note),
    )
    db.add(audit_entry)
    db.commit()

    _record_endpoint_activity(
        db,
        {
            "id": threat.device_id,
            "hostname": threat.hostname or "",
        },
        _activity_type_for_action(action),
        threat.file_name,
        f"Admin {action} for {threat.file_name} (threat {threat.id})",
    )

    if action in ("restore", "resolve", "mark_safe"):
        _resolve_threat_alerts(db, threat)

    _broadcast_threat("threat_update", threat)

    audit_rows = (
        db.query(ThreatAudit)
        .filter(ThreatAudit.threat_id == threat.id)
        .order_by(ThreatAudit.id.desc())
        .limit(50)
        .all()
    )

    return serialize_threat(
        threat,
        audit=[
            {
                "id": entry.id,
                "username": entry.username,
                "action": entry.action,
                "detail": entry.detail,
                "created_at": _iso(entry.created_at),
            }
            for entry in audit_rows
        ],
    )


def _action_detail(action, note):
    if note:
        return f"action={action}; note={note.strip()[:500]}"
    return f"action={action}"


def _activity_type_for_action(action):
    return {
        "keep_blocked": "threat_blocked",
        "quarantine": "threat_quarantined",
        "mark_safe": "threat_allowed",
        "restore": "threat_restored",
        "resolve": "threat_resolved",
    }.get(action, "threat_resolved")


def _resolve_threat_alerts(db, threat):
    """Resolve OPEN threat alerts for this device/file."""

    try:
        from .alert_model import Alert

        open_alerts = (
            db.query(Alert)
            .filter(
                Alert.device_id == threat.device_id,
                Alert.status == "OPEN",
            )
            .all()
        )

        if not open_alerts:
            return

        now = datetime.utcnow()

        for alert in open_alerts:
            alert.status = "RESOLVED"
            alert.resolved_at = now

        db.commit()
    except Exception:
        db.rollback()


def get_threat(db: Session, threat_id):
    threat = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.id == int(threat_id))
        .first()
    )

    if threat is None:
        return None

    audit_rows = (
        db.query(ThreatAudit)
        .filter(ThreatAudit.threat_id == threat.id)
        .order_by(ThreatAudit.id.desc())
        .limit(50)
        .all()
    )

    return serialize_threat(
        threat,
        audit=[
            {
                "id": entry.id,
                "username": entry.username,
                "action": entry.action,
                "detail": entry.detail,
                "created_at": _iso(entry.created_at),
            }
            for entry in audit_rows
        ],
    )


# ---------------------------------------------------------------------------
# Listing / filtering
# ---------------------------------------------------------------------------


def list_threats(db: Session, filters):
    where = []
    params = {}

    status = filters.get("status")
    if status:
        where.append("status = :status")
        params["status"] = status

    severity = filters.get("severity")
    if severity:
        where.append("severity = :severity")
        params["severity"] = severity

    category = filters.get("category")
    if category:
        where.append("category = :category")
        params["category"] = category

    device_id = filters.get("device_id")
    if device_id:
        where.append("device_id = :device_id")
        params["device_id"] = int(device_id)

    search = filters.get("search")
    if search:
        where.append(
            "(hostname ILIKE :search OR file_name ILIKE :search "
            "OR file_path ILIKE :search OR detection_name ILIKE :search "
            "OR file_hash ILIKE :search)"
        )
        params["search"] = f"%{search}%"

    if filters.get("active_only"):
        where.append(
            "status NOT IN ('ALLOWED', 'RESOLVED', 'RESTORED')"
        )

    if filters.get("critical_only"):
        where.append("severity = 'CRITICAL'")

    if filters.get("action_required"):
        where.append("action_required = TRUE")

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    sort_map = {
        "oldest": ("detected_at", "ASC"),
        "severity": ("severity", "DESC"),
    }

    col, direction = sort_map.get(
        filters.get("sort", "newest"),
        ("detected_at", "DESC"),
    )

    limit = min(max(_int(filters.get("limit"), 100), 1), 500)
    offset = max(_int(filters.get("offset"), 0), 0)

    total = db.execute(
        text(f"SELECT COUNT(*) AS c FROM threat_events{where_sql}"),
        params,
    ).mappings().first()["c"]

    rows = db.execute(
        text(f"""
            SELECT id
            FROM threat_events
            {where_sql}
            ORDER BY {col} {direction}, id {direction}
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    items = []

    for row in rows:
        threat = (
            db.query(ThreatEvent)
            .filter(ThreatEvent.id == row["id"])
            .first()
        )
        if threat is not None:
            items.append(serialize_threat(threat))

    return items, total


def threat_analytics(db: Session):
    """Summary counts + recent critical threats for dashboard/reporting."""

    active = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.status.in_(("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")))
        .count()
    )

    critical = (
        db.query(ThreatEvent)
        .filter(
            ThreatEvent.severity == "CRITICAL",
            ThreatEvent.status.in_(("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")),
        )
        .count()
    )

    quarantined = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.status == "QUARANTINED")
        .count()
    )

    devices_affected = (
        db.query(ThreatEvent.device_id)
        .filter(ThreatEvent.status.in_(("DETECTED", "BLOCKED", "QUARANTINED", "UNDER_REVIEW")))
        .distinct()
        .count()
    )

    resolved = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.status.in_(("RESOLVED", "RESTORED", "ALLOWED")))
        .count()
    )

    under_review = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.status == "UNDER_REVIEW", ThreatEvent.action_required.is_(True))
        .count()
    )

    by_severity = [
        {"name": name, "value": value}
        for name, value in (
            db.query(ThreatEvent.severity, text("COUNT(*)"))
            .group_by(ThreatEvent.severity)
            .all()
        )
    ]

    by_category = [
        {"name": name, "value": value}
        for name, value in (
            db.query(ThreatEvent.category, text("COUNT(*)"))
            .group_by(ThreatEvent.category)
            .all()
        )
    ]

    quarantine_history = [
        {
            "name": name,
            "value": value,
        }
        for name, value in (
            db.query(ThreatEvent.quarantine_method, text("COUNT(*)"))
            .filter(ThreatEvent.quarantine_method != "")
            .group_by(ThreatEvent.quarantine_method)
            .all()
        )
    ]

    admin_actions = [
        {
            "name": name,
            "value": value,
        }
        for name, value in (
            db.query(ThreatAudit.action, text("COUNT(*)"))
            .group_by(ThreatAudit.action)
            .all()
        )
    ]

    recent_critical = (
        db.query(ThreatEvent)
        .filter(ThreatEvent.severity == "CRITICAL")
        .order_by(ThreatEvent.detected_at.desc())
        .limit(10)
        .all()
    )

    return {
        "active": active,
        "critical": critical,
        "quarantined": quarantined,
        "devices_affected": devices_affected,
        "resolved": resolved,
        "under_review": under_review,
        "by_severity": by_severity,
        "by_category": by_category,
        "quarantine_history": quarantine_history,
        "admin_actions": admin_actions,
        "recent_critical": [serialize_threat(t) for t in recent_critical],
    }


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def retention_cleanup(db: Session):
    """Delete threat events older than the configured retention window."""

    retention_days = get_threat_settings(db)["retention_days"]

    if retention_days <= 0:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    result = db.execute(
        text("DELETE FROM threat_events WHERE detected_at < :cutoff"),
        {"cutoff": cutoff},
    )

    db.commit()

    return result.rowcount


def start_threat_cleanup():
    """Start the retention cleanup thread (runs once per process)."""

    for thread in threading.enumerate():
        if thread.name == "threat_cleanup":
            return

    def run():
        while True:
            try:
                db = SessionLocal()
                try:
                    retention_cleanup(db)
                finally:
                    db.close()
            except Exception:
                pass

            time.sleep(6 * 60 * 60)  # every 6 hours

    thread = threading.Thread(
        target=run,
        name="threat_cleanup",
        daemon=True,
    )

    thread.start()

    return thread