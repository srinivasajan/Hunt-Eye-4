# -*- mode: python ; coding: utf-8 -*-
# HuntEye.spec - Correct PyInstaller spec for HuntEye
#
# KEY ARCHITECTURE:
#   All Python packages live under src/ (config, core, ui, simulation, ai, control, perception)
#   pathex=['src'] tells PyInstaller's module graph to resolve imports from src/ as the root.
#   This means PyInstaller compiles config, core, ui, etc. directly into the archive,
#   importable as 'config', 'core', 'ui' etc. — matching what main.py and launcher.py expect.
#
# RUNTIME:
#   launcher.py -> main.main() in same process
#   main.py inserts sys._MEIPASS into sys.path for any late imports
#   config.yaml is copied next to HuntEye.exe (in dist/HuntEye/) for load_config() to find

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

# ---------------------------------------------------------------------------
# Hidden imports: packages that PyInstaller static analysis misses
# ---------------------------------------------------------------------------
hiddenimports = (
    collect_submodules('config') +
    collect_submodules('core') +
    collect_submodules('ui') +
    collect_submodules('simulation') +
    collect_submodules('ai') +
    collect_submodules('control') +
    collect_submodules('perception') +
    collect_submodules('customtkinter') +
    collect_submodules('cv2') +
    [
        'config',
        'config.loader',
        'config.settings',
        'config.writer',
        'core.hal',
        'core.logger',
        'core.shared_state',
        'core.worker_base',
        'core.orchestrator',
        'core.watchdog',
        'core.event_bus',
        'core.fps_counter',
        'core.ipc',
        'core.monitor',
        'core.paths',
        'core.profiler',
        'core.restart_limiter',
        'core.safety',
        'core.service_registry',
        'core.telemetry_stream',
        'core.plugin_loader',
        'core.json_utils',
        'ui.dashboard',
        'ui.ops_state',
        'ui.ui_state',
        'ui.layout_persistence',
        'ui.config_editor',
        'ui.waypoint_editor',
        'ui.preflight',
        'ui.hud',
        'ui.demo_scene',
        'ui.analytics_panel',
        'ui.diagnostics_utils',
        'simulation.camera',
        'simulation.camera_worker',
        'simulation.camera_stream',
        'ai.planner',
        'control.worker',
        'control.mavlink_interface',
        'perception.worker',
        'psutil',
        'yaml',
        'tkinter',
        'customtkinter',
        'cv2',
        'numpy',
    ]
)

# ---------------------------------------------------------------------------
# Data files: config.yaml goes to dist root (next to EXE), assets bundled
# ---------------------------------------------------------------------------
datas = [
    # config.yaml -> dist/HuntEye/ (next to EXE, where get_app_dir() looks)
    ('config.yaml', '.'),
]

# Include customtkinter themes/assets
try:
    datas += collect_data_files('customtkinter')
except Exception:
    pass

# ---------------------------------------------------------------------------
# Analysis: pathex=['src'] is THE critical fix
# ---------------------------------------------------------------------------
a = Analysis(
    ['launcher.py'],
    # pathex tells PyInstaller WHERE to look for imports.
    # Setting 'src' means `from config import ...` resolves to src/config/__init__.py
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_hunteye.py'],
    excludes=[
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'qt_ui',
        'tensorboard',
        'matplotlib',
        'IPython',
        'notebook',
        'stable_baselines3',
        'gymnasium',
    ],
    noarchive=False,
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
    upx=False,   # disabled: upx can corrupt cv2/torch binaries
    console=True,  # Keep console visible so crash_log.txt errors are visible
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='HuntEye',
)