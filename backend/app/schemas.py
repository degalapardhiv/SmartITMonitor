from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DeviceCreate(BaseModel):
    hostname: str
    ip: str
    cpu: float
    ram: float
    disk: float
    status: str = "online"

    department: str
    lab: str
    location: str
    os: str


class DeviceResponse(BaseModel):
    id: int

    hostname: str
    ip: str

    cpu: Optional[float] = None
    ram: Optional[float] = None
    disk: Optional[float] = None

    status: str

    department: Optional[str] = None
    lab: Optional[str] = None
    location: Optional[str] = None
    os: Optional[str] = None

    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentRegister(BaseModel):
    hostname: str
    ip: str
    os: str
    department: str | None = None
    lab: str | None = None
    location: str | None = None


class AgentRegisterResponse(BaseModel):
    device_id: int
    agent_token: str
