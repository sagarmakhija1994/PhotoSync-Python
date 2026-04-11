import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

# --- EXACT IMPORTS BASED ON YOUR ARCHITECTURE ---
from app.deps import get_db, get_current_user
from app.system_settings import get_setting
from app.services.storage import safe_join
from app.models import User, Photo, Device, Album, AlbumPhoto, SharedAccess

router = APIRouter(prefix="/albums", tags=["Albums"])


# --- SCHEMAS ---
class AlbumCreate(BaseModel):
    name: str


class AddPhotosRequest(BaseModel):
    photo_ids: List[int]


class ShareRequest(BaseModel):
    target_username: str


class ImportPhotoRequest(BaseModel):
    photo_id: int


# --- 1. CREATE ALBUM ---
@router.post("/create")
def create_album(request: AlbumCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_album = Album(name=request.name, owner_id=user.id)
    db.add(new_album)
    db.commit()
    db.refresh(new_album)
    return {"status": "success", "album_id": new_album.id, "name": new_album.name}


# --- 2. GET MY ALBUMS (Owned & Shared with me) ---
@router.get("/")
def get_albums(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned_albums = db.query(Album).filter(Album.owner_id == user.id).all()

    # Find albums shared with this user
    shared_accesses = db.query(SharedAccess).filter(SharedAccess.shared_with_user_id == user.id).all()
    shared_album_ids = [access.album_id for access in shared_accesses]
    shared_albums = db.query(Album).filter(Album.id.in_(shared_album_ids)).all()

    return {
        "owned": [{"id": a.id, "name": a.name} for a in owned_albums],
        "shared_with_me": [{"id": a.id, "name": a.name, "owner_id": a.owner_id} for a in shared_albums]
    }


# --- 3. ADD PHOTOS TO ALBUM ---
@router.post("/{album_id}/add-photos")
def add_photos(album_id: int, request: AddPhotosRequest, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or not owned by you.")

    added_count = 0
    for pid in request.photo_ids:
        # Check if it's already in the album to prevent duplicates
        exists = db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id, AlbumPhoto.photo_id == pid).first()
        if not exists:
            db.add(AlbumPhoto(album_id=album_id, photo_id=pid))
            added_count += 1

    db.commit()
    return {"status": "success", "added": added_count}


# --- 4. SHARE ALBUM ---
@router.post("/{album_id}/share")
def share_album(album_id: int, request: ShareRequest, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found.")

    target_user = db.query(User).filter(User.username == request.target_username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    exists = db.query(SharedAccess).filter(SharedAccess.album_id == album_id,
                                           SharedAccess.shared_with_user_id == target_user.id).first()
    if not exists:
        db.add(SharedAccess(album_id=album_id, shared_with_user_id=target_user.id))
        db.commit()

    return {"status": "success", "message": f"Shared with {target_user.username}"}


# --- 5. THE DISASTER RECOVERY IMPORT FUNCTION ---
@router.post("/import-photo")
def import_shared_photo(request: ImportPhotoRequest, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Physically copies a shared photo into the importing user's own hard drive folder."""
    original_photo = db.query(Photo).filter(Photo.id == request.photo_id).first()
    if not original_photo:
        raise HTTPException(status_code=404, detail="Photo not found.")

    storage_root = get_setting(db, "STORAGE_ROOT")
    if not storage_root:
        raise HTTPException(status_code=500, detail="Storage root not configured.")

    # 1. Find original physical file
    orig_owner = db.query(User).filter(User.id == original_photo.user_id).first()
    orig_device = db.query(Device).filter(Device.id == original_photo.device_id).first()

    # USING YOUR SAFE_JOIN METHOD
    orig_path = safe_join(storage_root, "users", orig_owner.username, orig_device.device_name,
                          original_photo.relative_path)

    if not os.path.exists(orig_path):
        raise HTTPException(status_code=404, detail="Original physical file missing from disk.")

    # 2. Create an "Imported" virtual device for the current user to keep things organized
    imported_device = db.query(Device).filter(Device.user_id == user.id, Device.device_name == "Imported").first()
    if not imported_device:
        imported_device = Device(user_id=user.id, device_name="Imported", device_uid="virtual_imported")
        db.add(imported_device)
        db.commit()
        db.refresh(imported_device)

    # 3. Setup new paths
    filename = os.path.basename(orig_path)
    new_relative_path = filename
    new_dir = safe_join(storage_root, "users", user.username, "Imported")
    new_thumb_dir = safe_join(new_dir, "thumbnails")
    os.makedirs(new_thumb_dir, exist_ok=True)

    new_path = safe_join(new_dir, filename)
    new_thumb_path = safe_join(new_thumb_dir, filename)

    # 4. PHYSICAL FILE COPY
    if not os.path.exists(new_path):
        shutil.copy2(orig_path, new_path)

    # Copy thumbnail if it exists
    orig_thumb_path = safe_join(os.path.dirname(orig_path), "thumbnails", filename)
    if os.path.exists(orig_thumb_path) and not os.path.exists(new_thumb_path):
        shutil.copy2(orig_thumb_path, new_thumb_path)

    # 5. Database Entry
    existing_copy = db.query(Photo).filter(Photo.user_id == user.id,
                                           Photo.file_hash == original_photo.file_hash).first()
    if not existing_copy:
        new_photo = Photo(
            user_id=user.id,
            device_id=imported_device.id,
            relative_path=new_relative_path,
            file_hash=original_photo.file_hash,
            file_size=original_photo.file_size
        )
        db.add(new_photo)
        db.commit()
        db.refresh(new_photo)
        return {"status": "success", "new_photo_id": new_photo.id, "message": "Physically copied to your space!"}

    return {"status": "already_imported", "photo_id": existing_copy.id}


# --- 6. GET ALBUM DETAILS & PHOTOS ---
@router.get("/{album_id}")
def get_album_details(album_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found.")

    # Security check: Are you the owner, or was it shared with you?
    if album.owner_id != user.id:
        access = db.query(SharedAccess).filter(SharedAccess.album_id == album_id,
                                               SharedAccess.shared_with_user_id == user.id).first()
        if not access:
            raise HTTPException(status_code=403, detail="Access denied.")

    # Fetch the photos and join with the Device table to get the device_name
    album_photos = db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).all()
    photo_ids = [ap.photo_id for ap in album_photos]

    photos = db.query(Photo, Device).join(Device, Photo.device_id == Device.id).filter(Photo.id.in_(photo_ids)).all()

    photo_list = [
        {"id": p.Photo.id, "device_name": p.Device.device_name, "file_size": p.Photo.file_size}
        for p in photos
    ]

    return {"id": album.id, "name": album.name, "owner_id": album.owner_id, "photos": photo_list}