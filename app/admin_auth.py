# app/admin_auth.py

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(request: Request):
    user_id = request.session.get("admin_user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Admin login required")

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()

    if not user or not user.is_admin or user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Admin access denied")

    return user
