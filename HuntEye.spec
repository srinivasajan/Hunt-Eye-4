# -*- mode: python ; coding: utf-8 -*-
import sys
import os

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'), 
        ('yolov8n.pt', '.'), # Bundle offline YOLO model
        ('models/torch_hub_cache', 'models/torch_hub_cache') # Bundle offline MiDaS cache
    ],
    hiddenimports=[
        'ultralytics', 
        'torch', 
        'torchvision', 
        'psutil', 
        'stable_baselines3', 
        'gymnasium', 
        'cv2', 
        'pymavlink'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HuntEye',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Final MVP is a clean desktop app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HuntEye',
)
