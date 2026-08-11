from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth_dependency import get_current_user
from .database import SessionLocal
from .department_model import Department
from .models import Device
from .role_dependency import require_admin


router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
)


class DepartmentCreate(BaseModel):
    name: str


class DepartmentUpdate(BaseModel):
    name: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _normalize(name):
    return name.strip()


@router.get("")
def list_departments(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    departments = (
        db.query(Department)
        .order_by(Department.name.asc())
        .all()
    )

    return [
        {"id": dept.id, "name": dept.name}
        for dept in departments
    ]


@router.post("")
def create_department(
    payload: DepartmentCreate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = _normalize(payload.name)

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Department name cannot be empty",
        )

    existing = (
        db.query(Department)
        .filter(Department.name == name)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Department already exists",
        )

    department = Department(name=name)

    db.add(department)
    db.commit()
    db.refresh(department)

    return {"id": department.id, "name": department.name}


@router.put("/{department_id}")
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = _normalize(payload.name)

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Department name cannot be empty",
        )

    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found",
        )

    duplicate = (
        db.query(Department)
        .filter(
            Department.name == name,
            Department.id != department_id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Department already exists",
        )

    old_name = department.name
    department.name = name

    db.commit()

    db.query(Device).filter(
        Device.department == old_name
    ).update(
        {Device.department: name}
    )

    db.commit()

    return {"id": department.id, "name": department.name}


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Department not found",
        )

    db.query(Device).filter(
        Device.department == department.name
    ).update(
        {Device.department: "Unknown"}
    )

    db.delete(department)
    db.commit()

    return {"status": "deleted"}