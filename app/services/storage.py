# app/services/storage.py

import os
import hashlib
from sqlalchemy.orm import Session
from app.system_settings import get_setting


CHUNK_SIZE = 1024 * 1024  # 1MB


def safe_join(base: str, *paths: str) -> str:
    final_path = os.path.abspath(os.path.join(base, *paths))
    if not final_path.startswith(os.path.abspath(base)):
        raise ValueError("Invalid path traversal detected")
    return final_path


def compute_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()
