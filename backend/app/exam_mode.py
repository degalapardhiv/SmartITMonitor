from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from .auth_dependency import get_current_user
from .database import SessionLocal
from .role_dependency import require_admin

router = APIRouter(
    prefix="/exam-mode",
    tags=["Exam Mode"],
)


class ExamModeUpdate(BaseModel):
    enabled: bool
    usb_policy: str = "approval_required"


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def user_name(current_user):
    if isinstance(current_user, dict):
        return (
            current_user.get("username")
            or current_user.get("sub")
            or "admin"
        )

    return getattr(
        current_user,
        "username",
        "admin",
    )


@router.get("")
def get_exam_mode(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    result = db.execute(
        text("""
            SELECT
                enabled,
                usb_policy,
                updated_at
            FROM exam_mode_settings
            WHERE id = 1
        """)
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Exam Mode configuration is missing",
        )

    return dict(result)


@router.put("")
def update_exam_mode(
    settings: ExamModeUpdate,
    current_user=Depends(require_admin),
    db=Depends(get_db),
):
    if settings.usb_policy not in {
        "approval_required",
        "allow",
        "block",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "usb_policy must be "
                "approval_required, allow, or block"
            ),
        )

    result = db.execute(
        text("""
            UPDATE exam_mode_settings
            SET
                enabled = :enabled,
                usb_policy = :usb_policy,
                updated_at = NOW()
            WHERE id = 1
            RETURNING
                enabled,
                usb_policy,
                updated_at
        """),
        {
            "enabled": settings.enabled,
            "usb_policy": settings.usb_policy,
        },
    ).mappings().first()

    db.commit()

    return dict(result)
