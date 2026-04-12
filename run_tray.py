import sys
import os

log_file = open("photosync_server.log", "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file
os.makedirs("data", exist_ok=True)


import threading
import webbrowser
import uvicorn
import pystray
from PIL import Image, ImageDraw
from app.main import app  # Imports your FastAPI app

# Global reference to the server so we can stop it
server = None

def create_image():
    # Generates a simple icon (You can load a real .ico file here instead!)
    image = Image.new('RGB', (64, 64), color = (33, 150, 243))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image

def start_server():
    global server
    # Lowered log_level to warning so the text file doesn't get massive over time
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

def on_open_dashboard(icon, item):
    webbrowser.open("http://127.0.0.1:8000/admin")

def on_exit(icon, item):
    global server
    if server:
        server.should_exit = True # Gracefully shuts down FastAPI
    icon.stop()

if __name__ == "__main__":
    # 1. Start the FastAPI server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 2. Build the System Tray Menu
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", on_open_dashboard, default=True),
        pystray.MenuItem("Exit PhotoSync", on_exit)
    )

    # 3. Start the System Tray Icon (This blocks the main thread)
    icon = pystray.Icon("PhotoSync", create_image(), "PhotoSync Server", menu)
    icon.run()