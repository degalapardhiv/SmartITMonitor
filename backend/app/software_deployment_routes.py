import os as os_module
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .agent_auth import get_agent_device
from .database import SessionLocal
from .models import Device
from .role_dependency import require_admin
from .software_deployment_model import (
    DeviceGroup,
    DeviceGroupMember,
    SoftwareDeployment,
    SoftwareDeploymentEvent,
    SoftwareDeploymentTarget,
    SoftwareInventory,
    SoftwarePackage,
)
from .software_deployment_service import (
    ACTION_WHITELIST,
    MAX_RETRY_ATTEMPTS,
    PACKAGE_DIR,
    SCOPE_WHITELIST,
    add_event,
    broadcast_deployment_update,
    deployment_summary,
    package_file_path,
    refresh_deployment_status,
    resolve_targets,
    sha256_file,
)


router = APIRouter(
    prefix="/software",
    tags=["Software Deployment"],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _package_dict(package):
    return {
        "id": package.id,
        "name": package.name,
        "version": package.version,
        "publisher": package.publisher,
        "os": package.os,
        "architecture": package.architecture,
        "file_name": package.file_name,
        "file_size": package.file_size,
        "checksum": package.checksum,
        "checksum_type": package.checksum_type,
        "install_command": package.install_command,
        "uninstall_command": package.uninstall_command,
        "verify_command": package.verify_command,
        "install_timeout_seconds": package.install_timeout_seconds,
        "approval_status": package.approval_status,
        "approved_by": package.approved_by,
        "notes": package.notes,
        "created_by": package.created_by,
        "created_at": package.created_at.isoformat()
        if package.created_at
        else None,
    }


def _deployment_dict(db, deployment):
    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == deployment.package_id)
        .first()
    )

    return {
        "id": deployment.id,
        "package": _package_dict(package) if package else None,
        "action": deployment.action,
        "scope": deployment.scope,
        "scope_ref": deployment.scope_ref,
        "status": deployment.status,
        "created_by": deployment.created_by,
        "created_at": deployment.created_at.isoformat()
        if deployment.created_at
        else None,
        "started_at": deployment.started_at.isoformat()
        if deployment.started_at
        else None,
        "completed_at": deployment.completed_at.isoformat()
        if deployment.completed_at
        else None,
        "summary": deployment_summary(db, deployment.id),
    }


def _target_dict(target):
    return {
        "id": target.id,
        "deployment_id": target.deployment_id,
        "device_id": target.device_id,
        "hostname": target.hostname,
        "status": target.status,
        "progress": target.progress,
        "detail": target.detail,
        "attempt_count": target.attempt_count,
        "started_at": target.started_at.isoformat()
        if target.started_at
        else None,
        "completed_at": target.completed_at.isoformat()
        if target.completed_at
        else None,
    }


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------


@router.get("/packages")
def list_packages(
    approval: str = "",
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(SoftwarePackage).order_by(
        SoftwarePackage.name,
        SoftwarePackage.version.desc(),
    )

    if approval in ("approved", "pending", "rejected"):
        query = query.filter(
            SoftwarePackage.approval_status == approval
        )

    return {
        "packages": [
            _package_dict(pkg) for pkg in query.all()
        ]
    }


@router.post("/packages")
async def create_package(
    name: str = Form(...),
    version: str = Form(...),
    publisher: str = Form(""),
    os: str = Form("windows"),
    architecture: str = Form(""),
    install_command: str = Form(""),
    uninstall_command: str = Form(""),
    verify_command: str = Form(""),
    install_timeout_seconds: int = Form(600),
    notes: str = Form(""),
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = name.strip()
    version = version.strip()

    if not name or not version:
        raise HTTPException(
            status_code=400,
            detail="name and version are required",
        )

    if os not in ("windows", "linux", "macos", ""):
        raise HTTPException(
            status_code=400,
            detail="os must be windows, linux, macos or empty",
        )

    if architecture not in ("x64", "x86", "arm64", "arm", ""):
        raise HTTPException(
            status_code=400,
            detail=(
                "architecture must be x64, x86, arm64, arm or empty"
            ),
        )

    existing = (
        db.query(SoftwarePackage)
        .filter(
            SoftwarePackage.name == name,
            SoftwarePackage.version == version,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A package with this name and version already exists",
        )

    os_module.makedirs(PACKAGE_DIR, exist_ok=True)

    package = SoftwarePackage(
        name=name,
        version=version,
        publisher=publisher.strip(),
        os=os,
        architecture=architecture,
        file_name=file.filename or name,
        install_command=install_command.strip(),
        uninstall_command=uninstall_command.strip(),
        verify_command=verify_command.strip(),
        install_timeout_seconds=install_timeout_seconds,
        notes=notes.strip(),
        approval_status="pending",
        created_by=current_user["username"],
    )

    db.add(package)
    db.commit()
    db.refresh(package)

    path = package_file_path(package)

    size = 0
    digest = sha256_new()

    try:
        with open(path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
                size += len(chunk)
                digest.update(chunk)
    except Exception:
        db.delete(package)
        db.commit()
        if os_module.path.exists(path):
            os_module.remove(path)
        raise HTTPException(
            status_code=500,
            detail="Failed to store package file",
        )

    package.file_size = size
    package.checksum = digest.hexdigest()
    package.checksum_type = "sha256"
    db.commit()
    db.refresh(package)

    return _package_dict(package)


def sha256_new():
    import hashlib

    return hashlib.sha256()


@router.put("/packages/{package_id}")
def update_package(
    package_id: int,
    payload: dict,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == package_id)
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    editable = {
        "publisher",
        "install_command",
        "uninstall_command",
        "verify_command",
        "install_timeout_seconds",
        "notes",
    }

    for key, value in (payload or {}).items():
        if key not in editable:
            continue
        setattr(package, key, value)

    package.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(package)

    return _package_dict(package)


class ApprovePayload(BaseModel):
    approval_status: str


@router.post("/packages/{package_id}/approve")
def approve_package(
    package_id: int,
    payload: ApprovePayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.approval_status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="approval_status must be approved or rejected",
        )

    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == package_id)
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    package.approval_status = payload.approval_status
    package.approved_by = current_user["username"]
    package.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(package)

    return _package_dict(package)


@router.delete("/packages/{package_id}")
def delete_package(
    package_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == package_id)
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    active = (
        db.query(SoftwareDeployment)
        .filter(
            SoftwareDeployment.package_id == package_id,
            SoftwareDeployment.status.in_(
                ("pending", "running")
            ),
        )
        .first()
    )

    if active:
        raise HTTPException(
            status_code=409,
            detail="Package is in use by an active deployment",
        )

    path = package_file_path(package)

    if os_module.path.exists(path):
        os_module.remove(path)

    db.delete(package)
    db.commit()

    return {"status": "deleted"}


@router.get("/packages/{package_id}/download")
def admin_download_package(
    package_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == package_id)
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    path = package_file_path(package)

    if not os_module.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Package file is missing",
        )

    return FileResponse(
        path,
        filename=package.file_name,
        media_type="application/octet-stream",
    )


# ---------------------------------------------------------------------------
# Device groups
# ---------------------------------------------------------------------------


@router.get("/groups")
def list_groups(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    groups = db.query(DeviceGroup).order_by(DeviceGroup.name).all()

    result = []

    for group in groups:
        count = (
            db.query(DeviceGroupMember)
            .filter(DeviceGroupMember.group_id == group.id)
            .count()
        )
        result.append(
            {
                "id": group.id,
                "name": group.name,
                "device_count": count,
            }
        )

    return {"groups": result}


class GroupPayload(BaseModel):
    name: str


@router.post("/groups")
def create_group(
    payload: GroupPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()

    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = (
        db.query(DeviceGroup)
        .filter(DeviceGroup.name == name)
        .first()
    )

    if existing:
        raise HTTPException(status_code=409, detail="Group already exists")

    group = DeviceGroup(
        name=name,
        created_by=current_user["username"],
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return {"id": group.id, "name": group.name, "device_count": 0}


@router.put("/groups/{group_id}")
def rename_group(
    group_id: int,
    payload: GroupPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = (
        db.query(DeviceGroup)
        .filter(DeviceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    name = payload.name.strip()

    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = (
        db.query(DeviceGroup)
        .filter(DeviceGroup.name == name)
        .first()
    )

    if existing and existing.id != group_id:
        raise HTTPException(status_code=409, detail="Group already exists")

    group.name = name
    db.commit()

    return {"id": group.id, "name": group.name}


@router.get("/groups/{group_id}/members")
def get_group_members(
    group_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = (
        db.query(DeviceGroup)
        .filter(DeviceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    rows = (
        db.query(DeviceGroupMember.device_id)
        .filter(DeviceGroupMember.group_id == group_id)
        .all()
    )

    return {
        "group_id": group_id,
        "device_ids": [row[0] for row in rows],
    }


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = (
        db.query(DeviceGroup)
        .filter(DeviceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.query(DeviceGroupMember).filter(
        DeviceGroupMember.group_id == group_id
    ).delete()

    db.delete(group)
    db.commit()

    return {"status": "deleted"}


class GroupMembersPayload(BaseModel):
    device_ids: list[int] = []


@router.post("/groups/{group_id}/members")
def set_group_members(
    group_id: int,
    payload: GroupMembersPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    group = (
        db.query(DeviceGroup)
        .filter(DeviceGroup.id == group_id)
        .first()
    )

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.query(DeviceGroupMember).filter(
        DeviceGroupMember.group_id == group_id
    ).delete()

    for device_id in payload.device_ids:
        db.add(
            DeviceGroupMember(
                group_id=group_id,
                device_id=device_id,
            )
        )

    db.commit()

    return {"status": "saved", "member_count": len(payload.device_ids)}


# ---------------------------------------------------------------------------
# Compatibility preview
# ---------------------------------------------------------------------------


@router.get("/preview")
def preview_deployment(
    package_id: int,
    scope: str = "all",
    scope_ref: str = "",
    device_ids: str = "",
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == package_id)
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.approval_status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved packages can be deployed",
        )

    if scope not in SCOPE_WHITELIST:
        raise HTTPException(status_code=400, detail="Invalid scope")

    ids = [
        int(item)
        for item in device_ids.split(",")
        if item.strip().isdigit()
    ]

    try:
        targets, summary = resolve_targets(
            db,
            package,
            scope,
            scope_ref,
            ids,
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid target scope reference",
        )

    return {
        "package_id": package.id,
        "package_name": f"{package.name} {package.version}",
        "scope": scope,
        "summary": {
            "total": summary["total"],
            "compatible": summary["compatible"],
            "offline": summary["offline"],
            "incompatible": summary["incompatible"],
        },
        "devices": summary["devices"],
        "targets": targets,
    }


# ---------------------------------------------------------------------------
# Deployments
# ---------------------------------------------------------------------------


class CreateDeploymentPayload(BaseModel):
    package_id: int
    action: str = "install"
    scope: str = "all"
    scope_ref: str = ""
    device_ids: list[int] = []
    confirm: bool = False


@router.post("/deployments")
def create_deployment(
    payload: CreateDeploymentPayload,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="Explicit deployment confirmation is required",
        )

    if payload.action not in ACTION_WHITELIST:
        raise HTTPException(
            status_code=400,
            detail="Action must be install, update, uninstall or enforce",
        )

    if payload.scope not in SCOPE_WHITELIST:
        raise HTTPException(status_code=400, detail="Invalid scope")

    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == payload.package_id)
        .first()
    )

    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.approval_status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved packages can be deployed",
        )

    if not package.install_command and payload.action != "uninstall":
        raise HTTPException(
            status_code=400,
            detail="Package has no predefined install command",
        )

    if (
        payload.action == "uninstall"
        and not package.uninstall_command
    ):
        raise HTTPException(
            status_code=400,
            detail="Package has no predefined uninstall command",
        )

    try:
        targets, summary = resolve_targets(
            db,
            package,
            payload.scope,
            payload.scope_ref,
            payload.device_ids,
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid target scope reference",
        )

    if not targets:
        raise HTTPException(
            status_code=400,
            detail="No compatible online or offline targets selected",
        )

    deployment = SoftwareDeployment(
        package_id=package.id,
        action=payload.action,
        scope=payload.scope,
        scope_ref=payload.scope_ref,
        status="pending",
        created_by=current_user["username"],
        started_at=datetime.utcnow(),
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    for entry in targets:
        target = SoftwareDeploymentTarget(
            deployment_id=deployment.id,
            device_id=entry["device_id"],
            hostname=entry["hostname"],
            status="offline" if entry["offline"] else "pending",
            progress=0,
        )
        db.add(target)

    db.commit()

    add_event(
        db,
        deployment.id,
        (
            f"Deployment created by {current_user['username']}: "
            f"{package.name} {package.version} ({payload.action}) "
            f"scope={payload.scope} targets={len(targets)}"
        ),
        level="audit",
        actor=current_user["username"],
    )

    refresh_deployment_status(db, deployment)

    broadcast_deployment_update(deployment.id)

    return _deployment_dict(db, deployment)


@router.get("/deployments")
def list_deployments(
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    deployments = (
        db.query(SoftwareDeployment)
        .order_by(SoftwareDeployment.id.desc())
        .limit(100)
        .all()
    )

    return {
        "deployments": [
            _deployment_dict(db, deployment)
            for deployment in deployments
        ]
    }


@router.get("/deployments/{deployment_id}")
def get_deployment(
    deployment_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    deployment = (
        db.query(SoftwareDeployment)
        .filter(SoftwareDeployment.id == deployment_id)
        .first()
    )

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    targets = (
        db.query(SoftwareDeploymentTarget)
        .filter(
            SoftwareDeploymentTarget.deployment_id == deployment_id
        )
        .order_by(SoftwareDeploymentTarget.hostname)
        .all()
    )

    return {
        **_deployment_dict(db, deployment),
        "targets": [
            _target_dict(target) for target in targets
        ],
    }


@router.get("/deployments/{deployment_id}/events")
def get_deployment_events(
    deployment_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    events = (
        db.query(SoftwareDeploymentEvent)
        .filter(
            SoftwareDeploymentEvent.deployment_id == deployment_id
        )
        .order_by(SoftwareDeploymentEvent.id.desc())
        .limit(200)
        .all()
    )

    return {
        "events": [
            {
                "id": event.id,
                "level": event.level,
                "actor": event.actor,
                "message": event.message,
                "created_at": event.created_at.isoformat()
                if event.created_at
                else None,
            }
            for event in events
        ]
    }


@router.post("/deployments/{deployment_id}/cancel")
def cancel_deployment(
    deployment_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    deployment = (
        db.query(SoftwareDeployment)
        .filter(SoftwareDeployment.id == deployment_id)
        .first()
    )

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail="Deployment is already finished",
        )

    targets = (
        db.query(SoftwareDeploymentTarget)
        .filter(
            SoftwareDeploymentTarget.deployment_id == deployment_id,
            SoftwareDeploymentTarget.status.in_(
                ("pending", "downloading", "installing", "offline")
            ),
        )
        .all()
    )

    for target in targets:
        target.status = "cancelled"
        target.completed_at = datetime.utcnow()

    deployment.status = "cancelled"
    deployment.completed_at = datetime.utcnow()

    db.commit()

    add_event(
        db,
        deployment.id,
        f"Deployment cancelled by {current_user['username']}",
        level="audit",
        actor=current_user["username"],
    )

    broadcast_deployment_update(deployment.id)

    return _deployment_dict(db, deployment)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


@router.get("/inventory")
def list_inventory(
    device_id: int | None = None,
    search: str = "",
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = (
        db.query(SoftwareInventory, Device.hostname)
        .join(
            Device,
            Device.id == SoftwareInventory.device_id,
        )
    )

    if device_id:
        query = query.filter(
            SoftwareInventory.device_id == device_id
        )

    if search:
        query = query.filter(
            SoftwareInventory.name.ilike(f"%{search}%")
        )

    rows = (
        query.order_by(
            SoftwareInventory.name,
            SoftwareInventory.device_id,
        )
        .limit(500)
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "device_id": row.device_id,
                "device": hostname,
                "name": row.name,
                "version": row.version,
                "publisher": row.publisher,
                "install_date": row.install_date.isoformat()
                if row.install_date
                else None,
            }
            for row, hostname in rows
        ]
    }


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@router.post("/agent/device-info")
def agent_device_info(
    payload: dict,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    device = (
        db.query(Device)
        .filter(Device.id == agent_device["id"])
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if payload.get("os"):
        device.os = payload["os"]

    if payload.get("architecture"):
        device.architecture = payload["architecture"]

    device.last_seen = datetime.utcnow()
    device.status = "online"
    db.commit()

    return {"status": "updated"}


@router.get("/agent/work")
def agent_software_work(
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()

    active = (
        db.query(SoftwareDeployment)
        .filter(
            SoftwareDeployment.status.in_(("pending", "running"))
        )
        .all()
    )

    active_ids = {deployment.id for deployment in active}

    if not active_ids:
        return {"jobs": []}

    targets = (
        db.query(SoftwareDeploymentTarget)
        .filter(
            SoftwareDeploymentTarget.device_id == agent_device["id"],
            SoftwareDeploymentTarget.deployment_id.in_(active_ids),
        )
        .all()
    )

    jobs = []
    claimed = []

    for target in targets:
        status = (target.status or "").lower()

        if status in ("completed", "cancelled"):
            continue

        retryable_failure = (
            status == "failed"
            and target.attempt_count < MAX_RETRY_ATTEMPTS
            and (
                target.next_retry_at is None
                or target.next_retry_at <= now
            )
        )

        if status not in ("pending", "offline", "downloading"):
            if not retryable_failure:
                continue

        deployment = (
            db.query(SoftwareDeployment)
            .filter(
                SoftwareDeployment.id == target.deployment_id
            )
            .first()
        )

        if not deployment:
            continue

        package = (
            db.query(SoftwarePackage)
            .filter(SoftwarePackage.id == deployment.package_id)
            .first()
        )

        if not package or package.approval_status != "approved":
            continue

        target.attempt_count += 1
        target.status = "pending"
        target.started_at = target.started_at or now
        claimed.append(target)

        jobs.append(
            {
                "target_id": target.id,
                "deployment_id": deployment.id,
                "action": deployment.action,
                "package": {
                    "id": package.id,
                    "name": package.name,
                    "version": package.version,
                    "publisher": package.publisher,
                    "file_name": package.file_name,
                    "checksum": package.checksum,
                    "checksum_type": package.checksum_type,
                    "install_command": package.install_command,
                    "uninstall_command": package.uninstall_command,
                    "verify_command": package.verify_command,
                    "install_timeout_seconds": package.install_timeout_seconds,
                },
            }
        )

    if claimed:
        db.commit()

    return {"jobs": jobs}


@router.get("/agent/download/{target_id}")
def agent_download_package(
    target_id: int,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    target = (
        db.query(SoftwareDeploymentTarget)
        .filter(SoftwareDeploymentTarget.id == target_id)
        .first()
    )

    if not target or target.device_id != agent_device["id"]:
        raise HTTPException(
            status_code=404,
            detail="Target not found for this device",
        )

    deployment = (
        db.query(SoftwareDeployment)
        .filter(SoftwareDeployment.id == target.deployment_id)
        .first()
    )

    if not deployment or deployment.status == "cancelled":
        raise HTTPException(
            status_code=404,
            detail="Deployment not found",
        )

    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == deployment.package_id)
        .first()
    )

    if not package or package.approval_status != "approved":
        raise HTTPException(
            status_code=403,
            detail="Package is not approved",
        )

    path = package_file_path(package)

    if not os_module.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Package file is missing",
        )

    target.status = "downloading"
    target.detail = "Downloading package"
    db.commit()

    return FileResponse(
        path,
        filename=package.file_name,
        media_type="application/octet-stream",
    )


class AgentStatusPayload(BaseModel):
    target_id: int
    status: str
    progress: int = 0
    detail: str = ""


@router.post("/agent/status")
def agent_update_status(
    payload: AgentStatusPayload,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    target = (
        db.query(SoftwareDeploymentTarget)
        .filter(SoftwareDeploymentTarget.id == payload.target_id)
        .first()
    )

    if not target or target.device_id != agent_device["id"]:
        raise HTTPException(status_code=404, detail="Target not found")

    if target.status in ("completed", "cancelled"):
        return _target_dict(target)

    if payload.status not in ("downloading", "installing"):
        raise HTTPException(status_code=400, detail="Invalid status")

    target.status = payload.status
    target.progress = max(0, min(100, payload.progress))
    target.detail = payload.detail[:500]
    db.commit()

    deployment = (
        db.query(SoftwareDeployment)
        .filter(SoftwareDeployment.id == target.deployment_id)
        .first()
    )

    if deployment:
        refresh_deployment_status(db, deployment)

    broadcast_deployment_update(target.deployment_id)

    return _target_dict(target)


class AgentResultPayload(BaseModel):
    target_id: int
    success: bool
    version: str = ""
    detail: str = ""


@router.post("/agent/result")
def agent_submit_result(
    payload: AgentResultPayload,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    target = (
        db.query(SoftwareDeploymentTarget)
        .filter(SoftwareDeploymentTarget.id == payload.target_id)
        .first()
    )

    if not target or target.device_id != agent_device["id"]:
        raise HTTPException(status_code=404, detail="Target not found")

    if target.status in ("completed", "cancelled"):
        return _target_dict(target)

    deployment = (
        db.query(SoftwareDeployment)
        .filter(SoftwareDeployment.id == target.deployment_id)
        .first()
    )

    package = (
        db.query(SoftwarePackage)
        .filter(SoftwarePackage.id == deployment.package_id)
        .first()
    )

    target.detail = payload.detail[:500]
    target.completed_at = datetime.utcnow()

    if payload.success:
        target.status = "completed"
        target.progress = 100

        installed_version = payload.version or package.version

        inventory = (
            db.query(SoftwareInventory)
            .filter(
                SoftwareInventory.device_id == target.device_id,
                SoftwareInventory.name == package.name,
            )
            .first()
        )

        if inventory:
            inventory.version = installed_version
            inventory.publisher = package.publisher
            inventory.updated_at = datetime.utcnow()
        else:
            db.add(
                SoftwareInventory(
                    device_id=target.device_id,
                    name=package.name,
                    version=installed_version,
                    publisher=package.publisher,
                )
            )

        add_event(
            db,
            target.deployment_id,
            (
                f"{target.hostname}: {package.name} "
                f"{installed_version} completed"
            ),
            level="info",
            actor=agent_device["hostname"],
            target_id=target.id,
            device_id=target.device_id,
        )
    else:
        target.status = "failed"
        target.progress = 0

        if target.attempt_count < MAX_RETRY_ATTEMPTS:
            target.next_retry_at = datetime.utcnow() + timedelta(
                minutes=60 * target.attempt_count
            )
            target.detail = (
                f"{target.detail} (will retry, "
                f"attempt {target.attempt_count}/{MAX_RETRY_ATTEMPTS})"
            )
        else:
            target.detail = (
                f"{target.detail} (max retries reached)"
            )

        add_event(
            db,
            target.deployment_id,
            (
                f"{target.hostname}: {package.name} failed - "
                f"{payload.detail[:300]}"
            ),
            level="error",
            actor=agent_device["hostname"],
            target_id=target.id,
            device_id=target.device_id,
        )

    db.commit()

    refresh_deployment_status(db, deployment)

    broadcast_deployment_update(target.deployment_id)

    return _target_dict(target)


class AgentInventoryPayload(BaseModel):
    items: list[dict] = []


@router.post("/agent/inventory")
def agent_report_inventory(
    payload: AgentInventoryPayload,
    agent_device=Depends(get_agent_device),
    db: Session = Depends(get_db),
):
    for item in payload.items:
        name = str(item.get("name", "")).strip()

        if not name:
            continue

        version = str(item.get("version", "")).strip()
        publisher = str(item.get("publisher", "")).strip()

        row = (
            db.query(SoftwareInventory)
            .filter(
                SoftwareInventory.device_id == agent_device["id"],
                SoftwareInventory.name == name,
            )
            .first()
        )

        if row:
            if version:
                row.version = version
            if publisher:
                row.publisher = publisher
            row.updated_at = datetime.utcnow()
        else:
            db.add(
                SoftwareInventory(
                    device_id=agent_device["id"],
                    name=name,
                    version=version,
                    publisher=publisher,
                )
            )

    db.commit()

    return {"status": "saved"}
