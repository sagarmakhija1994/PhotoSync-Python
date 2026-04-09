# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import SessionLocal
from app.models import User, Device
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register(
    username: str,
    email: str,
    password: str,
    device_name: str,
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        status="PENDING",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Registration successful. Await admin approval."
    }


@router.post("/login")
def login(
    username: str,
    password: str,
    device_uid: str, # Matches the Android @Query parameter
    device_name: str,
    db: Session = Depends(get_db),
):
    # 1. Verify User Credentials
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2. Check if User is Approved
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail=f"Account status: {user.status}",
        )

    # 3. Lookup Device using the correct model attribute 'device_uid'
    device = (
        db.query(Device)
        .filter(Device.device_uid == device_uid)
        .first()
    )

    # 4. Create Device entry if it doesn't exist
    if not device:
        # 2. First time this phone has EVER connected to the server
        device = Device(
            user_id=user.id,
            device_uid=device_uid,
            device_name=device_name,
            status="ACTIVE"
        )
        db.add(device)
    else:
        # 3. Phone exists! Update it to belong to the new user logging in
        device.user_id = user.id
        device.device_name = device_name

    # 5. Update Activity Timestamp
    device.last_seen_at = datetime.utcnow() # Matches models.py field name
    db.commit()

    # 6. Generate JWT Token
    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "device_id": device_uid, # Payload key is just a string, device_uid is the value
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }