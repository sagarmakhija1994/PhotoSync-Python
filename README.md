# 📸 PhotoSync Server

> 🔐 A private, self-hosted alternative to Google Photos — built for full control, performance, and family-scale sharing.

[![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)]()
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)]()
[![License](https://img.shields.io/badge/license-Private-red.svg)]()

---

## 🔗 Ecosystem

- 📱 Android Client → https://github.com/sagarmakhija1994/PhotoSync-Android
- 🖥 Backend Server → (this repo)

---

## ✨ What is PhotoSync?

PhotoSync is a **self-hosted, multi-user photo & video sync platform** that gives you:

- Full ownership of your data
- No cloud dependency
- Fast local transfers + remote access
- Private family sharing network

---

## ⚡ Quick Start

### 🪟 Windows (Recommended)

👉 **Download & Install**
- Go to **Releases**
- Download `.exe`
- Install & Run

Then open:
http://127.0.0.1:8000/admin

---

### 🧑‍💻 Manual Setup

```bash
git clone <repo-url>
cd photosync

python3.13 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🏗 Architecture

```mermaid
flowchart LR
    A[📱 Android App] -->|Local WiFi / Remote URL| B[🌐 FastAPI Server]
    B --> C[(🗄 SQLite DB)]
    B --> D[(📁 File Storage)]
    B --> E[🖥 Web Portal UI]
```

---

### 🖼️ Screenshots

## 🛠 Admin Web Portal
<div align="center"> <img src="https://github.com/user-attachments/assets/75c0a5c6-a37f-480f-bae8-58f6f5aed591" width="420"/> <img src="https://github.com/user-attachments/assets/f79b4ed4-5678-44c8-ba99-9260c73bf359" width="420"/> <img src="https://github.com/user-attachments/assets/6d825d36-0a36-4187-90da-a482992aecb6" width="420"/> <img src="https://github.com/user-attachments/assets/03d4a2c7-26b1-472a-a5be-613135ea73d0" width="420"/> </div>

## 👤 User Web Portal
<div align="center"> <img src="https://github.com/user-attachments/assets/697917e8-9033-4281-b421-2574f519afea" width="420"/> <img src="https://github.com/user-attachments/assets/7262fffe-a408-4b75-bdd8-9dbccbcaedeb" width="420"/> <img src="https://github.com/user-attachments/assets/0c18ee5d-4262-4b3e-8b68-9724a45b76b5" width="420"/> <img src="https://github.com/user-attachments/assets/1ffa034b-0c5b-4182-9305-9e869dc12564" width="420"/> <img src="https://github.com/user-attachments/assets/8172b693-595f-41c0-87e8-33a920df690f" width="420"/> <img src="https://github.com/user-attachments/assets/a1f6aa5b-fc63-423a-ad67-c0678338358a" width="420"/> </div>
---

## 🌟 Key Features

### 📦 Storage & Sync
- Multi-user isolated storage
- SHA-256 deduplication
- Original folder structure preserved

---

### 🌐 Smart Networking
- Dual URL system (Local + Remote)
- Dynamic port routing
- Optimized media delivery

---

### 🖥 Web Portal (v1.5)
- Integrated UI (no separate frontend)
- Lightbox viewer
- Smooth loading
- Ultrawide support

---

### 🪟 Windows App
- One-click installer
- Bundled FFmpeg + UI
- No setup required

---

### ⚙️ System Tray
- Open Web Portal
- Change port
- Auto restart

---

### 🔐 Security
- JWT authentication
- Session invalidation
- bcrypt / argon2

---

### 👨‍👩‍👧 Social Features
- Follow system
- Album sharing
- One-tap import

---

### 🛠 Advanced
- `/server-info` API
- Git LFS
- High-load stability

---

## 📁 Project Structure

```
photosync/
├─ app/
├─ dist/
├─ bin/
├─ requirements.txt
└─ README.md
```

---

## 🔧 Admin Setup

Open:
http://127.0.0.1:8000/admin

---

## 📡 Health Check

```bash
curl http://127.0.0.1:8000/health
```

---

## 👨‍💻 Author

Sagar Makhija

---

## 📜 License

Private / Internal Use
