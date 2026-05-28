#!/usr/bin/env python3
"""
Mouse Jiggler — keeps your screen awake by moving the mouse imperceptibly.
Runs in the system tray. Uses OS-native mouse input — indistinguishable
from real hardware movement. No services, no registry keys, no admin rights.

Cross-platform: Windows, macOS, Linux.
"""

import json
import os
import platform
import random
import signal
import sys
import threading
import time
import traceback
from pathlib import Path

# tkinter imported lazily in SettingsWindow (macOS PyInstaller needs Tcl/Tk bundled)

# ── pystray + PIL for tray icon ──────────────────────────────────────────
try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit(
        "Missing dependencies. Install with:\n"
        "  pip install Pillow\n"
        "Then run again."
    )

# ── Platform detection ───────────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# ── Constants ────────────────────────────────────────────────────────────
APP_NAME = "Mouse Jiggler"

# Config directory: platform-appropriate location
if IS_WINDOWS:
    CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
elif IS_MACOS:
    CONFIG_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
else:  # Linux
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mouse-jiggler"

CONFIG_FILE = CONFIG_DIR / "config.json"
CRASH_LOG = CONFIG_DIR / "crash.log"

DEFAULT_INTERVAL = 60       # seconds between jiggles
DEFAULT_PIXELS = 3          # max pixels to move
MIN_INTERVAL = 5            # minimum allowed interval
MAX_INTERVAL = 600          # maximum allowed interval


def log_crash(msg: str):
    """Write crash info to a log file for debugging silent failures."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CRASH_LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
            f.write(traceback.format_exc())
            f.write("\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
#  MOUSE MOVEMENT — platform-specific low-level implementations
# ═══════════════════════════════════════════════════════════════════════════

if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes

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

    INPUT_MOUSE = 0
    MOUSEEVENTF_MOVE = 0x0001

    def jiggle_mouse(pixels: int = DEFAULT_PIXELS):
        """Windows: Win32 SendInput API — indistinguishable from hardware input."""
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

elif IS_MACOS:
    import ctypes
    import ctypes.util

    _cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))

    class CGPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    # kCGEventMouseMoved = 5, kCGHIDEventTap = 0
    _CG_EVENT_MOUSE_MOVED = 5
    _CG_HID_EVENT_TAP = 0

    _cg.CGEventCreate.restype = ctypes.c_void_p
    _cg.CGEventCreate.argtypes = [ctypes.c_void_p]
    _cg.CGEventGetLocation.restype = CGPoint
    _cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
    _cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    _cg.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,   # source (NULL = default)
        ctypes.c_uint32,   # event type
        CGPoint,           # position
        ctypes.c_uint32,   # mouse button
    ]
    _cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    _cg.CFRelease.argtypes = [ctypes.c_void_p]

    def jiggle_mouse(pixels: int = DEFAULT_PIXELS):
        """macOS: CoreGraphics CGEvent — equivalent to hardware mouse events."""
        dx = random.choice([-1, 1]) * random.randint(1, max(1, pixels))
        dy = random.choice([-1, 1]) * random.randint(1, max(1, pixels))

        # Get current mouse position via a dummy event
        dummy = _cg.CGEventCreate(None)
        loc = _cg.CGEventGetLocation(dummy)
        _cg.CFRelease(dummy)

        new_x = loc.x + dx
        new_y = loc.y + dy

        pt = CGPoint(new_x, new_y)
        event = _cg.CGEventCreateMouseEvent(None, _CG_EVENT_MOUSE_MOVED, pt, 0)
        _cg.CGEventPost(_CG_HID_EVENT_TAP, event)
        _cg.CFRelease(event)

elif IS_LINUX:
    # Linux: Xlib via ctypes — self-contained, no xdotool needed
    import ctypes
    import ctypes.util

    _xlib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11"))

    _xlib.XOpenDisplay.restype = ctypes.c_void_p
    _xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    _xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]

    _xlib.XQueryPointer.restype = ctypes.c_int
    _xlib.XQueryPointer.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_uint),
    ]

    _xlib.XWarpPointer.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
        ctypes.c_int, ctypes.c_int,
    ]
    _xlib.XFlush.argtypes = [ctypes.c_void_p]

    _xlib.XDefaultRootWindow.restype = ctypes.c_ulong
    _xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]

    def _get_display():
        """Open X display. Returns (Display*, root_window) or (None, None)."""
        try:
            disp = _xlib.XOpenDisplay(None)
            if not disp:
                return None, None
            root = _xlib.XDefaultRootWindow(disp)
            return disp, root
        except Exception:
            return None, None

    def jiggle_mouse(pixels: int = DEFAULT_PIXELS):
        """Linux: Xlib XQueryPointer + XWarpPointer — self-contained, no xdotool."""
        dx = random.choice([-1, 1]) * random.randint(1, max(1, pixels))
        dy = random.choice([-1, 1]) * random.randint(1, max(1, pixels))

        disp, root = _get_display()
        if not disp:
            return

        try:
            rx = ctypes.c_int()
            ry = ctypes.c_int()
            wx = ctypes.c_int()
            wy = ctypes.c_int()
            mask = ctypes.c_uint()

            _xlib.XQueryPointer(
                disp, root,
                ctypes.byref(ctypes.c_void_p()), ctypes.byref(ctypes.c_void_p()),
                ctypes.byref(rx), ctypes.byref(ry),
                ctypes.byref(wx), ctypes.byref(wy),
                ctypes.byref(mask),
            )

            _xlib.XWarpPointer(disp, 0, root, 0, 0, 0, 0, rx.value + dx, ry.value + dy)
            _xlib.XFlush(disp)
        finally:
            _xlib.XCloseDisplay(disp)


# ═══════════════════════════════════════════════════════════════════════════
#  SINGLE INSTANCE — prevents multiple copies from running
# ═══════════════════════════════════════════════════════════════════════════

def acquire_single_instance() -> bool:
    """Return True if this is the only running instance, False otherwise."""
    if IS_WINDOWS:
        import ctypes
        import ctypes.wintypes

        mutex_name = f"Global\\{APP_NAME.replace(' ', '')}SingleInstance"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(
                0,
                f"{APP_NAME} is already running.\nCheck your system tray.",
                APP_NAME,
                0x40,
            )
            return False
        return True

    # macOS / Linux: PID-based lock file
    lock_file = CONFIG_DIR / ".lock"

    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if lock_file.exists():
        try:
            old_pid = int(lock_file.read_text().strip())
            # Check if the old process is still alive
            os.kill(old_pid, 0)
            # Process exists — already running
            print(f"{APP_NAME} is already running (PID {old_pid}).", file=sys.stderr)
            return False
        except (ValueError, OSError, ProcessLookupError):
            # Stale lock file or dead process — safe to overwrite
            pass

    lock_file.write_text(str(os.getpid()))
    # Clean up lock file on exit
    import atexit
    atexit.register(lambda: lock_file.unlink(missing_ok=True))
    return True


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
            defaults.update(data)
    except (json.JSONDecodeError, OSError):
        pass
    return defaults


def save_config(config: dict):
    """Persist config to the platform-appropriate location."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ── Settings Window (tkinter) ────────────────────────────────────────────
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

        import tkinter as tk
        from tkinter import ttk

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Settings")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Dark theme
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
        backend_name = {
            "Windows": "Win32 SendInput",
            "Darwin": "CoreGraphics CGEvent",
            "Linux": "Xlib XWarpPointer",
        }.get(platform.system(), "platform API")

        info = ttk.Label(
            main,
            text=(
                "The mouse moves 1–N pixels in a random direction\n"
                f"at your chosen interval. Uses {backend_name} —\n"
                "indistinguishable from real hardware input."
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


# ── Icon loading ─────────────────────────────────────────────────────────
def load_icon():
    """Load the application icon. Tries .ico/.png files, falls back to generated."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent

    # Try icon files
    for name in ("mouse_jiggler.ico", "mouse_jiggler.png", "icon_preview.png"):
        path = base_dir / name
        if path.exists():
            return Image.open(path).convert("RGBA")

    # Fallback: generate a simple icon
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    points = [
        (10, 6), (10, 48), (24, 38), (35, 54),
        (46, 48), (26, 28), (42, 19),
    ]
    draw.polygon(points, fill="#4CAF50", outline="#2E7D32")
    return img


# ═══════════════════════════════════════════════════════════════════════════
#  TRAY ICON — platform-specific implementations
# ═══════════════════════════════════════════════════════════════════════════

if IS_MACOS:
    # macOS: native AppKit NSStatusBar (no pystray — avoids PyObjC conflicts)
    try:
        from AppKit import (
            NSStatusBar, NSVariableStatusItemLength,
            NSMenu, NSMenuItem, NSImage, NSTIFFCompression,
            NSApplication, NSApp,
        )
        from Foundation import NSObject
    except ImportError as e:
        log_crash(f"PyObjC import failed: {e}")
        sys.exit(
            "Missing macOS dependencies. Install with:\n"
            "  pip3 install pyobjc-framework-Cocoa\n"
            "Then run again."
        )

    class _MacOSTray(NSObject):
        """Native macOS menu bar app using NSStatusBar."""

        def initWithApp_(self, app):
            self = super().init()
            if self is None:
                return None
            self._app = app
            self.status_item = None
            return self

        def setup(self):
            bar = NSStatusBar.systemStatusBar()
            self.status_item = bar.statusItemWithLength_(NSVariableStatusItemLength)

            # Set icon
            self._update_icon()

            # Build menu
            self._rebuild_menu()

        def _pil_to_nsimage(self, pil_img):
            """Convert PIL Image to NSImage for menu bar."""
            # Resize to 18x18 (standard menu bar icon size)
            size = 18
            scaled = pil_img.resize((size, size), Image.LANCZOS)
            # Convert to grayscale template for proper dark/light mode
            gray = scaled.convert("L")
            # Convert back to RGBA for NSImage
            rgba = Image.new("RGBA", (size, size))
            rgba.putalpha(gray)
            rgba_data = rgba.tobytes()

            # Create NSImage from raw RGBA bytes
            import ctypes
            from objc import lookUpClass

            # Use NSBitmapImageRep to create image from raw bytes
            NSBitmapImageRep = lookUpClass("NSBitmapImageRep")
            rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
                None, size, size, 8, 4, True, False,
                "NSDeviceRGBColorSpace",
                size * 4, 32,
            )
            if rep is None:
                raise RuntimeError("Failed to create NSBitmapImageRep")

            # Copy pixel data
            ctypes.memmove(
                rep.bitmapData(),
                rgba_data,
                len(rgba_data),
            )

            ns_img = NSImage.alloc().initWithSize_((size, size))
            ns_img.addRepresentation_(rep)
            ns_img.setTemplate_(True)  # macOS treats as template for dark/light mode
            return ns_img

        def _update_icon(self):
            if not self.status_item:
                return
            try:
                icon_img = load_icon()
                ns_img = self._pil_to_nsimage(icon_img)
                self.status_item.button().setImage_(ns_img)
            except Exception as e:
                log_crash(f"Failed to set tray icon: {e}")

        def _rebuild_menu(self):
            if not self.status_item:
                return

            menu = NSMenu.alloc().init()
            menu.setAutoenablesItems_(False)

            paused = self._app.paused

            # Pause / Resume
            pause_title = "▶ Resume" if paused else "⏸ Pause"
            pause_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                pause_title, "togglePause:", ""
            )
            pause_item.setTarget_(self)
            menu.addItem_(pause_item)

            # Settings
            settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "⚙ Settings", "openSettings:", ""
            )
            settings_item.setTarget_(self)
            menu.addItem_(settings_item)

            # Separator
            menu.addItem_(NSMenuItem.separatorItem())

            # Quit
            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "✕ Quit", "quitApp:", "q"
            )
            quit_item.setTarget_(self)
            menu.addItem_(quit_item)

            self.status_item.setMenu_(menu)

        def togglePause_(self, sender):
            self._app._toggle_pause()
            self._rebuild_menu()

        def openSettings_(self, sender):
            self._app._open_settings()

        def quitApp_(self, sender):
            self._app.running = False
            NSApp().terminate_(None)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN APP CLASS
# ═══════════════════════════════════════════════════════════════════════════

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

        if IS_MACOS:
            self._start_macos_tray()
        else:
            self._start_pystray_tray()

    def _jiggle_loop(self):
        """Main loop — jiggle at the configured interval."""
        while self.running:
            if not self.paused:
                jiggle_mouse(self.config.get("pixels", DEFAULT_PIXELS))
            time.sleep(self.config.get("interval", DEFAULT_INTERVAL))

    # ── macOS native tray ──────────────────────────────────────────────
    def _start_macos_tray(self):
        """Start native macOS menu bar app via NSStatusBar."""
        try:
            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(0)  # NSApplicationActivationPolicyRegular

            self._macos_tray = _MacOSTray.alloc().initWithApp_(self)
            self._macos_tray.setup()

            app.run()
        except Exception:
            log_crash("Failed to start macOS tray")

    # ── Windows / Linux pystray tray ───────────────────────────────────
    def _start_pystray_tray(self):
        """Start tray icon via pystray (Windows/Linux)."""
        import pystray

        icon_img = load_icon()
        menu = self._build_pystray_menu()
        self.tray_icon = pystray.Icon(APP_NAME, icon_img, APP_NAME, menu)
        try:
            self.tray_icon.run()
        except Exception:
            log_crash("pystray run failed")

    def _build_pystray_menu(self):
        import pystray

        paused = self.paused or not self.config.get("enabled", True)
        return pystray.Menu(
            pystray.MenuItem(
                "▶ Resume" if paused else "⏸ Pause",
                self._on_pystray_toggle,
                default=True,
            ),
            pystray.MenuItem("⚙ Settings", self._on_pystray_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ Exit", self._on_pystray_exit),
        )

    def _on_pystray_toggle(self, icon, item):
        self._toggle_pause()
        icon.menu = self._build_pystray_menu()

    def _on_pystray_settings(self, icon=None, item=None):
        self._open_settings()

    def _on_pystray_exit(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()

    def _toggle_pause(self):
        self.paused = not self.paused

    def _open_settings(self, icon=None, item=None):
        """Open the settings window."""
        try:
            self.settings_win.open()
        except ImportError:
            import tkinter.messagebox as mb
            mb.showerror(
                "Settings Unavailable",
                "The settings window requires tkinter.\n\n"
                "You can still Pause/Resume and Exit from the tray menu.\n"
                "To change settings, edit the config file directly:\n"
                f"{CONFIG_FILE}"
            )
        except Exception as e:
            log_crash(f"Settings error: {e}")

    def _on_config_changed(self, config):
        """Called when settings are saved."""
        self.config = config
        if not config.get("enabled", True):
            self.paused = True


# ── Entry point ──────────────────────────────────────────────────────────
def main():
    try:
        if not acquire_single_instance():
            sys.exit(0)

        app = MouseJiggler()
        app.start()
    except Exception:
        log_crash("Fatal startup error")
        if IS_MACOS:
            # Show error dialog on macOS since there's no terminal
            try:
                import subprocess
                subprocess.run([
                    "osascript", "-e",
                    f'display dialog "Mouse Jiggler crashed on startup.\\n\\n'
                    f'Crash log: {CRASH_LOG}\\n\\n'
                    f'Error: {traceback.format_exc()}\\n\\n'
                    'Check the crash log for details." '
                    'buttons {"OK"} default button "OK" with icon stop'
                ], timeout=10)
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
