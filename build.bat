@echo off
REM ============================================================
REM Build Mouse Jiggler into a single .exe with PyInstaller
REM Run this from the project directory
REM ============================================================

echo Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo Building Mouse Jiggler.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --noconsole ^
    --name "MouseJiggler" ^
    --add-data "mouse_jiggler.ico;." ^
    --clean ^
    mouse_jiggler.py

echo.
echo Done! Executable is in dist\MouseJiggler.exe
echo.
pause
