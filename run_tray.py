import sys
import os
import json
import threading
import webbrowser
import time
import tkinter as tk
from tkinter import simpledialog, messagebox

# ---- 1. CHECK BOOT STATE FIRST ----
IS_BACKGROUND = "--background" in sys.argv

# ---- 2. LOCATE THE INSTALLATION FOLDER ----
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(APP_DIR, "data"), exist_ok=True)

# ---- 3. REDIRECT LOGS LOCALLY ----
log_file_path = os.path.join(APP_DIR, "photosync_server.log")
log_file = open(log_file_path, "w", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

# ---- 4. SAFE CONFIGURATION LOGIC ----
config_path = os.path.join(APP_DIR, "config.json")


def prompt_for_setup(initial_port=8000):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    # Issue 1 Fixed: ONLY ask for the Port here. No folder selection.
    user_port = simpledialog.askinteger(
        "PhotoSync Setup",
        "Enter a port number for your PhotoSync server (e.g., 8000):",
        initialvalue=initial_port,
        minvalue=1024,
        maxvalue=65535
    )
    root.destroy()
    return user_port


def load_or_init_config():
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            return config.get("port", 8000), config.get("storage_path", "")
    else:
        if IS_BACKGROUND:
            return None, None

        new_port = prompt_for_setup()
        if not new_port:
            sys.exit(0)

        # Save config with an empty storage path. User configures it in Admin UI.
        with open(config_path, "w") as f:
            json.dump({"port": new_port, "storage_path": ""}, f)
        return new_port, ""


CURRENT_PORT, STORAGE_PATH = load_or_init_config()

# ---- 5. SET ENV VAR SAFELY ----
if STORAGE_PATH and os.path.exists(STORAGE_PATH):
    os.environ["PHOTOSYNC_STORAGE"] = STORAGE_PATH

# ---- 6. IMPORT FASTAPI ----
import uvicorn
import pystray
from PIL import Image, ImageDraw
from app.main import app

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
    new_port = prompt_for_setup(initial_port=CURRENT_PORT)

    if new_port and new_port != CURRENT_PORT:
        with open(config_path, "r") as f:
            config = json.load(f)
        config["port"] = new_port
        with open(config_path, "w") as f:
            json.dump(config, f)

        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        messagebox.showinfo("Restart Required",
                            f"Port saved as {new_port}!\n\nPlease right-click the tray icon, click 'Exit', and restart PhotoSync.")
        root.destroy()


def on_exit(icon, item):
    global server
    if server:
        server.should_exit = True
    icon.stop()


# ---- 7. EXECUTION LOGIC & SAFEGUARD UI ----
if __name__ == "__main__":
    if IS_BACKGROUND:
        if CURRENT_PORT is None:
            sys.exit(0)
        else:
            start_server()
    else:
        if CURRENT_PORT is not None:
            # 1. Start the server FIRST so the web portal is alive
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()

            # Wait 1.5 seconds for FastAPI to boot before opening browsers
            time.sleep(1.5)

            # Issue 2 Fixed: Show error, then redirect to Admin Portal on close
            if STORAGE_PATH and not os.path.exists(STORAGE_PATH):
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                messagebox.showerror("Storage Drive Missing",
                                     f"PhotoSync cannot find your media drive at: {STORAGE_PATH}\n\nPlease click OK to open the Admin Portal and update your settings.")
                root.destroy()

                # Instantly launch browser to the settings page!
                webbrowser.open(f"http://127.0.0.1:{CURRENT_PORT}/admin/settings")

            menu = pystray.Menu(
                pystray.MenuItem("Open Dashboard", on_open_dashboard, default=True),
                pystray.MenuItem("Change Port...", on_change_port),
                pystray.MenuItem("Exit PhotoSync", on_exit)
            )

            icon = pystray.Icon("PhotoSync", create_image(), "PhotoSync Server", menu)
            icon.run()
        else:
            sys.exit(0)