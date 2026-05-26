import sys
from pathlib import Path

def get_app_dir() -> Path:
    """Return the persistent directory where user data (configs, logs, recordings) should live.
    
    If packaged with PyInstaller, this is the directory containing the .exe.
    If running from source, this is the root project directory.
    This explicitly avoids sys._MEIPASS which is a temporary directory that is deleted on exit.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys.executable).resolve().parent
    
    # Running from source. Assuming this file is in src/core/paths.py
    return Path(__file__).resolve().parent.parent.parent
