# 🖱️ Mouse Jiggler

> Keep your screen awake without raising flags. Subtle, undetectable mouse movement from the system tray.

<p align="center">
  <img src="mouse_jiggler.ico" width="128" alt="Mouse Jiggler icon">
</p>

## ✨ Features

- **Runs in the system tray** — right-click for Pause, Settings, or Exit
- **Settings GUI** — configure interval (5–600s) and pixel range (1–10px)
- **Randomized movement** — 1–N pixels in a random direction each tick — no predictable pattern
- **Single-instance** — won't accidentally run twice
- **Persistent config** — settings saved to `%APPDATA%\Mouse Jiggler\config.json`

## 🔒 Why IT Won't Flag It

| Concern | How Mouse Jiggler handles it |
|---------|------------------------------|
| **Input detection** | Uses `SendInput` API at the hardware input layer — identical to a physical mouse |
| **Services** | No Windows service — runs as a normal user process |
| **Registry** | Zero registry writes — config is a plain JSON file in `%APPDATA%` |
| **Admin rights** | None needed — runs under standard user permissions |
| **Startup** | No auto-start entries — you launch it when you need it |
| **Pattern detection** | Random direction + random distance = no repeating pattern |
| **Dependencies** | Pure Python + `pystray` + `Pillow` — no sketchy DLLs or drivers |

## 🚀 Quick Start

**Requirements:** Python 3.9+ on Windows

```bash
pip install pystray Pillow
python mouse_jiggler.py
```

The icon appears in your system tray. Done.

## ⚙️ Settings

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| **Interval** | 5–600 seconds | 60s | Time between jiggles |
| **Max pixels** | 1–10 px | 3px | Maximum random offset per move |
| **Enabled** | on/off | on | Pause/resume jiggling |

Settings are saved automatically to:
```
%APPDATA%\Mouse Jiggler\config.json
```

## 📦 Build Standalone .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --noconsole --name "MouseJiggler" --add-data "mouse_jiggler.ico;." mouse_jiggler.py
```

Or just run `build.bat` — output lands in `dist\MouseJiggler.exe`.

No Python installation needed on the target machine.

## 🤖 GitHub Actions

Every push to `main` automatically builds `MouseJiggler.exe` on a Windows runner.  
Download the latest from the [Actions tab](https://github.com/jphermans/mouse-jiggler/actions).

To create a release with the `.exe` attached:
```bash
git tag v1.0.0 && git push origin v1.0.0
```

## 📁 Project Structure

```
mouse-jiggler/
├── mouse_jiggler.py          # Main application
├── mouse_jiggler.ico         # Application icon (multi-res)
├── generate_icon.py          # Icon generator script
├── requirements.txt          # Python dependencies
├── build.bat                 # One-click PyInstaller build
├── .gitignore
└── .github/workflows/
    └── build.yml             # CI: auto-build .exe on push
```

## 📄 License

MIT — use it, fork it, share it.
