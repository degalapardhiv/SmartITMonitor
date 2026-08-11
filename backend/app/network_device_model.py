from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .database import Base


class NetworkDevice(Base):
    __tablename__ = "network_devices"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, index=True, nullable=False)
    mac = Column(String, index=True)
    hostname = Column(String)
    vendor = Column(String)
    interface = Column(String)
    network = Column(String)

    managed = Column(Boolean, default=False)
    status = Column(String, default="online")

    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
