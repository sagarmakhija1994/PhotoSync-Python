# app/models.py

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    status = Column(String(20), default="PENDING", nullable=False)
    is_admin = Column(Boolean, default=False)

    max_storage_gb = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    devices = relationship(
        "Device",
        back_populates="user",
        cascade="all, delete-orphan",
    )



class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    device_uid = Column(String(100), unique=True, index=True, nullable=False)
    device_name = Column(String(100), nullable=False)

    status = Column(String(20), default="ACTIVE")

    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)

    user = relationship(
        "User",
        back_populates="devices",
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(String(500), nullable=False)


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    sha256 = Column(String(64), nullable=False)
    file_size = Column(Integer, nullable=False)

    # "photo" or "video"
    media_type = Column(String(10), nullable=False)

    # Relative to device root (e.g. DCIM/Camera/IMG_001.jpg)
    relative_path = Column(String(500), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "sha256", name="uq_user_photo_hash"),
    )
