# 📸 PhotoSync – Self-Hosted Multi-User Photo Sync Server

PhotoSync is a **self-hosted, secure, multi-user photo synchronization system** designed to sync photos and videos from Android devices to a personal home server.

It acts as a private alternative to cloud platforms like Google Photos, with full control over your data.

> ⚠️ This repository contains **only the backend + admin UI**.  
> The Android client is maintained in a separate repository.

---

## 🌟 Features

### 📦 Core Backup & Storage
- ✅ **Multi-User Support**  
  Isolated storage environments for each user.

- ✅ **Hash-Based Deduplication**  
  Uses SHA-256 hashing to prevent duplicate uploads—even after deletion/restoration.

- ✅ **Safe Filesystem Layout**  
  Files are stored under:
  ```
  /users/<username>/...
  ```
  preserving original device folder structure.

---

### 🌐 Networking & Syncing
- ✅ **Smart Dual-URL System**  
  Automatically switches between:
  - Local WiFi IP (fast transfer)
  - Cloudflare Tunnel (remote access)

- ✅ **Background Sync Engine**  
  Uses Android `WorkManager` for scheduled and constraint-based syncing.

---

### 👨‍👩‍👧 Private Social Network
- ✅ **Two-Way Follow System**  
  Send, accept, and manage connection requests.

- ✅ **Album Management**
  - Create / Rename albums
  - Organize photos efficiently

- ✅ **Granular Sharing**
  Share albums with selected users only.

- ✅ **One-Tap Import**
  Clone shared albums or photos into personal storage.

---

### 🔐 Security & Admin Dashboard
- ✅ **Server-Rendered Admin UI** (Jinja2)
- ✅ **Bootstrap Mode** (Initial setup lock)
- ✅ **Manual User Approval**
- ✅ **Admin Password Reset**
- ✅ **JWT Session Versioning**
- ✅ **"Logoff All" Kill Switch**

---

## 🏗 Architecture Overview

```
       [ Android App(s) ]
               │
    (Smart Dual-URL Routing)
    Local WiFi OR Cloudflare Tunnel
               │
      HTTPS (JWT Auth Bearer)
               ▼
    [ FastAPI Backend ]
               │
   ┌───────────┼───────────┐
   │           │           │
[SQLite DB] [File Storage] [Admin Web UI]
 (Metadata)  (Photos/Vids) (HTML/Jinja2)
```

📁 Example Storage Path:
```
/your/storage/path/users/<username>/DCIM/Camera/IMG_0001.jpg
```

---

## 🛠 Tech Stack

| Component        | Technology                |
|----------------|--------------------------|
| Backend         | Python 3.11              |
| API Framework   | FastAPI                  |
| Authentication  | JWT (Session Versioning) |
| Database        | SQLite                   |
| ORM             | SQLAlchemy               |
| Cryptography    | bcrypt                   |
| Reverse Proxy   | Cloudflare Tunnel        |
| Admin UI        | Jinja2 Templates         |

---

## 📁 Project Structure

```
photosync/
├─ app/
│  ├─ main.py
│  ├─ database.py
│  ├─ models.py
│  ├─ security.py
│  ├─ deps.py
│  ├─ system_settings.py
│  ├─ bootstrap.py
│  ├─ routers/
│  │  ├─ auth.py
│  │  ├─ admin.py
│  │  ├─ sync.py
│  │  ├─ albums.py
│  │  ├─ network.py
│  │  └─ health.py
│  └─ templates/
├─ requirements.txt
└─ README.md
```

---

## 🚀 Installation (Fresh Server)

### 1️⃣ Clone Repository
```bash
git clone <private-repo-url>
cd photosync
```

### 2️⃣ Create Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> Use `--reload` for development mode.

---

## ⚙️ Bootstrap Setup (CRITICAL)

On first run, the system is locked until setup is complete.

### Steps:
1. Open browser:
   ```
   http://127.0.0.1:8000/admin
   ```

2. You will be redirected to Bootstrap Page.

3. Configure:
   - Admin credentials
   - Storage root path (example):
     ```
     D:\Data\PhotoSync
     /mnt/storage/photosync
     ```

4. Save → Server becomes active.

---

## 🧪 Health Check

```bash
curl http://127.0.0.1:8000/health
```

### Response:
```json
{
  "status": "ok"
}
```

---

## 🎯 Release Status

✅ **Release 1.0 Complete**

You can now:
- Build the Android APK
- Connect devices
- Run your own private cloud photo system

---

## 📌 Notes

- Designed for **self-hosting + privacy-first usage**
- Optimized for **family-scale deployments**
- Works best with **Cloudflare Tunnel for remote access**

---

## 🧠 Future Scope (Optional Ideas)

- Web gallery UI for users
- AI-based image tagging
- Video transcoding
- Incremental sync optimizations

---

## 👨‍💻 Author

**Sagar Makhija**

---

## 📜 License

Private / Internal Use (Update as needed)
