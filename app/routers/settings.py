import os
import sys
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Import your actual templates engine
from app.templates_engine import templates

# Removed the global prefix so we can serve both HTML and API from this file
router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    storage_path: str


def get_config_path():
    """Finds the config.json file dynamically based on .exe or script location"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "config.json")

    # BACK UP 3 LEVELS: settings.py -> routers/ -> app/ -> ROOT
    routers_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(routers_dir)
    root_dir = os.path.dirname(app_dir)

    return os.path.join(root_dir, "config.json")


# --- 1. THE HTML UI ROUTE ---
@router.get("/admin/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


# --- 2. THE API ROUTES ---
@router.get("/api/settings")
def get_settings():
    config_path = get_config_path()
    storage_path = ""

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            storage_path = config.get("storage_path", "")

    # Check if the folder is missing or not yet set
    is_missing = False
    if storage_path and not os.path.exists(storage_path):
        is_missing = True
    elif not storage_path:
        is_missing = True  # Treat an empty path as "missing"

    return {
        "storage_path": storage_path,
        "is_missing": is_missing
    }


@router.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    config_path = get_config_path()

    # Verify the folder actually exists on the Windows server before accepting it
    if not os.path.exists(payload.storage_path):
        raise HTTPException(status_code=400, detail="Error: That folder path does not exist on the server.")

    # Save it to config.json
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)

    config["storage_path"] = payload.storage_path
    with open(config_path, "w") as f:
        json.dump(config, f)

    # Update the environment variable instantly so FastAPI routes use it immediately
    os.environ["PHOTOSYNC_STORAGE"] = payload.storage_path

    return {"status": "success", "message": "Storage path updated successfully!"}