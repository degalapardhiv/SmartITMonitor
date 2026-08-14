from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import SessionLocal
from .role_dependency import require_admin
from .settings_audit_model import SettingsAudit
from .settings_center_service import (
    SECTIONS,
    _log_audit,
    apply_section,
    get_section_snapshot,
)
from .websocket_manager import manager


router = APIRouter(
    prefix="/settings-center",
    tags=["Settings Center"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _actor(current_user, request):
    if isinstance(current_user, dict):
        username = current_user.get("username") or "admin"
        role = current_user.get("role") or "admin"
    else:
        username = getattr(current_user, "username", "admin")
        role = getattr(current_user, "role", "admin")

    client = request.client

    return {
        "username": username,
        "role": role,
        "ip": client.host if client else "",
    }


@router.get("")
def get_settings_center(
    request: Request,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    sections = []

    for section, meta in SECTIONS.items():
        values = get_section_snapshot(db, section)

        sections.append(
            {
                "key": section,
                "label": meta["label"],
                "description": meta["description"],
                "values": values,
                "keys": [
                    {
                        "key": spec["key"],
                        "label": spec["label"],
                        "type": spec["type"],
                        "default": spec.get("default", ""),
                        "help": spec.get("help", ""),
                        "choices": spec.get("choices", []),
                        "item_label": spec.get("item_label", ""),
                        "optional": bool(spec.get("optional")),
                        "secret": spec["type"] == "secret",
                        "is_set": bool(
                            values.get(spec["key"])
                            and (
                                spec["type"] != "secret"
                                or values[spec["key"]] == "********"
                            )
                        ),
                    }
                    for spec in meta["keys"]
                ],
            }
        )

    return {"sections": sections}


class SectionUpdate(BaseModel):
    values: dict


@router.put("/{section}")
def update_section(
    section: str,
    payload: SectionUpdate,
    request: Request,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if section not in SECTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown settings section: {section}",
        )

    actor = _actor(current_user, request)

    try:
        result = apply_section(
            db,
            section,
            payload.values,
            actor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    try:
        manager.broadcast_from_thread(
            {
                "type": "settings_updated",
                "section": section,
            }
        )
    except Exception:
        pass

    return result


class TestPayload(BaseModel):
    channel: str


@router.post("/test")
def test_channel(
    payload: TestPayload,
    request: Request,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    actor = _actor(current_user, request)

    if payload.channel == "telegram":
        from .services.telegram_service import send_telegram

        from .settings_center_service import get_telegram_config

        config = get_telegram_config()

        if not config["bot_token"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Telegram bot token is not configured. "
                    "Set a bot token in Settings Center first."
                ),
            )

        if not config["chat_id"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Telegram chat id is not configured. "
                    "Set a chat id in Settings Center first."
                ),
            )

        _log_audit(
            db,
            actor["username"],
            actor["role"],
            "TEST",
            "telegram",
            "send_test_message",
            None,
            None,
            actor["ip"],
        )

        ok = send_telegram(
            "Smart IT Monitor Telegram Test Alert",
        )

        if not ok:
            raise HTTPException(
                status_code=502,
                detail="Telegram test message could not be sent.",
            )

        return {"status": "telegram test sent"}

    if payload.channel == "email":
        from .email_settings_model import EmailSetting
        from .services.email_service import email_enabled, send_email

        if not email_enabled():
            raise HTTPException(
                status_code=400,
                detail="Email notifications are disabled.",
            )

        config = db.query(EmailSetting).first()

        if not config:
            raise HTTPException(
                status_code=400,
                detail="SMTP configuration is missing.",
            )

        _log_audit(
            db,
            actor["username"],
            actor["role"],
            "TEST",
            "email",
            "send_test_message",
            None,
            None,
            actor["ip"],
        )

        sent = send_email(
            "Smart IT Monitor Test",
            "Email test notification",
        )

        if not sent:
            raise HTTPException(
                status_code=502,
                detail="Email sending failed. Check SMTP configuration.",
            )

        return {"status": "email test sent"}

    raise HTTPException(
        status_code=400,
        detail=f"Unknown channel: {payload.channel}",
    )


@router.get("/audit")
def get_audit_log(
    limit: int = 100,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SettingsAudit)
        .order_by(SettingsAudit.id.desc())
        .limit(min(limit, 500))
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "username": row.username,
                "role": row.role,
                "action": row.action,
                "section": row.section,
                "key": row.key,
                "old_value": row.old_value,
                "new_value": row.new_value,
                "ip": row.ip,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }
