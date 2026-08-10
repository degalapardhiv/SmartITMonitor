from threading import Lock

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .auth_dependency import get_current_user

router = APIRouter(prefix="/exam-mode", tags=["Exam Mode"])

_lock = Lock()

_state = {
    "enabled": False,
    "usb_policy": "approval_required",
}


class ExamModeUpdate(BaseModel):
    enabled: bool
    usb_policy: str = "approval_required"


@router.get("")
def get_exam_mode(
    current_user=Depends(get_current_user),
):
    with _lock:
        return dict(_state)


@router.put("")
def update_exam_mode(
    settings: ExamModeUpdate,
    current_user=Depends(get_current_user),
):
    if settings.usb_policy not in {
        "approval_required",
        "allow",
        "block",
    }:
        return {
            "error": "Invalid USB policy"
        }

    with _lock:
        _state["enabled"] = settings.enabled
        _state["usb_policy"] = settings.usb_policy
        return dict(_state)
