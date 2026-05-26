"""Layout persistence for HuntEye dashboard (Dev 1.2 advanced usability).

Stores UIState as JSON in sessions/ so it persists across runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.logger import Logger


DEFAULT_LAYOUT_PATH = Path("sessions") / "ui_layout.json"


def load_layout(path: Path | str = DEFAULT_LAYOUT_PATH) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}

    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        Logger.warning(f"Failed to load UI layout | path={p} | error={e}")
        return {}


def save_layout(data: Dict[str, Any], path: Path | str = DEFAULT_LAYOUT_PATH) -> bool:
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return True
    except Exception as e:
        Logger.warning(f"Failed to save UI layout | path={p} | error={e}")
        return False
