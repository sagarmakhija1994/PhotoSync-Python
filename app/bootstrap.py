# app/bootstrap.py

from sqlalchemy.orm import Session
from app.models import User


def is_bootstrap_allowed(db: Session) -> bool:
    return db.query(User).count() == 0
