# PhotoSync – Self-Hosted Multi-User Photo Sync Server

PhotoSync is a **self-hosted, secure, multi-user photo synchronization system** designed to sync photos and videos from Android devices to a personal home server.

It is built to be:
- Internet-accessible (via Cloudflare Tunnel)
- Secure by default (manual user approval, JWT, device binding)
- Efficient for large photo libraries (hash-based deduplication)
- Simple to restore and redeploy

This repository contains **only the backend + admin UI**.
Android client lives in a separate repository.

---

## Features

- ✅ Multi-user support
- ✅ Manual user approval (pending → active)
- ✅ Multi-device per user
- ✅ Device-based security (revoke individual devices)
- ✅ Hash-based deduplication (no re-upload after reset)
- ✅ Safe filesystem layout (user-based storage)
- ✅ Cloudflare Tunnel compatible
- ✅ No cloud dependency

---

## Architecture Overview

Android App(s)\
│\
│ HTTPS (JWT Auth)\
▼\
FastAPI Backend (this repo)\
│\
├─ SQLite DB (users, devices, metadata)\
├─ File storage (photos/videos)\
└─ Admin Web UI\


Storage is **user-based**, not device-based:

/data/photos/users/<username>/DCIM/Camera/IMG_0001.jpg


---

## Tech Stack

| Component | Technology |
|--------|-----------|
| Backend | Python 3.11 |
| API | FastAPI |
| Auth | JWT (access tokens) |
| DB | SQLite |
| ORM | SQLAlchemy |
| Passwords | bcrypt |
| Reverse Proxy | Cloudflare Tunnel |
| Admin UI | Server-rendered HTML |

---

## Project Structure

photosync/\
├─ app/\
│ ├─ main.py\
│ ├─ database.py\
│ ├─ models.py\
│ ├─ security.py\
│ ├─ routers/\
│ │ ├─ auth.py\
│ │ ├─ admin.py\
│ │ └─ health.py\
│ └─ services/\
├─ data/\
│ ├─ meta.db # SQLite database\
│ └─ photos/ # User photo storage\
├─ requirements.txt\
└─ README.md\

---

## Installation (Fresh Server)

### 1. Clone repository

```bash
git clone <private-repo-url>
cd photosync
```

### 2. Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Server will be available at:
``bash
http://127.0.0.1:8000
``

### 5. Verify health
```bash
GET /health
```

Response:
``bash
{ "status": "ok" }
``