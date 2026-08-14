from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .agent_auth import get_agent_device
from .database import SessionLocal
from .role_dependency import require_admin
from .web_access_model import (
    WebAccessDomainEntry,
    WebAccessPolicy,
    WebAccessPolicyDevice,
    WebAccessSyncLog,
    WebAccessTarget,
)
from .web_access_service import (
    VALID_ACTIONS,
    VALID_TARGET_TYPES,
    add_sync_log,
    agent_policy_payload,
    broadcast_web_access_update,
    bump_version,
    materialize_devices,
    normalize_domain,
    record_agent_sync,
    resolve_policy_devices,
    serialize_policy,
)


router = APIRouter(
    prefix="/web-access",
    tags=["Web Access Control"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _actor_name(user):
    return user.get("username") or user.get("name") or ""


def _policy_or_404(db, policy_id):
    policy = (
        db.query(WebAccessPolicy)
        .filter(WebAccessPolicy.id == policy_id)
        .first()
    )

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Policy not found",
        )

    return policy


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class DomainCreate(BaseModel):
    domains: list[str] = Field(default_factory=list)
    include_subdomains: bool = False


class TargetCreate(BaseModel):
    target_type: str
    target_ref: str = ""


class PolicyCreate(BaseModel):
    name: str
    description: str = ""
    action: str = "blocklist"
    enabled: bool = True
    domains: list[str] = Field(default_factory=list)
    include_subdomains: bool = False
    targets: list[dict] = Field(default_factory=list)


class PolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    action: str | None = None
    enabled: bool | None = None


class AgentSyncResult(BaseModel):
    device_version: int = 0
    applied: list[dict] = Field(default_factory=list)
    failed: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Admin: policies
# ---------------------------------------------------------------------------


@router.get("/policies")
def list_policies(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policies = (
        db.query(WebAccessPolicy)
        .order_by(WebAccessPolicy.name.asc())
        .all()
    )

    return {
        "policies": [serialize_policy(db, policy) for policy in policies]
    }


@router.post("/policies")
def create_policy(
    payload: PolicyCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    action = payload.action.strip().lower()

    if action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"action must be one of {sorted(VALID_ACTIONS)}",
        )

    name = payload.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Policy name is required",
        )

    exists = (
        db.query(WebAccessPolicy)
        .filter(WebAccessPolicy.name == name)
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="A policy with this name already exists",
        )

    normalized_domains, seen_domains = [], set()

    for domain in payload.domains:
        normalized = _validate_domain(domain)

        if normalized in seen_domains:
            raise HTTPException(
                status_code=400,
                detail=f"Domain already in policy: {normalized}",
            )

        seen_domains.add(normalized)
        normalized_domains.append(normalized)

    seen_targets = set()

    for target in payload.targets:
        kind = (target.get("target_type") or "").strip().lower()
        ref = (target.get("target_ref") or "").strip()

        _validate_target(db, kind, ref)

        key = (kind, ref)

        if key in seen_targets:
            raise HTTPException(
                status_code=400,
                detail="This target is already assigned to the policy",
            )

        seen_targets.add(key)

    policy = WebAccessPolicy(
        name=name,
        description=payload.description,
        action=action,
        enabled=bool(payload.enabled),
        version=1,
        created_by=_actor_name(current_user),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    for domain in payload.domains:
        _add_domain(db, policy, domain, payload.include_subdomains)

    for target in payload.targets:
        _add_target(db, policy, target)

    materialize_devices(db, policy)

    add_sync_log(
        db,
        policy.id,
        None,
        "",
        "policy_created",
        f"Created by {_actor_name(current_user) or 'admin'}",
    )

    broadcast_web_access_update(policy.id)

    return serialize_policy(db, policy)


@router.get("/policies/{policy_id}")
def get_policy(
    policy_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    return serialize_policy(db, policy)


@router.put("/policies/{policy_id}")
def update_policy(
    policy_id: int,
    payload: PolicyUpdate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    changed = False

    if payload.name is not None:
        name = payload.name.strip()

        if not name:
            raise HTTPException(
                status_code=400,
                detail="Policy name is required",
            )

        conflict = (
            db.query(WebAccessPolicy)
            .filter(
                WebAccessPolicy.name == name,
                WebAccessPolicy.id != policy.id,
            )
            .first()
        )

        if conflict:
            raise HTTPException(
                status_code=400,
                detail="A policy with this name already exists",
            )

        if name != policy.name:
            policy.name = name
            changed = True

    if payload.description is not None:
        policy.description = payload.description
        changed = True

    if payload.action is not None:
        action = payload.action.strip().lower()

        if action not in VALID_ACTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"action must be one of {sorted(VALID_ACTIONS)}",
            )

        if action != policy.action:
            policy.action = action
            changed = True

    if payload.enabled is not None:
        if bool(payload.enabled) != bool(policy.enabled):
            policy.enabled = bool(payload.enabled)
            changed = True

    if changed:
        bump_version(db, policy)

        add_sync_log(
            db,
            policy.id,
            None,
            "",
            "policy_updated",
            f"Updated by {_actor_name(current_user) or 'admin'}",
        )

    db.commit()
    db.refresh(policy)

    broadcast_web_access_update(policy.id)

    return serialize_policy(db, policy)


@router.delete("/policies/{policy_id}")
def delete_policy(
    policy_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    db.query(WebAccessSyncLog).filter(
        WebAccessSyncLog.policy_id == policy_id
    ).delete()

    db.delete(policy)
    db.commit()

    return {"ok": True, "deleted": policy_id}


# ---------------------------------------------------------------------------
# Admin: domain entries
# ---------------------------------------------------------------------------


def _validate_domain(domain):
    normalized, error = normalize_domain(domain)

    if error:
        raise HTTPException(
            status_code=400,
            detail=error,
        )

    return normalized


def _add_domain(db, policy, domain, include_subdomains):
    normalized = _validate_domain(domain)

    exists = (
        db.query(WebAccessDomainEntry)
        .filter(
            WebAccessDomainEntry.policy_id == policy.id,
            WebAccessDomainEntry.domain == normalized,
        )
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail=f"Domain already in policy: {normalized}",
        )

    entry = WebAccessDomainEntry(
        policy_id=policy.id,
        domain=normalized,
        include_subdomains=bool(include_subdomains),
    )
    db.add(entry)
    db.commit()

    return entry


@router.post("/policies/{policy_id}/domains")
def add_domains(
    policy_id: int,
    payload: DomainCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    added = []

    for domain in payload.domains:
        try:
            entry = _add_domain(
                db, policy, domain, payload.include_subdomains
            )
        except HTTPException as exc:
            continue

        added.append(entry)

    if not added:
        raise HTTPException(
            status_code=400,
            detail="No new domains were added",
        )

    bump_version(db, policy)

    add_sync_log(
        db,
        policy.id,
        None,
        "",
        "domain_added",
        f"Added {len(added)} domain(s)",
    )

    broadcast_web_access_update(policy.id)

    return {
        "added": [
            {
                "id": entry.id,
                "domain": entry.domain,
                "include_subdomains": bool(entry.include_subdomains),
            }
            for entry in added
        ]
    }


@router.delete("/policies/{policy_id}/domains/{entry_id}")
def delete_domain(
    policy_id: int,
    entry_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    entry = (
        db.query(WebAccessDomainEntry)
        .filter(
            WebAccessDomainEntry.id == entry_id,
            WebAccessDomainEntry.policy_id == policy.id,
        )
        .first()
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Domain entry not found",
        )

    domain = entry.domain
    db.delete(entry)
    db.commit()

    bump_version(db, policy)

    add_sync_log(
        db,
        policy.id,
        None,
        "",
        "domain_removed",
        f"Removed domain {domain}",
    )

    broadcast_web_access_update(policy.id)

    return {"ok": True, "removed": domain}


# ---------------------------------------------------------------------------
# Admin: targets
# ---------------------------------------------------------------------------


def _validate_target(db, kind, ref):
    kind = (kind or "").strip().lower()
    ref = (ref or "").strip()

    if kind not in VALID_TARGET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"target_type must be one of {sorted(VALID_TARGET_TYPES)}",
        )

    if kind != "all" and not ref:
        raise HTTPException(
            status_code=400,
            detail="target_ref is required for this target type",
        )

    if kind == "group":
        from .software_deployment_model import DeviceGroup

        group = (
            db.query(DeviceGroup)
            .filter(DeviceGroup.name == ref)
            .first()
        )
        if group is None:
            raise HTTPException(
                status_code=400,
                detail=f"No device group named {ref!r}",
            )

    if kind == "device":
        from .models import Device

        match = None

        if ref.isdigit():
            match = (
                db.query(Device)
                .filter(Device.id == int(ref))
                .first()
            )
        else:
            match = (
                db.query(Device)
                .filter(Device.hostname == ref)
                .first()
            )

        if match is None:
            raise HTTPException(
                status_code=400,
                detail=f"No device matching {ref!r}",
            )


def _add_target(db, policy, target_data):
    kind = (target_data.get("target_type") or "").strip().lower()
    ref = (target_data.get("target_ref") or "").strip()

    _validate_target(db, kind, ref)

    exists = (
        db.query(WebAccessTarget)
        .filter(
            WebAccessTarget.policy_id == policy.id,
            WebAccessTarget.target_type == kind,
            WebAccessTarget.target_ref == ref,
        )
        .first()
    )

    if exists:
        raise HTTPException(
            status_code=400,
            detail="This target is already assigned to the policy",
        )

    target = WebAccessTarget(
        policy_id=policy.id,
        target_type=kind,
        target_ref=ref,
    )
    db.add(target)
    db.commit()

    return target


@router.post("/policies/{policy_id}/targets")
def add_target(
    policy_id: int,
    payload: TargetCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    target = _add_target(
        db,
        policy,
        {
            "target_type": payload.target_type,
            "target_ref": payload.target_ref,
        },
    )

    materialize_devices(db, policy)

    bump_version(db, policy)

    add_sync_log(
        db,
        policy.id,
        None,
        "",
        "target_added",
        f"Added target {target.target_type}:{target.target_ref}",
    )

    broadcast_web_access_update(policy.id)

    return {
        "id": target.id,
        "target_type": target.target_type,
        "target_ref": target.target_ref,
    }


@router.delete("/policies/{policy_id}/targets/{target_id}")
def delete_target(
    policy_id: int,
    target_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    target = (
        db.query(WebAccessTarget)
        .filter(
            WebAccessTarget.id == target_id,
            WebAccessTarget.policy_id == policy.id,
        )
        .first()
    )

    if target is None:
        raise HTTPException(
            status_code=404,
            detail="Target not found",
        )

    removed = f"{target.target_type}:{target.target_ref}"

    db.delete(target)
    db.commit()

    materialize_devices(db, policy)

    bump_version(db, policy)

    add_sync_log(
        db,
        policy.id,
        None,
        "",
        "target_removed",
        f"Removed target {removed}",
    )

    broadcast_web_access_update(policy.id)

    return {"ok": True, "removed": removed}


# ---------------------------------------------------------------------------
# Admin: device assignments & history
# ---------------------------------------------------------------------------


@router.get("/policies/{policy_id}/devices")
def list_policy_devices(
    policy_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    policy = _policy_or_404(db, policy_id)

    rows = (
        db.query(WebAccessPolicyDevice)
        .filter(WebAccessPolicyDevice.policy_id == policy.id)
        .order_by(WebAccessPolicyDevice.hostname.asc())
        .all()
    )

    return {
        "devices": [
            {
                "id": row.id,
                "device_id": row.device_id,
                "hostname": row.hostname,
                "status": row.status,
                "applied_version": row.applied_version,
                "detail": row.detail,
                "applied_at": row.applied_at.isoformat()
                if row.applied_at
                else None,
                "last_synced_at": row.last_synced_at.isoformat()
                if row.last_synced_at
                else None,
            }
            for row in rows
        ]
    }


@router.get("/sync-logs")
def list_sync_logs(
    policy_id: int | None = None,
    limit: int = 100,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(WebAccessSyncLog)

    if policy_id is not None:
        query = query.filter(WebAccessSyncLog.policy_id == policy_id)

    limit = max(1, min(limit, 500))

    rows = (
        query.order_by(WebAccessSyncLog.id.desc())
        .limit(limit)
        .all()
    )

    return {
        "logs": [
            {
                "id": log.id,
                "policy_id": log.policy_id,
                "device_id": log.device_id,
                "hostname": log.hostname,
                "action": log.action,
                "detail": log.detail,
                "created_at": log.created_at.isoformat()
                if log.created_at
                else None,
            }
            for log in rows
        ]
    }


@router.get("/stats")
def web_access_stats(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    from .web_access_service import policy_device_summary

    policies = db.query(WebAccessPolicy).all()

    total_policies = len(policies)
    enabled = sum(1 for p in policies if p.enabled)

    totals = {
        "total": 0,
        "pending": 0,
        "synced": 0,
        "failed": 0,
        "not_applicable": 0,
    }

    for policy in policies:
        summary = policy_device_summary(db, policy.id)
        for key in totals:
            totals[key] += summary[key]

    return {
        "total_policies": total_policies,
        "enabled_policies": enabled,
        "disabled_policies": total_policies - enabled,
        "devices": totals,
    }


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@router.get("/agent/policy")
def agent_policy(
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    from .web_access_service import get_web_access_settings

    settings = get_web_access_settings(db)

    if not settings["enabled"]:
        return {"enabled": False, "policies": []}

    policies = agent_policy_payload(db, agent_device)

    return {
        "enabled": True,
        "poll_interval_seconds": settings["poll_interval_seconds"],
        "policies": policies,
    }


@router.post("/agent/sync-result")
def agent_sync_result(
    payload: AgentSyncResult,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    summary = record_agent_sync(db, agent_device, payload.dict())

    return {
        "ok": True,
        "recorded": len(summary),
        "summary": summary,
    }
