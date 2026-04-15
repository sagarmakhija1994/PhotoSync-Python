# app/routers/photos.py
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from app.database import SessionLocal # Add this if not imported!
import subprocess
import sys

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.schemas.photos import PhotoCheckRequest, PhotoCheckResponse
from app.services.photos import photo_exists
from app.deps import get_current_user, get_db
from app.deps_device import get_current_device
from app.models import User, Device
from fastapi.responses import FileResponse
from app.models import SharedAccess, AlbumPhoto # Add these two models!

from fastapi import UploadFile, File, Form, HTTPException
import os
import shutil
import uuid
from datetime import datetime

from app.models import Photo
from app.services.storage import safe_join, compute_sha256
from app.system_settings import get_setting

router = APIRouter(prefix="/photos", tags=["photos"])

class DeletePhotosRequest(BaseModel):
    photo_ids: List[int]

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

    storage_root = os.environ.get("PHOTOSYNC_STORAGE") or get_setting(db, "STORAGE_ROOT")
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


# --- 6. DELETE BATCH ENDPOINT ---
@router.post("/delete-batch")
def delete_photos_batch(
        request: DeletePhotosRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    storage_root = os.environ.get("PHOTOSYNC_STORAGE") or get_setting(db, "STORAGE_ROOT")

    # 1. Fetch only the photos that belong to THIS user
    photos_to_delete = db.query(Photo).filter(
        Photo.user_id == user.id,
        Photo.id.in_(request.photo_ids)
    ).all()

    deleted_count = 0

    for photo in photos_to_delete:
        device = db.query(Device).filter(Device.id == photo.device_id).first()

        # Calculate paths
        original_path = safe_join(storage_root, "users", user.username, device.device_name, photo.relative_path)
        dir_name = os.path.dirname(original_path)
        thumb_path = safe_join(dir_name, ".thumbnails", os.path.basename(original_path))

        # 2. Delete physical files (ignore errors if they are already missing)
        try:
            if os.path.exists(original_path): os.remove(original_path)
            if os.path.exists(thumb_path): os.remove(thumb_path)
        except Exception as e:
            print(f"File deletion error for {photo.id}: {e}")

        # 3. Delete from DB
        db.delete(photo)
        deleted_count += 1

    db.commit()
    print(f"✅ DELETED {deleted_count} photos from server.")
    return {"status": "success", "deleted": deleted_count}

# --- SERVE PHOTO / THUMBNAIL (WITH SHARED ACCESS LOGIC) ---
@router.get("/file/{photo_id}")
def get_photo_file(
    photo_id: int,
    thumbnail: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # --- THE MAGIC SECURITY UPGRADE ---
    # If the user requesting the file is NOT the owner...
    if photo.user_id != user.id:
        # Check if this specific photo is inside an album shared with this specific user
        shared = db.query(AlbumPhoto).join(
            SharedAccess, AlbumPhoto.album_id == SharedAccess.album_id
        ).filter(
            AlbumPhoto.photo_id == photo_id,
            SharedAccess.shared_with_user_id == user.id
        ).first()

        if not shared:
            # We return 404 instead of 403 so we don't even leak the fact that the photo exists!
            raise HTTPException(status_code=404, detail="Photo not found or access denied")

    # --- PATH CALCULATION ---
    storage_root = os.environ.get("PHOTOSYNC_STORAGE") or get_setting(db, "STORAGE_ROOT")
    device = db.query(Device).filter(Device.id == photo.device_id).first()
    owner = db.query(User).filter(User.id == photo.user_id).first()

    original_path = safe_join(storage_root, "users", owner.username, device.device_name, photo.relative_path)

    # --- THUMBNAIL HANDLING WITH GIF SUPPORT ---
    if thumbnail:
        dir_name = os.path.dirname(original_path)
        filename = os.path.basename(original_path)

        if photo.media_type == "video":
            thumb_path = safe_join(dir_name, ".thumbnails", f"{filename}.gif")
            mime = "image/gif"
        else:
            thumb_path = safe_join(dir_name, ".thumbnails", filename)
            mime = "image/jpeg"

        if os.path.exists(thumb_path):
            return FileResponse(thumb_path, media_type=mime)

    if not os.path.exists(original_path):
        raise HTTPException(status_code=404, detail="Physical file missing from server")

    return FileResponse(original_path)


# =====================================================================
# --- HIDDEN ADMIN MAINTENANCE: BACKGROUND GIF BACKFILL ---
# =====================================================================

def _run_gif_backfill_task():
    """The actual heavy-lifting worker that runs in the background"""
    print("\n" + "=" * 60)
    print("🎬 [BACKGROUND] STARTING SMART GIF BACKFILL")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Resolve Storage Root (Using the exact same PyInstaller-safe logic)
        storage_root = os.environ.get("PHOTOSYNC_STORAGE") or get_setting(db, "STORAGE_ROOT")
        if not storage_root:
            import json
            if getattr(sys, 'frozen', False):
                root_dir = os.path.dirname(sys.executable)
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                root_dir = os.path.dirname(os.path.dirname(current_dir))

            config_path = os.path.join(root_dir, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    if config.get("storage_path"):
                        storage_root = config["storage_path"]

        if not storage_root:
            storage_root = r"C:\photosync-data"

        # 2. Resolve FFmpeg Path
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(os.path.dirname(current_dir))

        ffmpeg_exe = os.path.join(base_dir, "bin", "ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            ffmpeg_exe = "ffmpeg"

        # 3. Find all videos
        videos = db.query(Photo).filter(Photo.media_type == "video").all()
        print(f"🔍 Found {len(videos)} videos. Analyzing for missing thumbnails...\n")

        success_count, skip_count, fail_count = 0, 0, 0

        # 4. Process Loop
        for index, video in enumerate(videos, 1):
            owner = db.query(User).filter(User.id == video.user_id).first()
            device = db.query(Device).filter(Device.id == video.device_id).first()

            original_path = safe_join(storage_root, "users", owner.username, device.device_name, video.relative_path)

            if not os.path.exists(original_path):
                fail_count += 1
                continue

            dir_name = os.path.dirname(original_path)
            thumb_dir = safe_join(dir_name, ".thumbnails")
            os.makedirs(thumb_dir, exist_ok=True)

            gif_name = f"{os.path.basename(original_path)}.gif"
            thumb_path = safe_join(thumb_dir, gif_name)

            if os.path.exists(thumb_path):
                skip_count += 1
                continue  # Skip! We already have it.

            # Generate missing GIF
            print(f"[{index}/{len(videos)}] ⚙️ Generating: {os.path.basename(original_path)}...")
            command = [
                ffmpeg_exe, "-y", "-ss", "00:00:00", "-t", "4", "-i", original_path,
                "-vf",
                "fps=5,scale=300:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
                "-loop", "0", thumb_path
            ]

            try:
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                success_count += 1
            except Exception as e:
                print(f" ❌ FAILED: {str(e)}")
                fail_count += 1

        print("\n" + "=" * 60)
        print(f"🎉 BACKFILL COMPLETE! Generated: {success_count} | Skipped: {skip_count} | Failed: {fail_count}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"CRITICAL BACKFILL ERROR: {e}")
    finally:
        db.close()


@router.post("/admin/backfill-gifs")
def trigger_gif_backfill(
        background_tasks: BackgroundTasks,
        user: User = Depends(get_current_user)  # Still secured by your JWT!
):
    """
    Hidden endpoint to trigger the video thumbnail generation job.
    Returns immediately, runs the process in the background.
    """
    # Optional: If you only want YOU to be able to run this, add:
    # if user.username != "admin": raise HTTPException(status_code=403)

    background_tasks.add_task(_run_gif_backfill_task)

    return {
        "status": "success",
        "message": "The GIF backfill process has been started in the background. Check server logs for live progress!"
    }