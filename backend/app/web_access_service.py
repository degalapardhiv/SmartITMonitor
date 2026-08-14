from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Device
from .software_deployment_model import DeviceGroup, DeviceGroupMember
from .web_access_model import (
    WebAccessDomainEntry,
    WebAccessPolicy,
    WebAccessPolicyDevice,
    WebAccessSyncLog,
    WebAccessTarget,
)

VALID_ACTIONS = {
    "allowlist",
    "blocklist",
}

VALID_TARGET_TYPES = {
    "all",
    "group",
    "department",
    "lab",
    "location",
    "device",
}

DEVICE_STATUSES = {
    "pending",
    "synced",
    "failed",
    "not_applicable",
}

# Settings keys
ENABLED_KEY = "web_access_enabled"
POLL_INTERVAL_KEY = "web_access_poll_interval_seconds"


def _now():
    return datetime.utcnow()


def normalize_domain(raw):
    """Return (domain, error) with a canonical lowercase domain."""
    text = (raw or "").strip().lower()

    if not text:
        return "", "Domain is required"

    scheme_index = text.find("://")

    if scheme_index != -1:
        text = text[scheme_index + 3:]

    if "/" in text:
        text = text.split("/", 1)[0]

    if "#" in text:
        text = text.split("#", 1)[0]

    if "@" in text:
        return "", "Domain must not contain user credentials"

    if text.startswith("www."):
        text = text[4:]

    if ":" in text:
        text = text.split(":", 1)[0]

    text = text.strip(".")

    if not text or " " in text or text.count(".") < 1:
        return "", f"Invalid domain: {raw!r}"

    for char in text:
        if not (char.isalnum() or char in ".-"):
            return "", f"Invalid character {char!r} in domain {raw!r}"

    try:
        text = text.encode("idna").decode("ascii")
    except UnicodeError:
        return "", f"Domain could not be normalized: {raw!r}"

    return text, ""


def _domain_query(db, policy_id):
    return (
        db.query(WebAccessDomainEntry)
        .filter(WebAccessDomainEntry.policy_id == policy_id)
        .order_by(WebAccessDomainEntry.domain.asc())
    )


def _target_query(db, policy_id):
    return (
        db.query(WebAccessTarget)
        .filter(WebAccessTarget.policy_id == policy_id)
        .order_by(WebAccessTarget.id.asc())
    )


def resolve_policy_devices(db: Session, policy):
    """Return Device rows currently targeted by a policy's targets.

    Targets are OR-ed together: a device is included if it matches any
    single target (all, department, lab, location, group, device).
    """
    targets = _target_query(db, policy.id).all()

    if not targets:
        return []

    result_ids = set()

    for target in targets:
        kind = target.target_type
        ref = target.target_ref

        if kind == "all":
            rows = db.query(Device.id).all()
            result_ids.update(row_id for (row_id,) in rows)

        elif kind in ("department", "lab", "location"):
            column = {
                "department": Device.department,
                "lab": Device.lab,
                "location": Device.location,
            }[kind]
            rows = (
                db.query(Device.id)
                .filter(column == ref)
                .all()
            )
            result_ids.update(row_id for (row_id,) in rows)

        elif kind == "group":
            group = (
                db.query(DeviceGroup)
                .filter(DeviceGroup.name == ref)
                .first()
            )
            if group is None:
                continue
            rows = (
                db.query(Device.id)
                .join(
                    DeviceGroupMember,
                    DeviceGroupMember.device_id == Device.id,
                )
                .filter(DeviceGroupMember.group_id == group.id)
                .all()
            )
            result_ids.update(row_id for (row_id,) in rows)

        elif kind == "device":
            if ref.isdigit():
                result_ids.add(int(ref))
            else:
                match = (
                    db.query(Device)
                    .filter(Device.hostname == ref)
                    .first()
                )
                if match:
                    result_ids.add(match.id)

    if not result_ids:
        return []

    return (
        db.query(Device)
        .filter(Device.id.in_(result_ids))
        .all()
    )


def materialize_devices(db: Session, policy):
    """Recompute the resolved device set for a policy."""
    devices = resolve_policy_devices(db, policy)

    current_ids = set(devices)

    existing = (
        db.query(WebAccessPolicyDevice)
        .filter(WebAccessPolicyDevice.policy_id == policy.id)
        .all()
    )

    existing_map = {row.device_id: row for row in existing}

    for device in devices:
        row = existing_map.get(device.id)

        if row is None:
            row = WebAccessPolicyDevice(
                policy_id=policy.id,
                device_id=device.id,
                hostname=device.hostname,
                status="pending",
                applied_version=0,
            )
            db.add(row)
        else:
            row.hostname = device.hostname

        current_ids.discard(device.id)

    for device_id in current_ids:
        if device_id in existing_map:
            db.delete(existing_map[device_id])

    db.commit()

    return len(devices)


def bump_version(db: Session, policy):
    policy.version = (policy.version or 1) + 1
    policy.updated_at = _now()
    db.commit()
    return policy.version


def add_sync_log(
    db: Session,
    policy_id,
    device_id,
    hostname,
    action,
    detail="",
):
    log = WebAccessSyncLog(
        policy_id=policy_id,
        device_id=device_id,
        hostname=hostname or "",
        action=action,
        detail=detail or "",
    )
    db.add(log)
    db.commit()
    return log


def broadcast_web_access_update(policy_id):
    from .websocket_manager import manager

    try:
        manager.broadcast_from_thread(
            {
                "type": "web_access_update",
                "policy_id": policy_id,
            }
        )
    except Exception:
        pass


def _did(obj, name):
    """Read an attribute from either a dict or an ORM object."""
    if isinstance(obj, dict):
        return obj.get(name)

    return getattr(obj, name, None)


def serialize_domain_entry(entry):
    return {
        "id": entry.id,
        "policy_id": entry.policy_id,
        "domain": entry.domain,
        "include_subdomains": bool(entry.include_subdomains),
    }


def serialize_target(target):
    return {
        "id": target.id,
        "policy_id": target.policy_id,
        "target_type": target.target_type,
        "target_ref": target.target_ref,
    }


def policy_device_summary(db: Session, policy_id):
    rows = (
        db.query(WebAccessPolicyDevice)
        .filter(WebAccessPolicyDevice.policy_id == policy_id)
        .all()
    )

    counts = {
        "total": len(rows),
        "pending": 0,
        "synced": 0,
        "failed": 0,
        "not_applicable": 0,
    }

    for row in rows:
        status = row.status or "pending"

        if status in counts:
            counts[status] += 1

    return counts


def serialize_policy(db: Session, policy):
    entries = _domain_query(db, policy.id).all()
    targets = _target_query(db, policy.id).all()

    return {
        "id": policy.id,
        "name": policy.name,
        "description": policy.description,
        "action": policy.action,
        "enabled": bool(policy.enabled),
        "version": policy.version,
        "created_by": policy.created_by,
        "created_at": policy.created_at.isoformat()
        if policy.created_at
        else None,
        "updated_at": policy.updated_at.isoformat()
        if policy.updated_at
        else None,
        "domains": [serialize_domain_entry(e) for e in entries],
        "targets": [serialize_target(t) for t in targets],
        "device_summary": policy_device_summary(db, policy.id),
    }


def get_web_access_settings(db: Session):
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

    def _int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    return {
        "enabled": str(_get(ENABLED_KEY, "true")).lower()
        in ("1", "true", "yes", "on"),
        "poll_interval_seconds": _int(
            _get(POLL_INTERVAL_KEY, "15"), 15
        ),
    }


def agent_policy_payload(db: Session, device):
    """Return enabled policies that target the given device.

    Each payload carries the policy version plus the current domain
    rules so the agent can apply and report back a concrete revision.
    """
    device_ids = (_did(device, "id"),)

    policy_rows = (
        db.query(WebAccessPolicy)
        .filter(WebAccessPolicy.enabled.is_(True))
        .all()
    )

    policies = []

    for policy in policy_rows:
        devices = resolve_policy_devices(db, policy)

        if not any(d.id in device_ids for d in devices):
            continue

        entries = _domain_query(db, policy.id).all()

        if not entries:
            continue

        policies.append(
            {
                "id": policy.id,
                "name": policy.name,
                "action": policy.action,
                "version": policy.version,
                "domains": [
                    {
                        "domain": entry.domain,
                        "include_subdomains": bool(
                            entry.include_subdomains
                        ),
                    }
                    for entry in entries
                ],
            }
        )

    return policies


def record_agent_sync(
    db: Session,
    device,
    result,
):
    """Record the agent's apply result for its assigned policies."""
    device_id = _did(device, "id")
    hostname = _did(device, "hostname") or ""
    applied = result.get("applied") or []
    failed = result.get("failed") or []
    device_version = result.get("device_version", 0)

    summary = []

    for item in applied:
        policy_id = item.get("policy_id")
        version = item.get("version")

        row = (
            db.query(WebAccessPolicyDevice)
            .filter(
                WebAccessPolicyDevice.policy_id == policy_id,
                WebAccessPolicyDevice.device_id == device_id,
            )
            .first()
        )

        detail = item.get("detail", "Policy applied")

        if row is not None:
            row.status = "synced"
            row.applied_version = version or 0
            row.detail = detail
            row.applied_at = _now()
            row.last_synced_at = _now()
        elif policy_id is not None:
            db.add(
                WebAccessPolicyDevice(
                    policy_id=policy_id,
                    device_id=device_id,
                    hostname=hostname,
                    status="synced",
                    applied_version=version or 0,
                    detail=detail,
                    applied_at=_now(),
                    last_synced_at=_now(),
                )
            )

        add_sync_log(
            db,
            policy_id,
            device_id,
            hostname,
            "policy_synced",
            detail,
        )

        summary.append(
            {
                "policy_id": policy_id,
                "status": "synced",
                "version": version,
            }
        )

    for item in failed:
        policy_id = item.get("policy_id")

        row = (
            db.query(WebAccessPolicyDevice)
            .filter(
                WebAccessPolicyDevice.policy_id == policy_id,
                WebAccessPolicyDevice.device_id == device_id,
            )
            .first()
        )

        detail = item.get(
            "detail", "Policy could not be applied"
        )

        if row is not None:
            row.status = "failed"
            row.detail = detail
            row.last_synced_at = _now()

        add_sync_log(
            db,
            policy_id,
            device_id,
            hostname,
            "sync_failed",
            detail,
        )

        summary.append(
            {
                "policy_id": policy_id,
                "status": "failed",
                "version": item.get("version"),
            }
        )

    return summary
