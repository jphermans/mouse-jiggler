#!/usr/bin/env python3
"""
Mouse Jiggler (macOS) — keeps your screen awake with imperceptible mouse movement.
Native macOS menu bar app using rumps. No tkinter, no pystray.
"""

import ctypes
import ctypes.util
import json
import os
import random
import sys
import threading
import time
import webbrowser
from pathlib import Path

try:
    import rumps
except ImportError:
    sys.exit(
        "Missing rumps. Install with:\n"
        "  pip3 install rumps\n"
        "Then run again."
    )

# ── Constants ────────────────────────────────────────────────────────────
APP_NAME = "Mouse Jiggler"
CONFIG_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_INTERVAL = 60
DEFAULT_PIXELS = 3


# ── Configuration ────────────────────────────────────────────────────────
def load_config():
    defaults = {"interval": DEFAULT_INTERVAL, "pixels": DEFAULT_PIXELS, "enabled": True}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                defaults.update(json.load(f))
    except (json.JSONDecodeError, OSError):
        pass
    return defaults


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ── Mouse Movement (CoreGraphics via ctypes) ─────────────────────────────
_cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))


class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


_CG_EVENT_MOUSE_MOVED = 5
_CG_HID_EVENT_TAP = 0

_cg.CGEventCreate.restype = ctypes.c_void_p
_cg.CGEventCreate.argtypes = [ctypes.c_void_p]
_cg.CGEventGetLocation.restype = CGPoint
_cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
_cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
_cg.CGEventCreateMouseEvent.argtypes = [
    ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32,
]
_cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
_cg.CFRelease.argtypes = [ctypes.c_void_p]


def jiggle_mouse(pixels=DEFAULT_PIXELS):
    dx = random.choice([-1, 1]) * random.randint(1, max(1, pixels))
    dy = random.choice([-1, 1]) * random.randint(1, max(1, pixels))

    dummy = _cg.CGEventCreate(None)
    loc = _cg.CGEventGetLocation(dummy)
    _cg.CFRelease(dummy)

    pt = CGPoint(loc.x + dx, loc.y + dy)
    event = _cg.CGEventCreateMouseEvent(None, _CG_EVENT_MOUSE_MOVED, pt, 0)
    _cg.CGEventPost(_CG_HID_EVENT_TAP, event)
    _cg.CFRelease(event)


# ── Icon ─────────────────────────────────────────────────────────────────
def make_icon():
    """Generate a simple menu bar icon using PIL."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Small mouse pointer shape
    draw.polygon(
        [(3, 2), (3, 13), (7, 10), (10, 15), (13, 13), (8, 8), (12, 5)],
        fill="#4CAF50",
        outline="#2E7D32",
    )
    return img


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════════

class MouseJigglerApp(rumps.App):
    def __init__(self):
        super().__init__(
            APP_NAME,
            icon=make_icon(),
            quit_button=None,  # we handle quit ourselves
        )
        self.config = load_config()
        self.running = False
        self.paused = False
        self.thread = None

        # Build menu
        self._build_menu()

        # Start jiggling if enabled
        if self.config.get("enabled", True):
            self._start_jiggling()

    def _build_menu(self):
        """Rebuild the entire menu to reflect current state."""
        self.menu.clear()

        # Interval submenu
        interval_menu = rumps.MenuItem("Interval")
        current = self.config.get("interval", DEFAULT_INTERVAL)
        for secs in [30, 60, 120, 300, 600]:
            label = f"{secs}s" if secs < 120 else f"{secs // 60}min"
            item = rumps.MenuItem(label, callback=self._set_interval)
            item.state = 1 if secs == current else 0
            interval_menu.add(item)
        self.menu.add(interval_menu)

        # Pixel submenu
        pixel_menu = rumps.MenuItem("Pixels")
        current_px = self.config.get("pixels", DEFAULT_PIXELS)
        for px in [1, 2, 3, 5, 10]:
            item = rumps.MenuItem(f"{px}px", callback=self._set_pixels)
            item.state = 1 if px == current_px else 0
            pixel_menu.add(item)
        self.menu.add(pixel_menu)

        self.menu.add(rumps.separator)

        # Pause / Resume
        if self.paused:
            self.menu.add(rumps.MenuItem("▶ Resume", callback=self._toggle_pause))
        else:
            self.menu.add(rumps.MenuItem("⏸ Pause", callback=self._toggle_pause))

        self.menu.add(rumps.separator)

        # Config file
        self.menu.add(rumps.MenuItem("Open Config File", callback=self._open_config))
        self.menu.add(rumps.separator)

        # Quit
        self.menu.add(rumps.MenuItem("Quit", callback=self._quit))

    def _start_jiggling(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self._jiggle_loop, daemon=True)
        self.thread.start()

    def _stop_jiggling(self):
        self.running = False

    def _jiggle_loop(self):
        while self.running:
            if not self.paused:
                jiggle_mouse(self.config.get("pixels", DEFAULT_PIXELS))
            time.sleep(self.config.get("interval", DEFAULT_INTERVAL))

    # ── Menu callbacks ──────────────────────────────────────────────────
    def _toggle_pause(self, sender):
        self.paused = not self.paused
        self.title = f"{APP_NAME} (Paused)" if self.paused else APP_NAME
        self._build_menu()

    def _set_interval(self, sender):
        label = sender.title
        secs = int(label.replace("s", "").replace("min", ""))
        if "min" in label:
            secs *= 60
        self.config["interval"] = secs
        save_config(self.config)
        self._build_menu()

    def _set_pixels(self, sender):
        px = int(sender.title.replace("px", ""))
        self.config["pixels"] = px
        save_config(self.config)
        self._build_menu()

    def _open_config(self, _):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not CONFIG_FILE.exists():
            save_config(self.config)
        os.system(f"open '{CONFIG_FILE}'")

    def _quit(self, _):
        self._stop_jiggling()
        rumps.quit_application()


# ── Entry Point ──────────────────────────────────────────────────────────
def main():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    app = MouseJigglerApp()
    app.run()


if __name__ == "__main__":
    main()
