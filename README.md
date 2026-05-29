# 🖱️ Mouse Jiggler

> Keep your screen awake without raising flags. Subtle, undetectable mouse movement from the system tray.
> **Cross-platform** — Windows, macOS (Apple Silicon), and Linux.

<p align="center">
  <img src="icon_preview.png" width="128" alt="Mouse Jiggler icon">
</p>

## ✨ Features

- **Runs in the system tray / menu bar** — click for Pause, Settings, or Quit
- **Randomized movement** — 1–N pixels in a random direction each tick — no predictable pattern
- **Single-instance** — won't accidentally run twice
- **Persistent config** — saves to your OS-native config directory
- **Platform-native UI** — pystray on Windows/Linux, rumps on macOS

## 🔧 How It Moves the Mouse

| Platform | UI Framework | Mouse Backend |
|----------|-------------|----------------|
| **Windows** | pystray + tkinter | Win32 `SendInput` API |
| **macOS** | ObjC (native Cocoa) | CoreGraphics `CGEvent` |
| **Linux** | pystray + tkinter | Xlib `XWarpPointer` via ctypes |

## 🚀 Quick Start

### Windows / Linux

**Requirements:** Python 3.9+

```bash
pip install pystray Pillow
python mouse_jiggler.py
```

### macOS

**Requirements:** macOS 11+ (Big Sur or later)

Download the latest `MouseJiggler-macOS.zip` from [GitHub Actions](https://github.com/jphermans/mouse-jiggler/actions).

Unzip, then right-click → **Open** the first time (unsigned developer).

> **Note:** To control the mouse, enable **Mouse Jiggler** in **System Settings → Privacy & Security → Accessibility**.

To build from source:
```bash
pip3 install Pillow
python3 generate_macos_icon.py AppIcon.icns
clang -O2 -framework Cocoa -framework CoreGraphics -framework ServiceManagement \
  -o MouseJiggler mouse_jiggler_macos.m
```

## ⚙️ Settings

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| **Interval** | 30s–10min | 60s | Time between jiggles |
| **Max pixels** | 1–10 px | 3px | Maximum random offset per move |

**Windows / Linux:** Settings open via tray menu → "⚙ Settings" (tkinter GUI).
**macOS:** Settings changed via menu bar presets (Interval/Pixels submenus) or edit `config.json` directly ("Open Config File").

| Platform | Config path |
|----------|-------------|
| Windows | `%APPDATA%\Mouse Jiggler\config.json` |
| macOS | `~/Library/Application Support/Mouse Jiggler/config.json` |
| Linux | `~/.config/mouse-jiggler/config.json` |

## 📦 Build Standalone Binary

### Windows
```bash
pip install pyinstaller pystray Pillow
pyinstaller --onefile --windowed --noconsole --name "MouseJiggler" --add-data "mouse_jiggler.ico;." mouse_jiggler.py
```

### macOS
```bash
swiftc -O -o MouseJiggler mouse_jiggler_macos.swift
# Output: MouseJiggler (Mach-O executable)
```

### Linux
```bash
pip install pyinstaller pystray Pillow
sudo apt install python3-tk  # for settings GUI
pyinstaller --onefile --windowed --name "MouseJiggler" --add-data "mouse_jiggler.ico:." mouse_jiggler.py
```

## 🤖 GitHub Actions

Every push to `main` automatically builds for all three platforms:

| Artifact | Runner | Source File |
|----------|--------|-------------|
| `MouseJiggler.exe` | `windows-latest` (x64) | `mouse_jiggler.py` |
| `MouseJiggler-macOS.zip` | `macos-latest` (Apple Silicon) | ObjC (native) |
| `MouseJiggler` | `ubuntu-22.04` (x64) | `mouse_jiggler.py` |

Download the latest from the [Actions tab](https://github.com/jphermans/mouse-jiggler/actions).

To create a release with all binaries:
```bash
git tag v1.0.0 && git push origin v1.0.0
```

## 📁 Project Structure

```
mouse-jiggler/
├── mouse_jiggler.py           # Windows + Linux (pystray)
├── mouse_jiggler_macos.m      # macOS (ObjC — native Cocoa)
├── generate_macos_icon.py     # macOS app icon generator
├── mouse_jiggler.ico          # Application icon (multi-res)
├── generate_icon.py          # Icon generator script
├── icon_preview.png          # Icon preview for README
├── requirements.txt          # Windows/Linux dependencies
├── build.bat                 # One-click PyInstaller build (Windows)
├── .gitignore
└── .github/workflows/
    └── build.yml             # CI: auto-build for Windows + macOS + Linux
```

## 📄 License

MIT — use it, fork it, share it.
