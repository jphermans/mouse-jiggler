"""
py2app setup script for Mouse Jiggler macOS
"""
from setuptools import setup

APP = ['mouse_jiggler_macos.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'LSUIElement': True,  # hide from dock — menu bar only
        'CFBundleName': 'Mouse Jiggler',
        'CFBundleDisplayName': 'Mouse Jiggler',
        'CFBundleIdentifier': 'com.jphermans.mouse-jiggler',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
    'packages': ['rumps', 'PIL'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
