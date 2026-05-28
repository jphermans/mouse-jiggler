# Mouse Jiggler

Keeps your screen awake by subtly moving the mouse cursor at regular intervals. Runs quietly in the Windows system tray.

## Why this is safe

- Uses the **Win32 `SendInput` API** via `ctypes` — same low-level input path as a real physical mouse. No detectable difference from hardware input.
- **Not a Windows service** — runs as a normal user process in the tray.
- **No registry modifications**, no admin rights needed, no startup entries (you launch it manually).
- Random movement direction and distance (1–N pixels) — no predictable pattern.

## Quick Start

### Prerequisites
- Python 3.9+
- Windows

### Install & Run
```bash
pip install pystray Pillow
python mouse_jiggler.py
```

The app appears in your system tray. Right-click for Pause / Settings / Exit.

### Settings
- **Interval**: 5–600 seconds between jiggles (default: 60s)
- **Max pixels**: 1–10 pixel random offset per move (default: 3)
- **Enable/disable** toggle

Settings are saved to `%APPDATA%\Mouse Jiggler\config.json`.

### Build standalone .exe
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --noconsole --name "MouseJiggler" mouse_jiggler.py
```
Output: `dist\MouseJiggler.exe` — no Python install needed on the target machine.

## GitHub Actions

Every push to `main` builds `MouseJiggler.exe` automatically. Download the latest from the [Actions tab](https://github.com/jphermans/mouse-jiggler/actions).

## Files

| File | Purpose |
|------|---------|
| `mouse_jiggler.py` | Main application |
| `requirements.txt` | Python dependencies |
| `build.bat` | One-click PyInstaller build |
| `.github/workflows/build.yml` | CI: auto-build .exe on push |
