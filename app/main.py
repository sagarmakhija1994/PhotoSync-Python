import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine
from app.models import Base
from app.routers import auth, admin, health, sync
from app.routers import photos
from app.routers import devices
from app.routers import albums
from app.routers import network
from app.routers import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PhotoSync Server",
    version="0.1.0",
)

# Updated CORS to allow any local network IP to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ CHANGE THIS SECRET
app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_ME_ADMIN_SESSION_SECRET",
    https_only=False,  # set True when behind HTTPS
)

# --- Include all your API routers ---
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(photos.router)
app.include_router(devices.router)
app.include_router(sync.router)
app.include_router(albums.router)
app.include_router(network.router)
app.include_router(settings.router)


@app.get("/server-info")
def get_server_info():
    # You can update this string whenever you release a new version!
    return {
        "name": "PhotoSync Server",
        "version": "1.5.0"
    }

if os.path.isdir("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

@app.get("/{catchall:path}")
def serve_react_app(catchall: str):
    # If the browser is asking for a specific file (like logo.png or favicon.ico), serve it
    file_path = os.path.join("dist", catchall)
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    # Otherwise, give them the React index.html (React Router will handle the rest internally)
    index_path = os.path.join("dist", "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return {"error": "Web UI not built. Please run 'npm run build' and move the dist folder here."}