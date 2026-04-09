# app/main.py

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.database import engine
from app.models import Base
from app.routers import auth, admin, health, sync
from app.routers import photos
from app.routers import devices


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PhotoSync Server",
    version="0.1.0",
)

# ⚠️ CHANGE THIS SECRET
app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_ME_ADMIN_SESSION_SECRET",
    https_only=False,   # set True when behind HTTPS
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(photos.router)
app.include_router(devices.router)
app.include_router(sync.router)

@app.get("/")
def read_root():
    return {"message": "PhotoSync Server is running"}