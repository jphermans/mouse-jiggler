#!/usr/bin/env python3
"""
Mouse Jiggler — keeps your screen awake by moving the mouse imperceptibly.
Runs in the system tray. Uses SendInput API (hardware-level) — indistinguishable
from real mouse movement. No services, no registry keys, no admin rights needed.

Windows only.
"""

import ctypes
import ctypes.wintypes
import json
import os
import random
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# ── pystray + PIL for tray icon ──────────────────────────────────────────
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit(
        "Missing dependencies. Install with:\n"
        "  pip install pystray Pillow\n"
        "Then run again."
    )

# ── Constants ────────────────────────────────────────────────────────────
APP_NAME = "Mouse Jiggler"
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_INTERVAL = 60       # seconds between jiggles
DEFAULT_PIXELS = 3          # max pixels to move
MIN_INTERVAL = 5            # minimum allowed interval
MAX_INTERVAL = 600          # maximum allowed interval

# ── SendInput structures (low-level Win32 API) ───────────────────────────
# Uses ctypes — no pywin32 dependency. SendInput injects at the same level
# as a physical mouse driver, so it's indistinguishable from real input.

PUL = ctypes.POINTER(ctypes.c_ulong)

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput)]

class Input(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", InputUnion),
    ]

# Flags
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001

def jiggle_mouse(pixels: int = DEFAULT_PIXELS):
    """Move the mouse by a random 1..pixels offset in a random direction."""
    dx = random.choice([-1, 1]) * random.randint(1, max(1, pixels))
    dy = random.choice([-1, 1]) * random.randint(1, max(1, pixels))

    inp = Input()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = dx
    inp.union.mi.dy = dy
    inp.union.mi.mouseData = 0
    inp.union.mi.dwFlags = MOUSEEVENTF_MOVE
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = None

    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


# ── Configuration ────────────────────────────────────────────────────────
def load_config() -> dict:
    """Load config from JSON, or return defaults."""
    defaults = {
        "interval": DEFAULT_INTERVAL,
        "pixels": DEFAULT_PIXELS,
        "enabled": True,
    }
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            # Merge with defaults (in case config is missing keys)
            defaults.update(data)
    except (json.JSONDecodeError, OSError):
        pass
    return defaults


def save_config(config: dict):
    """Persist config to %APPDATA%."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ── Settings Window ──────────────────────────────────────────────────────
class SettingsWindow:
    def __init__(self, config: dict, on_save=None):
        self.config = config
        self.on_save = on_save
        self.root = None

    def open(self):
        if self.root is not None:
            self.root.lift()
            self.root.focus_force()
            return

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Settings")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Dark-ish theme
        self.root.configure(bg="#2b2b2b")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#2b2b2b")
        style.configure("TLabel", background="#2b2b2b", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#2b2b2b", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("TScale", background="#2b2b2b")

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)

        # ── Enable / Disable ──
        self.enabled_var = tk.BooleanVar(value=self.config.get("enabled", True))
        cb = ttk.Checkbutton(main, text="Enable jiggling", variable=self.enabled_var)
        cb.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # ── Interval ──
        ttk.Label(main, text="Interval (seconds):").grid(row=1, column=0, sticky="w")
        self.interval_var = tk.IntVar(value=self.config.get("interval", DEFAULT_INTERVAL))
        self.interval_label = ttk.Label(main, text=str(self.interval_var.get()))
        self.interval_label.grid(row=1, column=1, sticky="e", padx=(10, 0))

        scale = ttk.Scale(
            main, from_=MIN_INTERVAL, to=MAX_INTERVAL,
            variable=self.interval_var, orient="horizontal",
            command=self._on_interval_change, length=300,
        )
        scale.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        # ── Pixel range ──
        ttk.Label(main, text="Max pixels per move:").grid(row=3, column=0, sticky="w")
        self.pixels_var = tk.IntVar(value=self.config.get("pixels", DEFAULT_PIXELS))
        self.pixels_label = ttk.Label(main, text=str(self.pixels_var.get()))
        self.pixels_label.grid(row=3, column=1, sticky="e", padx=(10, 0))

        px_scale = ttk.Scale(
            main, from_=1, to=10,
            variable=self.pixels_var, orient="horizontal",
            command=self._on_pixels_change, length=300,
        )
        px_scale.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 20))

        # ── Info ──
        info = ttk.Label(
            main,
            text=(
                "The mouse moves 1–N pixels in a random direction\n"
                "at your chosen interval. Movements are injected\n"
                "via the Win32 SendInput API — indistinguishable\n"
                "from real hardware input."
            ),
            justify="left",
            foreground="#888",
            font=("Segoe UI", 9),
        )
        info.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 15))

        # ── Buttons ──
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=6, column=0, columnspan=2, sticky="e")
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=self._on_close).pack(side="left")

        # Center on screen
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        self.root.mainloop()

    def _on_interval_change(self, val):
        v = int(float(val))
        self.interval_label.config(text=str(v))

    def _on_pixels_change(self, val):
        v = int(float(val))
        self.pixels_label.config(text=str(v))

    def _save(self):
        self.config["interval"] = self.interval_var.get()
        self.config["pixels"] = self.pixels_var.get()
        self.config["enabled"] = self.enabled_var.get()
        save_config(self.config)
        if self.on_save:
            self.on_save(self.config)
        self._on_close()

    def _on_close(self):
        if self.root:
            self.root.destroy()
            self.root = None


# ── Tray Icon ────────────────────────────────────────────────────────────
def load_icon():
    """Load the application icon. Tries the .ico file, falls back to a generated one."""
    # When running from source, icon is next to the script
    # When running from PyInstaller .exe, it's in the MEIPASS temp dir
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent

    ico_path = base_dir / "mouse_jiggler.ico"
    if ico_path.exists():
        return Image.open(ico_path)

    # Fallback: generate a simple icon
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    points = [
        (10, 6), (10, 48), (24, 38), (35, 54),
        (46, 48), (26, 28), (42, 19),
    ]
    draw.polygon(points, fill="#4CAF50", outline="#2E7D32")
    return img


class MouseJiggler:
    def __init__(self):
        self.config = load_config()
        self.running = False
        self.paused = False
        self.thread = None
        self.tray_icon = None
        self.settings_win = SettingsWindow(
            self.config, on_save=self._on_config_changed
        )

    def start(self):
        """Start the jiggle thread and tray icon."""
        if self.config.get("enabled", True):
            self.running = True
            self.paused = False
            self.thread = threading.Thread(target=self._jiggle_loop, daemon=True)
            self.thread.start()

        self._create_tray()

    def _jiggle_loop(self):
        """Main loop — jiggle at the configured interval."""
        while self.running:
            if not self.paused:
                jiggle_mouse(self.config.get("pixels", DEFAULT_PIXELS))
            time.sleep(self.config.get("interval", DEFAULT_INTERVAL))

    def _create_tray(self):
        """Build and run the system tray icon."""
        icon_img = load_icon()

        paused = self.paused or not self.config.get("enabled", True)
        menu = pystray.Menu(
            pystray.MenuItem(
                "▶ Resume" if paused else "⏸ Pause",
                self._toggle_pause,
                default=True,
            ),
            pystray.MenuItem("⚙ Settings", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ Exit", self._exit),
        )

        self.tray_icon = pystray.Icon(
            APP_NAME, icon_img, APP_NAME, menu
        )
        self.tray_icon.run()

    def _toggle_pause(self, icon, item):
        if self.paused:
            self.paused = False
            self.tray_icon.title = APP_NAME
        else:
            self.paused = True
            self.tray_icon.title = f"{APP_NAME} (Paused)"

        paused = self.paused
        icon.menu = pystray.Menu(
            pystray.MenuItem(
                "▶ Resume" if paused else "⏸ Pause",
                self._toggle_pause,
                default=True,
            ),
            pystray.MenuItem("⚙ Settings", self._open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ Exit", self._exit),
        )

    def _open_settings(self, icon=None, item=None):
        """Open the settings window."""
        self.settings_win.open()

    def _on_config_changed(self, config):
        """Called when settings are saved."""
        self.config = config
        if not config.get("enabled", True):
            self.paused = True

    def _exit(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()


# ── Entry point ──────────────────────────────────────────────────────────
def main():
    import ctypes.wintypes
    mutex_name = f"Global\\{APP_NAME.replace(' ', '')}SingleInstance"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"{APP_NAME} is already running.\nCheck your system tray.",
            APP_NAME,
            0x40,
        )
        sys.exit(0)

    app = MouseJiggler()
    app.start()


if __name__ == "__main__":
    main()
