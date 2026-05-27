# rthook_hunteye.py - PyInstaller runtime hook for HuntEye
# Ensures src/ packages are importable from within the bundled EXE.
import sys, os

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # In PyInstaller, sys._MEIPASS is the extraction directory (_internal/).
    # All src packages are extracted there directly (thanks to pathex=['src']).
    # No extra path manipulation needed - but add _MEIPASS explicitly as safety.
    _meipass = sys._MEIPASS
    if _meipass not in sys.path:
        sys.path.insert(0, _meipass)
