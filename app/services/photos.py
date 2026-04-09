# app/services/photos.py

from sqlalchemy.orm import Session
from app.models import Photo


def photo_exists(
    db: Session,
    user_id: int,
    sha256: str,
) -> bool:
    return (
        db.query(Photo)
        .filter(
            Photo.user_id == user_id,
            Photo.sha256 == sha256,
        )
        .first()
        is not None
    )
