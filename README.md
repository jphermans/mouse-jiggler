# 🖱️ Mouse Jiggler

> Keep your screen awake without raising flags. Subtle, undetectable mouse movement from the system tray.
> **Cross-platform** — Windows, macOS (Apple Silicon), and Linux.

<p align="center">
  <img src="icon_preview.png" width="128" alt="Mouse Jiggler icon">
</p>

## ✨ Features

- **Runs in the system tray** — right-click for Pause, Settings, or Exit
- **Settings GUI** — configure interval (5–600s) and pixel range (1–10px)
- **Randomized movement** — 1–N pixels in a random direction each tick — no predictable pattern
- **Single-instance** — won't accidentally run twice
- **Persistent config** — saves to your OS-native config directory
- **Cross-platform** — native mouse input on every OS, zero extra dependencies

## 🔧 How It Moves the Mouse

| Platform | Backend | Notes |
|----------|---------|-------|
| **Windows** | Win32 `SendInput` API | Hardware-level input — identical to a physical mouse |
| **macOS** | CoreGraphics `CGEvent` | Low-level event posting via ctypes — no pyobjc needed |
| **Linux** | Xlib `XWarpPointer` | Low-level X11 via ctypes — no external tools needed |

## 🔒 Why IT Won't Flag It

| Concern | How Mouse Jiggler handles it |
|---------|------------------------------|
| **Input detection** | Uses OS-native input APIs at the hardware layer — identical to a physical mouse |
| **Services** | No services or daemons — runs as a normal user process |
| **Registry / plists** | Zero system writes — config is a plain JSON file |
| **Admin / root** | None needed — runs under standard user permissions |
| **Startup** | No auto-start entries — you launch it when you need it |
| **Pattern detection** | Random direction + random distance = no repeating pattern |
| **Dependencies** | Pure Python + `pystray` + `Pillow` — no sketchy DLLs or drivers |

## 🚀 Quick Start

**Requirements:** Python 3.9+

```bash
pip install pystray Pillow
python mouse_jiggler.py
```

The icon appears in your system tray. Done.

### macOS Note

macOS requires Accessibility permission for apps that simulate mouse input. On first run:
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button and add the app (or drag it in)
3. Toggle the switch on

You'll only need to do this once.

## ⚙️ Settings

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| **Interval** | 5–600 seconds | 60s | Time between jiggles |
| **Max pixels** | 1–10 px | 3px | Maximum random offset per move |
| **Enabled** | on/off | on | Pause/resume jiggling |

Settings are saved automatically:

| Platform | Config path |
|----------|-------------|
| Windows | `%APPDATA%\Mouse Jiggler\config.json` |
| macOS | `~/Library/Application Support/Mouse Jiggler/config.json` |
| Linux | `~/.config/mouse-jiggler/config.json` |

## 📦 Build Standalone Binary

```bash
pip install pyinstaller
# Windows
pyinstaller --onefile --windowed --noconsole --name "MouseJiggler" --add-data "mouse_jiggler.ico;." mouse_jiggler.py
# macOS
pyinstaller --onefile --windowed --name "MouseJiggler" --add-data "mouse_jiggler.ico:." mouse_jiggler.py
```

Or run `build.bat` on Windows. Output lands in `dist/`.

No Python installation needed on the target machine.

## 🤖 GitHub Actions

Every push to `main` automatically builds on both platforms:

| Artifact | Runner | Download from |
|----------|--------|---------------|
| `MouseJiggler.exe` | `windows-latest` (x64) | [Actions tab](https://github.com/jphermans/mouse-jiggler/actions) |
| `MouseJiggler-macOS.zip` | `macos-latest` (Apple Silicon) | [Actions tab](https://github.com/jphermans/mouse-jiggler/actions) |
| `MouseJiggler` | `ubuntu-22.04` (x64, glibc 2.35+) | [Actions tab](https://github.com/jphermans/mouse-jiggler/actions) |

Compatible with Debian 12+, Ubuntu 22.04+, Fedora 36+, Arch, and any distro shipping glibc ≥ 2.35.

To create a release with both binaries attached:
```bash
git tag v1.0.0 && git push origin v1.0.0
```

## 📁 Project Structure

```
mouse-jiggler/
├── mouse_jiggler.py          # Main application (cross-platform)
├── mouse_jiggler.ico         # Application icon (multi-res)
├── generate_icon.py          # Icon generator script
├── icon_preview.png          # Icon preview for README
├── requirements.txt          # Python dependencies
├── build.bat                 # One-click PyInstaller build (Windows)
├── .gitignore
└── .github/workflows/
    └── build.yml             # CI: auto-build for Windows + macOS
```

## 📄 License

MIT — use it, fork it, share it.
