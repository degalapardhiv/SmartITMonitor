import hmac

from fastapi import Depends, Header, HTTPException
from sqlalchemy import text

from .database import SessionLocal


AGENT_TOKEN_MAX_LENGTH = 256


def _secure_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(
        a.encode("utf-8"),
        b.encode("utf-8"),
    )


def get_agent_device(
    x_agent_token: str | None = Header(default=None),
):
    if not x_agent_token:
        raise HTTPException(
            status_code=401,
            detail="Agent authentication required",
        )

    if len(x_agent_token) > AGENT_TOKEN_MAX_LENGTH:
        raise HTTPException(
            status_code=401,
            detail="Invalid agent token",
        )

    db = SessionLocal()

    try:
        devices = db.execute(
            text("""
                SELECT id, hostname, agent_token
                FROM devices
                WHERE agent_token IS NOT NULL
            """),
        ).mappings().all()

        match = next(
            (
                device
                for device in devices
                if device["agent_token"]
                and _secure_equal(device["agent_token"], x_agent_token)
            ),
            None,
        )

        if not match:
            raise HTTPException(
                status_code=401,
                detail="Invalid agent token",
            )

        return {
            "id": match["id"],
            "hostname": match["hostname"],
        }

    finally:
        db.close()
