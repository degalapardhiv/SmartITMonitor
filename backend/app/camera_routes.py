from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .camera_model import Camera
from .database import SessionLocal
from .auth_dependency import get_current_user
from .role_dependency import require_admin


router = APIRouter(
    prefix="/cameras",
    tags=["Cameras"]
)


class CameraCreate(BaseModel):
    name: str
    ip: str
    stream_url: str = ""
    location: str = ""


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def camera_to_dict(camera):
    return {
        "id": camera.id,
        "name": camera.name,
        "ip": camera.ip,
        "stream_url": camera.stream_url,
        "location": camera.location,
        "status": camera.status,
        "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
        "created_at": camera.created_at.isoformat() if camera.created_at else None,
    }


@router.get("")
def list_cameras(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):

    cameras = (
        db.query(Camera)
        .order_by(Camera.name.asc())
        .all()
    )

    return [camera_to_dict(camera) for camera in cameras]


@router.post("")
def create_camera(
    payload: CameraCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):

    name = payload.name.strip()
    ip = payload.ip.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Camera name is required")

    if not ip:
        raise HTTPException(status_code=400, detail="Camera IP is required")

    duplicate = (
        db.query(Camera)
        .filter(Camera.name == name)
        .first()
    )

    if duplicate:
        raise HTTPException(status_code=409, detail="A camera with this name already exists")

    camera = Camera(
        name=name,
        ip=ip,
        stream_url=payload.stream_url.strip(),
        location=payload.location.strip(),
        status="unknown",
    )

    db.add(camera)
    db.commit()
    db.refresh(camera)

    return camera_to_dict(camera)


@router.put("/{camera_id}")
def update_camera(
    camera_id: int,
    payload: CameraCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):

    camera = (
        db.query(Camera)
        .filter(Camera.id == camera_id)
        .first()
    )

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    name = payload.name.strip()
    ip = payload.ip.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Camera name is required")

    if not ip:
        raise HTTPException(status_code=400, detail="Camera IP is required")

    duplicate = (
        db.query(Camera)
        .filter(Camera.name == name, Camera.id != camera_id)
        .first()
    )

    if duplicate:
        raise HTTPException(status_code=409, detail="A camera with this name already exists")

    camera.name = name
    camera.ip = ip
    camera.stream_url = payload.stream_url.strip()
    camera.location = payload.location.strip()

    db.commit()
    db.refresh(camera)

    return camera_to_dict(camera)


@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):

    camera = (
        db.query(Camera)
        .filter(Camera.id == camera_id)
        .first()
    )

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    db.delete(camera)
    db.commit()

    return {"status": "deleted", "id": camera_id}


@router.post("/{camera_id}/check")
def check_camera_now(
    camera_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):

    camera = (
        db.query(Camera)
        .filter(Camera.id == camera_id)
        .first()
    )

    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    from .services.camera_service import check_camera

    alert = check_camera(db, camera)

    db.refresh(camera)

    return {
        "id": camera.id,
        "status": camera.status,
        "last_seen": camera.last_seen.isoformat() if camera.last_seen else None,
        "alert_created": alert is not None,
    }