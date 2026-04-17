# app/routers/albums.py
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from fastapi import Query

# --- EXACT IMPORTS BASED ON YOUR ARCHITECTURE ---
from app.deps import get_db, get_current_user
from app.system_settings import get_setting
from app.services.storage import safe_join
from app.models import User, Photo, Device, Album, AlbumPhoto, SharedAccess

router = APIRouter(prefix="/albums", tags=["Albums"])


# --- SCHEMAS ---
class AlbumCreate(BaseModel):
    name: str


class RemovePhotosRequest(BaseModel):
    photo_ids: List[int]


class RenameAlbumRequest(BaseModel):
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

    # NEW: Join with User to grab the username
    shared_albums = db.query(Album, User).join(User, Album.owner_id == User.id) \
        .filter(Album.id.in_(shared_album_ids)).all()

    return {
        "owned": [{"id": a.id, "name": a.name} for a in owned_albums],
        "shared_with_me": [
            {"id": a.Album.id, "name": a.Album.name, "owner_id": a.Album.owner_id, "owner_username": a.User.username}
            for a in shared_albums]
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

    storage_root = os.environ.get("PHOTOSYNC_STORAGE") or get_setting(db, "STORAGE_ROOT")
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
    new_thumb_dir = safe_join(new_dir, ".thumbnails")
    os.makedirs(new_thumb_dir, exist_ok=True)

    new_path = safe_join(new_dir, filename)
    new_thumb_path = safe_join(new_thumb_dir, filename)

    # 4. PHYSICAL FILE COPY
    if not os.path.exists(new_path):
        shutil.copy2(orig_path, new_path)

    # Copy thumbnail if it exists
    orig_thumb_path = safe_join(os.path.dirname(orig_path), ".thumbnails", filename)
    if os.path.exists(orig_thumb_path) and not os.path.exists(new_thumb_path):
        shutil.copy2(orig_thumb_path, new_thumb_path)

    # 5. Database Entry (FIXED: sha256 and media_type)
    existing_copy = db.query(Photo).filter(Photo.user_id == user.id,
                                           Photo.sha256 == original_photo.sha256).first()
    if not existing_copy:
        new_photo = Photo(
            user_id=user.id,
            device_id=imported_device.id,
            relative_path=new_relative_path,
            sha256=original_photo.sha256,
            file_size=original_photo.file_size,
            media_type=original_photo.media_type,
            created_at=original_photo.created_at
        )
        db.add(new_photo)
        db.commit()
        db.refresh(new_photo)
        return {"status": "success", "new_photo_id": new_photo.id, "message": "Physically copied to your space!"}

    return {"status": "already_imported", "photo_id": existing_copy.id}


# --- SEARCH USERS (INSTAGRAM STYLE) ---
@router.get("/available-users")
def search_users(q: str = Query(""), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Searches for active users by username. Requires at least 3 characters."""
    if len(q) < 3:
        return []  # Return empty if they haven't typed enough

    # Search for usernames that contain the query string (case-insensitive)
    search_query = f"%{q}%"
    other_users = db.query(User).filter(
        User.id != user.id,
        User.status == "ACTIVE",
        User.username.ilike(search_query)
    ).limit(20).all()  # Safety limit so we don't send 1,000 rows

    return [{"id": u.id, "username": u.username} for u in other_users]


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
        {
            "id": p.Photo.id,
            "device_name": p.Device.device_name,
            "file_size": p.Photo.file_size,
            "media_type": p.Photo.media_type,
            "filename": os.path.basename(p.Photo.relative_path.replace("\\", "/")),
            "created_at": p.Photo.created_at.isoformat()
        }
        for p in photos
    ]

    return {"id": album.id, "name": album.name, "owner_id": album.owner_id, "photos": photo_list}


# --- 7. CLONE ENTIRE SHARED ALBUM ---
@router.post("/{album_id}/import-all")
def import_entire_album(album_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Physically copies all photos from a shared album and creates a local version of the album."""
    shared_album = db.query(Album).filter(Album.id == album_id).first()
    if not shared_album:
        raise HTTPException(status_code=404, detail="Album not found.")

    # 1. Security check
    access = db.query(SharedAccess).filter(SharedAccess.album_id == album_id,
                                           SharedAccess.shared_with_user_id == user.id).first()
    if not access and shared_album.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    # 2. Create a new local album for the importing user
    new_local_album = Album(name=f"Imported: {shared_album.name}", owner_id=user.id)
    db.add(new_local_album)
    db.commit()
    db.refresh(new_local_album)

    # 3. Get all photos from the original album
    album_photos = db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).all()

    imported_count = 0
    for ap in album_photos:
        try:
            # We call the logic manually here
            import_req = ImportPhotoRequest(photo_id=ap.photo_id)
            result = import_shared_photo(import_req, user, db)

            # Link the newly created photo (or existing copy) to the new album
            new_photo_id = result.get("new_photo_id") or result.get("photo_id")
            db.add(AlbumPhoto(album_id=new_local_album.id, photo_id=new_photo_id))
            imported_count += 1
        except Exception as e:
            print(f"Failed to import photo {ap.photo_id}: {e}")

    db.commit()
    return {"status": "success", "new_album_id": new_local_album.id, "imported_photos": imported_count}


# --- 8. RENAME ALBUM ---
@router.put("/{album_id}/rename")
def rename_album(album_id: int, request: RenameAlbumRequest, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or you don't own it.")

    album.name = request.name
    db.commit()
    return {"status": "success", "new_name": album.name}


# --- 9. DELETE ALBUM ---
@router.delete("/{album_id}")
def delete_album(
        album_id: int,
        delete_files: bool = Query(False),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or you don't own it.")

    # If the user wants to permanently delete the physical files inside this album
    if delete_files:
        storage_root = os.environ.get("PHOTOSYNC_STORAGE") or get_setting(db, "STORAGE_ROOT")
        album_photos = db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).all()

        for ap in album_photos:
            photo = db.query(Photo).filter(Photo.id == ap.photo_id, Photo.user_id == user.id).first()
            if photo:
                device = db.query(Device).filter(Device.id == photo.device_id).first()
                # Delete physical files
                original_path = safe_join(storage_root, "users", user.username, device.device_name, photo.relative_path)
                dir_name = os.path.dirname(original_path)
                thumb_path_1 = safe_join(dir_name, ".thumbnails", os.path.basename(original_path))

                try:
                    if os.path.exists(original_path): os.remove(original_path)
                    if os.path.exists(thumb_path_1): os.remove(thumb_path_1)
                except Exception as e:
                    print(f"Failed to delete file {photo.id}: {e}")

                # Delete from Photo table
                db.delete(photo)

    db.query(SharedAccess).filter(SharedAccess.album_id == album_id).delete()
    db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album_id).delete()
    db.delete(album)
    db.commit()

    return {"status": "success", "message": "Album deleted."}


# --- 10. GET ALBUM SHARE STATUS ---
@router.get("/{album_id}/shares")
def get_album_shares(album_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns a list of users this album is currently shared with."""
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or you don't own it.")

    shares = db.query(SharedAccess, User).join(User, SharedAccess.shared_with_user_id == User.id) \
        .filter(SharedAccess.album_id == album_id).all()

    return [{"id": u.User.id, "username": u.User.username} for u in shares]


# --- 11. UNSHARE ALBUM WITH SPECIFIC USER ---
@router.delete("/{album_id}/share/{target_user_id}")
def unshare_album(album_id: int, target_user_id: int, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or you don't own it.")

    deleted = db.query(SharedAccess).filter(
        SharedAccess.album_id == album_id,
        SharedAccess.shared_with_user_id == target_user_id
    ).delete()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Share record not found.")

    db.commit()
    return {"status": "success", "message": "User access removed."}


# --- 12. REMOVE PHOTOS FROM ALBUM (UNLINK) ---
@router.post("/{album_id}/remove-photos")
def remove_photos(album_id: int, request: RemovePhotosRequest, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Unlinks photos from an album without deleting the physical files from the server."""
    album = db.query(Album).filter(Album.id == album_id, Album.owner_id == user.id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album not found or you don't own it.")

    deleted_count = db.query(AlbumPhoto).filter(
        AlbumPhoto.album_id == album_id,
        AlbumPhoto.photo_id.in_(request.photo_ids)
    ).delete(synchronize_session=False)

    db.commit()
    return {"status": "success", "message": f"Removed {deleted_count} photos from album."}