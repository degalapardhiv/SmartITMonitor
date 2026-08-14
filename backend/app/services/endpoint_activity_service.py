import csv
import io
import json
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import text

from ..database import SessionLocal
from ..websocket_manager import manager
from .settings_service import get_setting, set_setting

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EVENT_TYPES = {
    "app_launched",
    "app_closed",
    "browser_opened",
    "browser_closed",
    "url_visited",
    "user_login",
    "user_logout",
    "usb_connected",
    "usb_removed",
    "software_installed",
    "software_removed",
    "system_boot",
    "system_event",
    "network_connected",
    "network_disconnected",
    "security_failed_auth",
    "security_privilege_escalation",
    "security_usb_rejected",
    "threat_detected",
    "threat_blocked",
    "threat_quarantined",
    "threat_restored",
    "threat_allowed",
    "threat_resolved",
    "usb_threat_detected",
}

URL_AUDITING_KEY = "endpoint_url_auditing"
RETENTION_DAYS_KEY = "endpoint_retention_days"

DEFAULT_URL_AUDITING = "false"
DEFAULT_RETENTION_DAYS = "30"

MAX_BATCH_EVENTS = 100
MAX_DESCRIPTION_LENGTH = 2000
MAX_METADATA_LENGTH = 4000

# Keys that are never persisted, even if an agent sends them.
SENSITIVE_METADATA_KEYS = {
    "password",
    "token",
    "keystrokes",
    "clipboard",
    "message",
    "content",
    "secret",
    "cookie",
}

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def get_activity_settings(db):
    """Return endpoint activity settings (URL auditing + retention days)."""

    return {
        "url_auditing": (
            (get_setting(db, URL_AUDITING_KEY) or DEFAULT_URL_AUDITING)
            .lower() == "true"
        ),
        "retention_days": _parse_int(
            get_setting(db, RETENTION_DAYS_KEY),
            DEFAULT_RETENTION_DAYS,
        ),
    }


def save_activity_settings(db, url_auditing=None, retention_days=None):
    if url_auditing is not None:
        set_setting(db, URL_AUDITING_KEY, "true" if url_auditing else "false")

    if retention_days is not None:
        retention_days = max(1, min(int(retention_days), 3650))
        set_setting(db, RETENTION_DAYS_KEY, str(retention_days))

    return get_activity_settings(db)


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


# ---------------------------------------------------------------------------
# Admin audit trail
# ---------------------------------------------------------------------------


def record_activity_audit(db, username, action, detail=""):
    db.execute(
        text("""
            INSERT INTO activity_audit (username, action, detail, created_at)
            VALUES (:username, :action, :detail, :created_at)
        """),
        {
            "username": username,
            "action": action,
            "detail": detail,
            "created_at": datetime.utcnow(),
        },
    )
    db.commit()


def get_activity_audit(db, limit=50):
    rows = db.execute(
        text("""
            SELECT id, username, action, detail, created_at
            FROM activity_audit
            ORDER BY id DESC
            LIMIT :limit
        """),
        {"limit": limit},
    ).mappings().all()

    return [
        {
            "id": row["id"],
            "username": row["username"],
            "action": row["action"],
            "detail": row["detail"],
            "created_at": _iso(row["created_at"]),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Serialization / ingestion
# ---------------------------------------------------------------------------


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _serialize_event(row):
    metadata = None

    if row.get("metadata"):
        try:
            metadata = json.loads(row["metadata"])
        except (TypeError, ValueError):
            metadata = None

    return {
        "id": row["id"],
        "device_id": row["device_id"],
        "hostname": row["hostname"],
        "username": row["username"],
        "event_type": row["event_type"],
        "application": row["application"],
        "domain": row["domain"],
        "url": row["url"],
        "description": row["description"],
        "metadata": metadata,
        "timestamp": _iso(row["timestamp"]),
    }


def _extract_domain(url):
    if not url:
        return None

    try:
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return parsed.netloc.lower()
    except ValueError:
        pass

    return None


def _normalize_event(raw, allow_url):
    """Validate and normalize a single activity event from an agent."""

    event_type = str(raw.get("event_type") or "").strip()

    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"Unsupported event type: {event_type}")

    username = str(raw.get("username") or "").strip()[:128] or ""
    application = str(raw.get("application") or "").strip()[:128] or ""
    description = str(raw.get("description") or "").strip()[:MAX_DESCRIPTION_LENGTH]

    metadata = raw.get("metadata") or {}

    if isinstance(metadata, dict):
        for key in SENSITIVE_METADATA_KEYS:
            metadata.pop(key, None)
        metadata = json.dumps(metadata, default=str)[:MAX_METADATA_LENGTH]
    else:
        metadata = ""

    url = ""
    domain = ""

    if allow_url:
        url = str(raw.get("url") or "").strip()[:2000]
        domain = (
            str(raw.get("domain") or "").strip()[:255]
            or _extract_domain(url)
            or ""
        )

    return {
        "username": username,
        "event_type": event_type,
        "application": application,
        "domain": domain,
        "url": url,
        "description": description,
        "metadata": metadata,
    }


def _parse_event_time(raw):
    timestamp = raw.get("timestamp")

    if timestamp:
        try:
            parsed = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )
            if parsed.tzinfo:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except ValueError:
            pass

    return datetime.utcnow()


def ingest_endpoint_events(db, agent_device, payload):
    """Store activity events submitted by an enrolled device.

    Returns the number of events stored.
    """

    events = payload.get("events") or []

    if not isinstance(events, list) or not events:
        return 0

    if len(events) > MAX_BATCH_EVENTS:
        raise ValueError(f"Too many events in one batch (max {MAX_BATCH_EVENTS})")

    allow_url = get_activity_settings(db)["url_auditing"]

    device_id = int(agent_device["id"])
    hostname = agent_device.get("hostname") or ""
    now = datetime.utcnow()

    stored = []

    for raw in events:
        if not isinstance(raw, dict):
            continue

        normalized = _normalize_event(raw, allow_url)

        timestamp = _parse_event_time(raw)

        if timestamp > now + timedelta(minutes=5):
            timestamp = now

        db.execute(
            text("""
                INSERT INTO endpoint_activity (
                    device_id,
                    hostname,
                    username,
                    event_type,
                    application,
                    domain,
                    url,
                    description,
                    metadata,
                    timestamp
                )
                VALUES (
                    :device_id,
                    :hostname,
                    :username,
                    :event_type,
                    :application,
                    :domain,
                    :url,
                    :description,
                    :metadata,
                    :timestamp
                )
            """),
            {
                "device_id": device_id,
                "hostname": hostname,
                "username": normalized["username"],
                "event_type": normalized["event_type"],
                "application": normalized["application"],
                "domain": normalized["domain"],
                "url": normalized["url"],
                "description": normalized["description"],
                "metadata": normalized["metadata"],
                "timestamp": timestamp,
            },
        )

        stored.append({
            "id": None,
            "device_id": device_id,
            "hostname": hostname,
            "username": normalized["username"],
            "event_type": normalized["event_type"],
            "application": normalized["application"],
            "domain": normalized["domain"],
            "url": normalized["url"],
            "description": normalized["description"],
            "metadata": normalized["metadata"],
            "timestamp": timestamp,
        })

    db.commit()

    for row in stored:
        result = db.execute(
            text("""
                SELECT id
                FROM endpoint_activity
                WHERE device_id = :device_id
                  AND timestamp = :timestamp
                ORDER BY id DESC
                LIMIT 1
            """),
            {"device_id": row["device_id"], "timestamp": row["timestamp"]},
        ).mappings().first()

        if result:
            row["id"] = result["id"]

    # Live WebSocket updates for connected dashboards.
    for row in stored:
        try:
            manager.broadcast_from_thread({
                "type": "endpoint_activity",
                "event": _serialize_event(row),
            })
        except Exception:
            pass

    return len(stored)


def add_usb_rejected_event(db, device, reason):
    """Record a USB rejection as a security activity event (best effort)."""

    try:
        ingest_endpoint_events(
            db,
            {"id": device["id"], "hostname": device.get("hostname") or ""},
            {
                "events": [{
                    "event_type": "security_usb_rejected",
                    "description": "USB request rejected",
                    "metadata": {"reason": reason},
                }]
            },
        )
    except Exception:
        db.rollback()


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def _build_filters(filters):
    where = []
    params = {}

    if filters.get("device_id"):
        where.append("device_id = :device_id")
        params["device_id"] = int(filters["device_id"])

    if filters.get("event_type"):
        where.append("event_type = :event_type")
        params["event_type"] = filters["event_type"]

    if filters.get("from"):
        where.append("timestamp >= :from_ts")
        params["from_ts"] = filters["from"]

    if filters.get("to"):
        where.append("timestamp <= :to_ts")
        params["to_ts"] = filters["to"]

    if filters.get("search"):
        where.append(
            "(hostname ILIKE :search OR username ILIKE :search "
            "OR application ILIKE :search OR domain ILIKE :search "
            "OR description ILIKE :search)"
        )
        params["search"] = f"%{filters['search']}%"

    where_sql = " WHERE " + " AND ".join(where) if where else ""

    return where_sql, params


def list_events(db, filters):
    """Return (items, total) for admin queries."""

    where_sql, params = _build_filters(filters)

    sort = "ASC" if filters.get("sort") == "oldest" else "DESC"

    limit = min(max(int(filters.get("limit", 50)), 1), 200)
    offset = max(int(filters.get("offset", 0)), 0)

    total = db.execute(
        text(f"SELECT COUNT(*) AS c FROM endpoint_activity{where_sql}"),
        params,
    ).mappings().first()["c"]

    rows = db.execute(
        text(f"""
            SELECT id, device_id, hostname, username, event_type, application,
                   domain, url, description, metadata, timestamp
            FROM endpoint_activity
            {where_sql}
            ORDER BY timestamp {sort}, id {sort}
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()

    return [_serialize_event(row) for row in rows], total


def list_devices(db):
    """Distinct devices that have submitted activity (for filter dropdowns)."""

    rows = db.execute(
        text("""
            SELECT device_id, hostname, MAX(timestamp) AS last_seen,
                   COUNT(*) AS event_count
            FROM endpoint_activity
            GROUP BY device_id, hostname
            ORDER BY hostname
        """)
    ).mappings().all()

    return [
        {
            "device_id": row["device_id"],
            "hostname": row["hostname"],
            "last_seen": _iso(row["last_seen"]),
            "event_count": row["event_count"],
        }
        for row in rows
    ]


def list_event_types(db):
    rows = db.execute(
        text("""
            SELECT DISTINCT event_type
            FROM endpoint_activity
            ORDER BY event_type
        """)
    ).mappings().all()

    return [row["event_type"] for row in rows]


def export_csv(db, filters):
    """Return filtered events as CSV text."""

    where_sql, params = _build_filters(filters)

    rows = db.execute(
        text(f"""
            SELECT id, device_id, hostname, username, event_type, application,
                   domain, url, description, timestamp
            FROM endpoint_activity
            {where_sql}
            ORDER BY timestamp DESC, id DESC
        """),
        params,
    ).mappings().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow([
        "id", "device_id", "hostname", "username", "event_type",
        "application", "domain", "url", "description", "timestamp",
    ])

    for row in rows:
        writer.writerow([
            row["id"],
            row["device_id"],
            row["hostname"],
            row["username"],
            row["event_type"],
            row["application"],
            row["domain"],
            row["url"],
            row["description"],
            _iso(row["timestamp"]),
        ])

    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def retention_cleanup(db):
    """Delete events older than the configured retention window."""

    retention_days = get_activity_settings(db)["retention_days"]
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    result = db.execute(
        text("""
            DELETE FROM endpoint_activity
            WHERE timestamp < :cutoff
        """),
        {"cutoff": cutoff},
    )

    db.commit()

    return result.rowcount


def start_endpoint_activity_cleanup():
    """Start the retention cleanup thread (runs once per process)."""

    for thread in threading.enumerate():
        if thread.name == "endpoint_activity_cleanup":
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
        name="endpoint_activity_cleanup",
        daemon=True,
    )

    thread.start()

    return thread
