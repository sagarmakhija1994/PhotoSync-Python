# app/routers/photos.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.photos import PhotoCheckRequest, PhotoCheckResponse
from app.services.photos import photo_exists
from app.deps import get_current_user, get_db
from app.deps_device import get_current_device
from app.models import User, Device

from fastapi import UploadFile, File, Form, HTTPException
import os
import shutil
import uuid
from datetime import datetime

from app.models import Photo
from app.services.storage import safe_join, compute_sha256
from app.system_settings import get_setting

router = APIRouter(prefix="/photos", tags=["photos"])


@router.post("/check", response_model=PhotoCheckResponse)
def check_photo_exists(
    payload: PhotoCheckRequest,
    user: User = Depends(get_current_user),
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    exists = photo_exists(
        db=db,
        user_id=user.id,
        sha256=payload.sha256,
    )

    return PhotoCheckResponse(exists=exists)


@router.post("/upload_old")
def upload_photo(
    file: UploadFile = File(...),
    sha256: str = Form(...),
    relative_path: str = Form(...),
    media_type: str = Form(...),
    user: User = Depends(get_current_user),
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    # Dedup check (hard safety)
    exists = photo_exists(db, user.id, sha256)
    if exists:
        return {"status": "skipped"}

    storage_root = get_setting(db, "STORAGE_ROOT")
    if not storage_root:
        raise HTTPException(500, "Storage root not configured")

    # Final destination
    dest_dir = safe_join(
        storage_root,
        "users",
        user.username,
        device.device_name,
        os.path.dirname(relative_path),
    )

    os.makedirs(dest_dir, exist_ok=True)

    final_path = safe_join(
        storage_root,
        "users",
        user.username,
        device.device_name,
        relative_path,
    )

    # Write to temp file first
    tmp_path = final_path + f".tmp-{uuid.uuid4().hex}"

    try:
        with open(tmp_path, "wb") as out:
            shutil.copyfileobj(file.file, out)

        # Verify hash
        actual_hash = compute_sha256(tmp_path)
        if actual_hash != sha256:
            os.remove(tmp_path)
            raise HTTPException(400, "SHA256 mismatch")

        # Atomic rename
        os.replace(tmp_path, final_path)

    finally:
        file.file.close()
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Record in DB
    photo = Photo(
        user_id=user.id,
        device_id=device.id,
        sha256=sha256,
        file_size=os.path.getsize(final_path),
        media_type=media_type,
        relative_path=relative_path,
        created_at=datetime.utcnow(),
    )

    db.add(photo)
    db.commit()

    return {"status": "uploaded"}
