import sys
import os
import json
import threading
import webbrowser
import tkinter as tk
from tkinter import simpledialog, messagebox

# ---- 1. CHECK BOOT STATE FIRST ----
# We need to know immediately if we are in the invisible Session 0
IS_BACKGROUND = "--background" in sys.argv

# ---- 2. CREATE FOLDERS BEFORE ANYTHING ELSE ----
os.makedirs("data", exist_ok=True)
app_data_path = os.path.join(os.getenv('APPDATA'), 'PhotoSync')
os.makedirs(app_data_path, exist_ok=True)
os.makedirs(os.path.join(app_data_path, "data"), exist_ok=True)

# ---- 3. REDIRECT LOGS ----
log_file_path = os.path.join(app_data_path, "photosync_server.log")
log_file = open(log_file_path, "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# ---- 4. NOW WE IMPORT FASTAPI ----
import uvicorn
import pystray
from PIL import Image, ImageDraw
from app.main import app

# ---- 5. SAFE CONFIGURATION LOGIC ----
config_path = os.path.join(app_data_path, "config.json")


def prompt_for_port(initial_port=8000, title="PhotoSync Setup"):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    user_port = simpledialog.askinteger(
        title,
        "Enter a port number for your PhotoSync server (e.g., 8000, 8080):",
        initialvalue=initial_port,
        minvalue=1024,
        maxvalue=65535
    )
    root.destroy()
    return user_port if user_port else initial_port


def load_or_init_config():
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            return config.get("port", 8000)
    else:
        # CRITICAL SAFEGUARD:
        # If config doesn't exist and we are in Session 0, DO NOT open the popup.
        if IS_BACKGROUND:
            return None

            # Otherwise, the user clicked it normally. Ask them for the port!
        new_port = prompt_for_port()
        with open(config_path, "w") as f:
            json.dump({"port": new_port}, f)
        return new_port


# Load the port (Will be None if background boot + no config)
CURRENT_PORT = load_or_init_config()

server = None


def create_image():
    image = Image.new('RGB', (64, 64), color=(33, 150, 243))
    dc = ImageDraw.Draw(image)
    dc.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
    return image


def start_server():
    global server
    config = uvicorn.Config(app, host="0.0.0.0", port=CURRENT_PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def on_open_dashboard(icon, item):
    webbrowser.open(f"http://127.0.0.1:{CURRENT_PORT}/admin")


def on_change_port(icon, item):
    global CURRENT_PORT
    new_port = prompt_for_port(initial_port=CURRENT_PORT, title="Change PhotoSync Port")

    if new_port != CURRENT_PORT:
        with open(config_path, "w") as f:
            json.dump({"port": new_port}, f)

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo("Restart Required",
                            f"Port saved as {new_port}!\n\nPlease right-click the tray icon, click 'Exit', and restart PhotoSync to apply changes.")
        root.destroy()


def on_exit(icon, item):
    global server
    if server:
        server.should_exit = True
    icon.stop()


# ---- 6. EXECUTION LOGIC ----
if __name__ == "__main__":
    if IS_BACKGROUND:
        if CURRENT_PORT is None:
            # We are on the lock screen, but the user hasn't set a port yet.
            # Exit silently. The app will run normally when they launch from Start Menu.
            sys.exit(0)
        else:
            # We have a port, and we are in the background. Run server without UI!
            start_server()
    else:
        # User launched app manually. Give them the full tray UI.
        if CURRENT_PORT is not None:
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()

            menu = pystray.Menu(
                pystray.MenuItem("Open Dashboard", on_open_dashboard, default=True),
                pystray.MenuItem("Change Port...", on_change_port),
                pystray.MenuItem("Exit PhotoSync", on_exit)
            )

            icon = pystray.Icon("PhotoSync", create_image(), "PhotoSync Server", menu)
            icon.run()
        else:
            # Failsafe in case they hit cancel on the port popup
            sys.exit(0)