# app/routers/devices.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.schemas.devices import DeviceRegisterRequest, DeviceRegisterResponse
from app.database import SessionLocal
from app.models import Device, User
from app.deps import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(
    payload: DeviceRegisterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = (
        db.query(Device)
        .filter(Device.device_uid == payload.device_uid)
        .first()
    )

    if device:
        if device.user_id != user.id:
            raise HTTPException(403, "Device belongs to another user")

        if device.status != "ACTIVE":
            raise HTTPException(403, "Device is blocked")

        device.last_seen_at = datetime.utcnow()
        db.commit()

        return DeviceRegisterResponse(status="already_registered")

    device = Device(
        user_id=user.id,
        device_uid=payload.device_uid,
        device_name=payload.device_name,
        status="ACTIVE",
        last_seen_at=datetime.utcnow(),
    )

    db.add(device)
    db.commit()

    return DeviceRegisterResponse(status="registered")
