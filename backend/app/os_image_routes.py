from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth_dependency import get_current_user
from .database import SessionLocal
from .os_image_model import OSImage
from .role_dependency import require_admin


router = APIRouter(
    prefix="/os-images",
    tags=["OS Images"],
)


class OSImagePayload(BaseModel):
    name: str
    version: str = ""
    edition: str = ""
    architecture: str = "x86_64"
    checksum: str = ""
    checksum_type: str = "sha256"
    kernel_path: str = ""
    initrd_path: str = ""
    kickstart_url: str = ""
    approved: bool = False


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def image_to_dict(image):
    return {
        "id": image.id,
        "name": image.name,
        "version": image.version,
        "edition": image.edition,
        "architecture": image.architecture,
        "checksum": image.checksum,
        "checksum_type": image.checksum_type,
        "kernel_path": image.kernel_path,
        "initrd_path": image.initrd_path,
        "kickstart_url": image.kickstart_url,
        "approved": image.approved,
        "created_by": image.created_by,
        "created_at": (
            image.created_at.isoformat()
            if image.created_at
            else None
        ),
    }


def _apply_payload(image, payload):
    image.name = (payload.name or "").strip()
    image.version = (payload.version or "").strip()
    image.edition = (payload.edition or "").strip()
    image.architecture = (payload.architecture or "x86_64").strip()
    image.checksum = (payload.checksum or "").strip()
    image.checksum_type = (payload.checksum_type or "sha256").strip()
    image.kernel_path = (payload.kernel_path or "").strip()
    image.initrd_path = (payload.initrd_path or "").strip()
    image.kickstart_url = (payload.kickstart_url or "").strip()
    image.approved = bool(payload.approved)

    return image


@router.get("")
def list_images(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    images = (
        db.query(OSImage)
        .order_by(OSImage.name.asc(), OSImage.version.asc())
        .all()
    )

    return [image_to_dict(image) for image in images]


@router.post("")
def create_image(
    payload: OSImagePayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = (payload.name or "").strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="OS image name is required",
        )

    duplicate = (
        db.query(OSImage)
        .filter(
            OSImage.name == name,
            OSImage.version == (payload.version or "").strip(),
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="An OS image with this name and version already exists",
        )

    image = OSImage(created_by=current_user["username"])

    _apply_payload(image, payload)

    db.add(image)
    db.commit()
    db.refresh(image)

    return image_to_dict(image)


@router.put("/{image_id}")
def update_image(
    image_id: int,
    payload: OSImagePayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    image = (
        db.query(OSImage)
        .filter(OSImage.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=404,
            detail="OS image not found",
        )

    name = (payload.name or "").strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="OS image name is required",
        )

    duplicate = (
        db.query(OSImage)
        .filter(
            OSImage.name == name,
            OSImage.version == (payload.version or "").strip(),
            OSImage.id != image_id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="An OS image with this name and version already exists",
        )

    _apply_payload(image, payload)

    db.commit()
    db.refresh(image)

    return image_to_dict(image)


@router.delete("/{image_id}")
def delete_image(
    image_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    image = (
        db.query(OSImage)
        .filter(OSImage.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=404,
            detail="OS image not found",
        )

    db.delete(image)
    db.commit()

    return {"status": "deleted", "id": image_id}


@router.post("/{image_id}/verify-checksum")
def verify_checksum_now(
    image_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    image = (
        db.query(OSImage)
        .filter(OSImage.id == image_id)
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=404,
            detail="OS image not found",
        )

    from .services.provisioning_service import (
        ProvisioningError,
        verify_image_checksum,
    )

    try:
        verified = verify_image_checksum(image)

        return {
            "id": image.id,
            "name": image.name,
            "verified": verified,
            "checksum": image.checksum,
        }

    except ProvisioningError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )