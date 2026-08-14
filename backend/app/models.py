from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from .database import Base


class Device(Base):

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    hostname = Column(String, unique=True, index=True)
    ip = Column(String)

    cpu = Column(Float)
    ram = Column(Float)
    disk = Column(Float)

    status = Column(String)

    department = Column(String)
    lab = Column(String)
    location = Column(String)
    os = Column(String)
    architecture = Column(String)

    agent_token = Column(String, unique=True, index=True)

    last_seen = Column(
        DateTime,
        default=datetime.utcnow
    )
