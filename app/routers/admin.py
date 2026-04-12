from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import SessionLocal
from app.deps import get_current_user, get_db
from app.models import User
from app.security import verify_password
from app.templates_engine import templates
from app.admin_auth import require_admin

from app.bootstrap import is_bootstrap_allowed
from app.security import hash_password
from fastapi import Form
from pydantic import BaseModel

import os
from app.system_settings import set_setting

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def active_admin_count(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.is_admin == True, User.status == "ACTIVE")
        .count()
    )


class AdminPasswordReset(BaseModel):
    new_password: str

# ---------- LOGIN ----------

@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request, db: Session = Depends(get_db)):
    if is_bootstrap_allowed(db):
        return RedirectResponse("/admin/bootstrap", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


@router.post("/login")
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()

    if (
        not user
        or not user.is_admin
        or not verify_password(password, user.password_hash)
    ):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid admin credentials"},
        )

    request.session["admin_user_id"] = user.id
    return RedirectResponse("/admin/users", status_code=303)


@router.get("/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


# ---------- PROTECTED ADMIN ----------

@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "users.html",
        {"request": request, "users": users},
    )


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.status = "ACTIVE"
    user.approved_at = datetime.utcnow()
    db.commit()

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/block")
def block_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Prevent blocking admin if it is the last active admin
    if user.is_admin:
        if active_admin_count(db) <= 1:
            raise HTTPException(
                status_code=400,
                detail="At least one active admin must exist",
            )

    user.status = "BLOCKED"
    db.commit()

    return RedirectResponse("/admin/users", status_code=303)


@router.get("/bootstrap", response_class=HTMLResponse)
def bootstrap_page(request: Request, db: Session = Depends(get_db)):
    if not is_bootstrap_allowed(db):
        return RedirectResponse("/admin/login", status_code=303)

    return templates.TemplateResponse(
        "bootstrap.html",
        {"request": request, "error": None},
    )


@router.post("/bootstrap")
def bootstrap_create_admin(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    storage_path: str = Form(...),
    db: Session = Depends(get_db),
):
    if not is_bootstrap_allowed(db):
        raise HTTPException(status_code=403, detail="Bootstrap already completed")

    storage_path = os.path.abspath(storage_path)

    # Validate path exists
    if not os.path.isdir(storage_path):
        return templates.TemplateResponse(
            "bootstrap.html",
            {
                "request": request,
                "error": "Storage path does not exist",
            },
        )

    # Validate writable
    try:
        test_file = os.path.join(storage_path, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
    except Exception:
        return templates.TemplateResponse(
            "bootstrap.html",
            {
                "request": request,
                "error": "Storage path is not writable by server",
            },
        )

    admin = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        status="ACTIVE",
        is_admin=True,
    )

    db.add(admin)

    # Save storage root
    set_setting(db, "STORAGE_ROOT", storage_path)

    db.commit()

    request.session["admin_user_id"] = admin.id
    return RedirectResponse("/admin/users", status_code=303)


@router.get("")
def admin_root(request: Request, db: Session = Depends(get_db)):
    # If no users exist, go to bootstrap
    from app.bootstrap import is_bootstrap_allowed

    if is_bootstrap_allowed(db):
        return RedirectResponse("/admin/bootstrap", status_code=303)

    # If already logged in, go to users
    if request.session.get("admin_user_id"):
        return RedirectResponse("/admin/users", status_code=303)

    # Otherwise, login
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/users/create", response_class=HTMLResponse)
def create_user_page(
    request: Request,
    admin: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        "create_user.html",
        {"request": request, "error": None},
    )


@router.post("/users/create")
def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    status: str = Form("PENDING"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            "create_user.html",
            {"request": request, "error": "Username already exists"},
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        status=status,
        is_admin=is_admin,
    )

    db.add(user)
    db.commit()

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    request: AdminPasswordReset,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.password_hash = hash_password(request.new_password)
    db.commit()
    return {"status": "success", "message": f"Password for {target_user.username} has been reset."}


@router.post("/users/{user_id}/force-logout")
def force_logout_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Increment the version to instantly invalidate old tokens
    target_user.session_version += 1
    db.commit()
    return {"status": "success", "message": f"{target_user.username} has been logged out of all devices."}