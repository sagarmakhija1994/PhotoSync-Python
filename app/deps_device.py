# app/deps_device.py

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Device
from datetime import datetime


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_device(
    x_device_id: str = Header(..., alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> Device:
    device = db.query(Device).filter(Device.device_uid == x_device_id).first()

    if not device or device.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Device not registered")

    device.last_seen_at = datetime.utcnow()
    db.commit()

    return device