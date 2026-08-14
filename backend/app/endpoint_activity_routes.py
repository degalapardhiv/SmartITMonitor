from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .agent_auth import get_agent_device
from .database import SessionLocal
from .role_dependency import require_admin
from .services.endpoint_activity_service import (
    export_csv,
    get_activity_audit,
    get_activity_settings,
    ingest_endpoint_events,
    list_devices,
    list_event_types,
    list_events,
    record_activity_audit,
    save_activity_settings,
)

router = APIRouter(prefix="/endpoint-activity", tags=["Endpoint Activity"])


class ActivityBatch(BaseModel):
    events: list[dict]


class ActivitySettingsUpdate(BaseModel):
    url_auditing: bool | None = None
    retention_days: int | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_datetime(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime: {value}",
        )


def _actor_name(user):
    return user.get("username") or user.get("sub") or "admin"


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@router.post("")
def submit_activity(
    payload: ActivityBatch,
    agent_device=Depends(get_agent_device),
    db=Depends(get_db),
):
    """Agent endpoint: submit endpoint activity events."""

    try:
        stored = ingest_endpoint_events(
            db,
            agent_device,
            payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"stored": stored}


@router.get("/agent/config")
def agent_config(
    agent_device=Depends(get_agent_device),
    db=Depends(get_db),
):
    """Agent endpoint: current activity configuration."""

    settings = get_activity_settings(db)

    from .settings_center_service import get_activity_upload_interval

    return {
        "url_auditing": settings["url_auditing"],
        "retention_days": settings["retention_days"],
        "interval_seconds": get_activity_upload_interval(),
    }


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.get("")
def get_events(
    device_id: int | None = None,
    event_type: str | None = None,
    search: str | None = None,
    from_: str | None = None,
    to: str | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    if sort not in {"newest", "oldest"}:
        raise HTTPException(
            status_code=400,
            detail="sort must be 'newest' or 'oldest'",
        )

    filters = {
        "device_id": device_id,
        "event_type": event_type,
        "search": search,
        "from": _parse_datetime(from_),
        "to": _parse_datetime(to),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }

    items, total = list_events(db, filters)

    return {"items": items, "total": total}


@router.get("/devices")
def get_devices(
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    return {"devices": list_devices(db)}


@router.get("/types")
def get_types(
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    return {"types": list_event_types(db)}


@router.get("/export")
def export_events(
    device_id: int | None = None,
    event_type: str | None = None,
    search: str | None = None,
    from_: str | None = None,
    to: str | None = None,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    filters = {
        "device_id": device_id,
        "event_type": event_type,
        "search": search,
        "from": _parse_datetime(from_),
        "to": _parse_datetime(to),
    }

    content = export_csv(db, filters)
    filename = f"endpoint-activity-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/settings")
def get_settings(
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    """Settings + audit trail. Views are recorded in the audit trail."""

    username = _actor_name(current_user)

    record_activity_audit(
        db,
        username,
        "SETTINGS_VIEWED",
        "Endpoint activity settings viewed",
    )

    return {
        "settings": get_activity_settings(db),
        "audit": get_activity_audit(db),
    }


@router.get("/audit")
def get_audit(
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    return {"audit": get_activity_audit(db)}


@router.put("/settings")
def update_settings(
    update: ActivitySettingsUpdate,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    if update.url_auditing is None and update.retention_days is None:
        raise HTTPException(
            status_code=400,
            detail="Nothing to update",
        )

    before = get_activity_settings(db)

    new = save_activity_settings(
        db,
        url_auditing=update.url_auditing,
        retention_days=update.retention_days,
    )

    username = _actor_name(current_user)

    changes = []

    if before["url_auditing"] != new["url_auditing"]:
        changes.append(
            f"url_auditing {before['url_auditing']}->{new['url_auditing']}"
        )

    if before["retention_days"] != new["retention_days"]:
        changes.append(
            f"retention_days {before['retention_days']}->{new['retention_days']}"
        )

    record_activity_audit(
        db,
        username,
        "SETTINGS_UPDATED",
        "; ".join(changes),
    )

    return {
        "settings": new,
        "audit": get_activity_audit(db),
    }
