from fastapi import Depends, Header, HTTPException
from sqlalchemy import text

from .database import SessionLocal


def get_agent_device(
    x_agent_token: str | None = Header(default=None),
):
    if not x_agent_token:
        raise HTTPException(
            status_code=401,
            detail="Agent authentication required",
        )

    db = SessionLocal()

    try:
        device = db.execute(
            text("""
                SELECT id, hostname
                FROM devices
                WHERE agent_token = :token
            """),
            {"token": x_agent_token},
        ).mappings().first()

        if not device:
            raise HTTPException(
                status_code=401,
                detail="Invalid agent token",
            )

        return dict(device)

    finally:
        db.close()
