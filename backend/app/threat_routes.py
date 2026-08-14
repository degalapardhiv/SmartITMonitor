from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .agent_auth import get_agent_device
from .database import SessionLocal
from .role_dependency import require_admin
from .threat_service import (
    ADMIN_ACTIONS,
    CATEGORY_DISPLAY,
    VALID_SEVERITIES,
    VALID_STATUSES,
    apply_admin_action,
    get_threat,
    get_threat_settings,
    ingest_threat,
    list_threats,
    threat_analytics,
)

router = APIRouter(prefix="/threats", tags=["Threat Protection"])


class ThreatReport(BaseModel):
    file_name: str = ""
    file_path: str = ""
    file_type: str = ""
    file_hash: str = ""
    detection_name: str = ""
    category: str = "suspicious_file"
    severity: str = ""
    detection_source: str = ""
    action: str = ""
    username: str = ""
    source: str = ""
    usb_request_id: int | None = None
    quarantine_path: str = ""
    quarantine_method: str = ""
    detected_at: str = ""
    notes: str = ""


class ThreatAction(BaseModel):
    action: str
    note: str = ""


class FileActionRequest(BaseModel):
    device_id: int
    file_path: str
    action: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _actor_name(user):
    return user.get("username") or user.get("sub") or "admin"


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@router.post("/agent/report")
def report_threat(
    payload: ThreatReport,
    agent_device=Depends(get_agent_device),
    db=Depends(get_db),
):
    """Agent endpoint: report a detected / safe file for policy decision."""

    category = (payload.category or "").lower()

    if category not in CATEGORY_DISPLAY:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown category '{category}'. "
                f"Valid: {', '.join(sorted(CATEGORY_DISPLAY))}"
            ),
        )

    if payload.severity and payload.severity.upper() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown severity '{payload.severity}'. "
                f"Valid: {', '.join(sorted(VALID_SEVERITIES))}"
            ),
        )

    settings = get_threat_settings(db)

    if not settings["enabled"]:
        return {
            "status": "disabled",
            "threat": None,
            "message": "Threat protection is disabled",
        }

    try:
        threat = ingest_threat(
            db,
            agent_device,
            payload.model_dump(exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "recorded", "threat": threat}


@router.get("/agent/config")
def agent_config(
    agent_device=Depends(get_agent_device),
    db=Depends(get_db),
):
    """Agent endpoint: current threat policy the agent should enforce."""

    return get_threat_settings(db)


@router.post("/agent/action")
def agent_file_action(
    payload: FileActionRequest,
    agent_device=Depends(get_agent_device),
    db=Depends(get_db),
):
    """Agent endpoint: reseolve/restore an already-quarantined file.

    The payload identifies the file that the administrator has approved;
    the status update is applied via the admin review endpoint instead.
    """

    raise HTTPException(
        status_code=400,
        detail=(
            "File actions are applied by administrators through the "
            "threat review API."
        ),
    )


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_threat_events(
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    device_id: int | None = None,
    search: str | None = None,
    active_only: bool = False,
    critical_only: bool = False,
    action_required: bool = False,
    include_allowed: bool = False,
    sort: str = "newest",
    limit: int = 100,
    offset: int = 0,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    if status and status.upper() not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown status '{status}'. Valid: {', '.join(sorted(VALID_STATUSES))}",
        )

    if severity and severity.upper() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown severity '{severity}'.",
        )

    if category and category.lower() not in CATEGORY_DISPLAY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown category '{category}'.",
        )

    # Safe-file noise is hidden by default on this listing endpoint.
    active_only = active_only or not include_allowed

    filters = {
        "status": status.upper() if status else None,
        "severity": severity.upper() if severity else None,
        "category": category.lower() if category else None,
        "device_id": device_id,
        "search": search,
        "active_only": active_only,
        "critical_only": critical_only,
        "action_required": action_required,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }

    items, total = list_threats(db, filters)

    return {"items": items, "total": total}


@router.get("/analytics")
def analytics(
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    return threat_analytics(db)


@router.get("/export")
def export_threats_csv(
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    device_id: int | None = None,
    search: str | None = None,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    filters = {
        "status": status.upper() if status else None,
        "severity": severity.upper() if severity else None,
        "category": category.lower() if category else None,
        "device_id": device_id,
        "search": search,
        "active_only": False,
    }

    items, _total = list_threats(db, filters)

    headers = [
        "id",
        "hostname",
        "device_id",
        "file_name",
        "file_path",
        "file_hash",
        "category",
        "severity",
        "detection_source",
        "action",
        "status",
        "username",
        "source",
        "quarantine_path",
        "detected_at",
        "reviewed_by",
    ]

    rows = [
        "\ufeff" + ",".join(headers),
    ]

    for item in items:
        rows.append(
            ",".join(
                _csv_cell(item.get(header, ""))
                for header in headers
            )
        )

    content = "\r\n".join(rows)
    filename = f"threats-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


def _csv_cell(value):
    value = str(value or "")
    if any(ch in value for ch in (",", '"', "\n", "\r")):
        return '"' + value.replace('"', '""') + '"'
    return value


@router.get("/{threat_id}")
def get_threat_detail(
    threat_id: int,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    threat = get_threat(db, threat_id)

    if threat is None:
        raise HTTPException(status_code=404, detail="Threat not found")

    return threat


@router.post("/{threat_id}/action")
def review_threat(
    threat_id: int,
    payload: ThreatAction,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    if payload.action not in ADMIN_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{payload.action}'. Valid: {', '.join(sorted(ADMIN_ACTIONS))}",
        )

    username = _actor_name(current_user)

    try:
        return apply_admin_action(
            db,
            threat_id,
            payload.action,
            username,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))