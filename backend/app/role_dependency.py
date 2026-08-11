from fastapi import Depends, HTTPException

from .auth_dependency import get_current_user


def require_admin(
    current_user = Depends(get_current_user),
):

    if current_user.get("role", "").lower() != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return current_user
