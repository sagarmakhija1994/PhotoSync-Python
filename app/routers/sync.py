import os
import shutil
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt
from typing import List
from PIL import Image
from fastapi.responses import FileResponse

# Import your database and models
from app.database import SessionLocal
from app.models import User, Device, SystemSetting, Photo
from app.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/photos", tags=["photos"])
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_context(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        device_uid = payload.get("device_id")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    device = db.query(Device).filter(Device.device_uid == device_uid).first()

    if not user or not device:
        raise HTTPException(status_code=401, detail="Auth failed")

    return {"user": user, "device": device}


# --- SINGLE SOURCE OF TRUTH FOR PATHS ---
def build_file_path(db: Session, username: str, device_name: str, raw_path: str) -> str:
    """Guarantees the exact same file path is generated for Upload, Check, and Serve."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == "storage_path").first()

    # Base path from DB or fallback
    base_storage_path = setting.value.strip() if setting and setting.value else r"C:\photosync-data"

    clean_user = username.strip()
    clean_device = device_name.strip()

    # Clean the path sent by Android (e.g., "DCIM/Camera/IMG_01.jpg")
    clean_raw = raw_path.strip().strip('"').strip()

    # Normalize slashes for Windows and remove leading slashes
    clean_relative = clean_raw.replace("/", os.sep).replace("\\", os.sep).lstrip(os.sep)

    # THE FIX: Added the "users" folder into the join to match your hard drive!
    return os.path.abspath(os.path.join(base_storage_path, "users", clean_user, clean_device, clean_relative))


# --- MODELS ---
class PhotoCheckRequest(BaseModel):
    sha256: str
    file_size: int
    media_type: str


class PhotoCheckItem(BaseModel):
    sha256: str
    file_size: int
    media_type: str


class PhotoBatchCheckRequest(BaseModel):
    items: List[PhotoCheckItem]


# --- 1. THE BATCH CHECK ENDPOINT (Self-Healing) ---
@router.post("/check-batch")
def check_photos_batch(
        request: PhotoBatchCheckRequest,
        context: dict = Depends(get_current_context),
        db: Session = Depends(get_db)
):
    user = context["user"]
    incoming_hashes = [item.sha256.strip() for item in request.items]

    print("\n" + "=" * 50)
    print("🔍 BATCH CHECK DEBUG TRACE")
    print(f"1. Phone is asking about {len(incoming_hashes)} hashes.")

    existing_records = db.query(Photo).filter(
        Photo.user_id == user.id,
        Photo.sha256.in_(incoming_hashes)
    ).all()

    print(f"2. Database recognized {len(existing_records)} of those hashes.")

    verified_hashes = []

    for record in existing_records:
        device = db.query(Device).filter(Device.id == record.device_id).first()

        # USE THE HELPER TO GUARANTEE MATCH
        expected_path = build_file_path(db, user.username, device.device_name, record.relative_path)

        print(f"3. Verifying physical file at:\n   -> {expected_path}")

        if os.path.exists(expected_path):
            print("   -> STATUS: File EXISTS! ✅")
            verified_hashes.append(record.sha256)
        else:
            print("   -> STATUS: GHOST FILE (Missing)! ❌ Deleting DB record.")
            db.delete(record)

    db.commit()
    print(f"4. Telling phone to skip {len(verified_hashes)} files.")
    print("=" * 50 + "\n")

    return {"existing_hashes": verified_hashes}


# --- 2. SINGLE CHECK ENDPOINT (Fallback) ---
@router.post("/check")
def check_photo(
        request: PhotoCheckRequest,
        context: dict = Depends(get_current_context),
        db: Session = Depends(get_db)
):
    user = context["user"]
    existing_photo = db.query(Photo).filter(
        Photo.user_id == user.id,
        Photo.sha256 == request.sha256.strip()
    ).first()

    return {"exists": existing_photo is not None}


# --- 3. GALLERY LIST ENDPOINT ---
@router.get("/list")
def list_photos(
        context: dict = Depends(get_current_context),
        db: Session = Depends(get_db)
):
    user = context["user"]

    # Join the Photo and Device tables to get the device_name
    photos = db.query(Photo, Device.device_name) \
        .join(Device, Photo.device_id == Device.id) \
        .filter(Photo.user_id == user.id) \
        .order_by(Photo.created_at.desc()) \
        .all()

    # Format the JSON response
    result = []
    for photo, device_name in photos:
        result.append({
            "id": photo.id,
            "filename": os.path.basename(photo.relative_path.replace("\\", "/")),
            "device_name": device_name,
            "media_type": photo.media_type,
            "file_size": photo.file_size,
            "created_at": photo.created_at.isoformat()
        })

    return {"photos": result}


# --- 4. SECURE FILE / THUMBNAIL SERVER ---
@router.get("/file/{photo_id}")
def get_photo_file(
        photo_id: int,
        thumbnail: bool = False,
        context: dict = Depends(get_current_context),
        db: Session = Depends(get_db)
):
    user = context["user"]

    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.user_id == user.id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    device = db.query(Device).filter(Device.id == photo.device_id).first()

    # USE THE HELPER TO GUARANTEE MATCH
    original_path = build_file_path(db, user.username, device.device_name, photo.relative_path)

    if thumbnail and photo.media_type == "photo":
        dir_name = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        thumb_path = os.path.join(dir_name, "thumbnails", filename)
        if os.path.exists(thumb_path):
            return FileResponse(thumb_path)

    if not os.path.exists(original_path):
        raise HTTPException(status_code=404, detail="Physical file is missing from server")

    return FileResponse(original_path)


# --- 5. THE UPLOAD ENDPOINT ---
@router.post("/upload")
def upload_file(
        file: UploadFile = File(...),
        sha256: str = Form(...),
        relative_path: str = Form(...),
        media_type: str = Form(...),
        context: dict = Depends(get_current_context),
        db: Session = Depends(get_db)
):
    user = context["user"]
    device = context["device"]

    # THE FIX: Strip invisible newlines and quotes from Retrofit MultiPart forms
    clean_sha256 = sha256.strip().strip('"')
    clean_path = relative_path.strip().strip('"')
    clean_media = media_type.strip().strip('"')

    # USE THE HELPER TO GUARANTEE MATCH
    file_path = build_file_path(db, user.username, device.device_name, clean_path)

    # Ensure all directories exist (e.g. DCIM, Camera)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

            # Force physical write to disk before database logging
            buffer.flush()
            os.fsync(buffer.fileno())

        new_photo = Photo(
            user_id=user.id,
            device_id=device.id,
            sha256=clean_sha256,
            file_size=os.path.getsize(file_path),
            media_type=clean_media,
            relative_path=clean_path
        )
        db.add(new_photo)

        # Safe Thumbnail Generation
        if clean_media == "photo":
            print("DEBUG: Attempting to generate thumbnail...")
            try:
                thumb_path = generate_thumbnail(file_path)
                print(f"✅ THUMBNAIL SUCCESS: {thumb_path}")
            except Exception as e:
                print(f"❌ THUMBNAIL FAILED for {file.filename}: {str(e)}")

        db.commit()
        print(f"✅ UPLOAD SUCCESS: Saved at {file_path}")
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# --- UTILITIES ---
def generate_thumbnail(original_path: str):
    # 1. Create a hidden .thumbnails folder in the same directory
    dir_name = os.path.dirname(original_path)
    thumb_dir = os.path.join(dir_name, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)

    # 2. Build the thumbnail path
    base_name = os.path.basename(original_path)
    thumb_path = os.path.join(thumb_dir, base_name)

    # 3. Open and resize
    with Image.open(original_path) as img:
        # Maintain aspect ratio
        img.thumbnail((400, 400))
        # Convert to RGB (in case of PNG with transparency)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(thumb_path, "JPEG", quality=80)

    return thumb_path