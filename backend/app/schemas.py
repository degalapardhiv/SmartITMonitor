from pydantic import BaseModel
from datetime import datetime


class DeviceCreate(BaseModel):
    hostname: str
    ip: str
    cpu: float
    ram: float
    disk: float
    status: str

    department: str
    lab: str
    location: str
    os: str


class DeviceResponse(BaseModel):
    id: int

    hostname: str
    ip: str

    cpu: float
    ram: float
    disk: float

    status: str

    department: str
    lab: str
    location: str
    os: str

    last_seen: datetime

    class Config:
        from_attributes = True


class AgentRegister(BaseModel):
    hostname: str
    ip: str
    os: str


class AgentRegisterResponse(BaseModel):
    device_id: int
    agent_token: str
