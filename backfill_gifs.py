import os
import sys
import json
import subprocess
from app.database import SessionLocal
from app.models import Photo, Device, User, SystemSetting


def get_ffmpeg_path():
    """Smart path resolver that finds our bundled ffmpeg.exe from the root directory"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_ffmpeg = os.path.join(base_dir, "bin", "ffmpeg.exe")

    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg
    return "ffmpeg"  # Fallback if not bundled


def build_file_path(db, username: str, device_name: str, raw_path: str) -> str:
    """Matches the exact path logic from your sync.py, including config.json!"""
    base_storage_path = os.environ.get("PHOTOSYNC_STORAGE")

    # NEW: Actually check the config.json file!
    if not base_storage_path:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                if config.get("storage_path"):
                    base_storage_path = config["storage_path"]

    # Fallback to DB
    if not base_storage_path:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "storage_path").first()
        base_storage_path = setting.value.strip() if setting and setting.value else r"C:\photosync-data"

    clean_user = username.strip()
    clean_device = device_name.strip()
    clean_raw = raw_path.strip().strip('"').strip()
    clean_relative = clean_raw.replace("/", os.sep).replace("\\", os.sep).lstrip(os.sep)

    return os.path.abspath(os.path.join(base_storage_path, "users", clean_user, clean_device, clean_relative))


def generate_video_gif(original_path: str):
    """The Highly Compressed GIF Generator"""
    dir_name = os.path.dirname(original_path)
    thumb_dir = os.path.join(dir_name, ".thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)

    gif_name = f"{os.path.basename(original_path)}.gif"
    thumb_path = os.path.join(thumb_dir, gif_name)

    ffmpeg_exe = get_ffmpeg_path()

    # The Magic Diet: 4s, 5fps, 300px scale, max 128 colors, bayer dither
    # The '-y' flag ensures it OVERWRITES the old heavy 2.6MB files without asking!
    command = [
        ffmpeg_exe, "-y",
        "-ss", "00:00:00",
        "-t", "4",
        "-i", original_path,
        "-vf",
        "fps=5,scale=300:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
        "-loop", "0",
        thumb_path
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Calculate the new size to prove the compression worked
        size_kb = os.path.getsize(thumb_path) / 1024
        return True, f"Optimized size: {size_kb:.1f} KB"
    except Exception as e:
        return False, str(e)


def run_backfill():
    print("=" * 65)
    print("🎬 STARTING VIDEO GIF DIET SCRIPT (OVERWRITING HEAVY GIFS)")
    print("=" * 65)

    db = SessionLocal()
    try:
        # Grab only the videos from the database
        videos = db.query(Photo).filter(Photo.media_type == "video").all()
        print(f"Found {len(videos)} videos in the database. Beginning compression...\n")

        success_count = 0
        fail_count = 0

        for index, video in enumerate(videos, 1):
            user = db.query(User).filter(User.id == video.user_id).first()
            device = db.query(Device).filter(Device.id == video.device_id).first()

            physical_path = build_file_path(db, user.username, device.device_name, video.relative_path)

            if not os.path.exists(physical_path):
                print(f"[{index}/{len(videos)}] ⚠️ MISSING FILE: {os.path.basename(physical_path)}")
                print(f"    -> Looked in: {physical_path}")  # <--- ADD THIS LINE
                fail_count += 1
                continue

            success, msg = generate_video_gif(physical_path)

            if success:
                success_count += 1
                print(f"[{index}/{len(videos)}] ✅ {os.path.basename(physical_path)} -> {msg}")
            else:
                fail_count += 1
                print(f"[{index}/{len(videos)}] ❌ FAILED: {os.path.basename(physical_path)} ({msg})")

        print("\n" + "=" * 65)
        print("🎉 GIF COMPRESSION COMPLETE")
        print(f"Successfully Optimized: {success_count} | Failed: {fail_count}")
        print("Your Android app will now scroll perfectly!")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    run_backfill()