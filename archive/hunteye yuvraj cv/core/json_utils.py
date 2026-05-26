"""JSON/serialization helpers for HuntEye.

These utilities are used by IPC and snapshot export paths.
They intentionally avoid importing UI modules.
"""

from __future__ import annotations

from typing import Any


def json_safe(value: Any) -> Any:
    """Convert common non-JSON-friendly values into JSON-serializable forms."""

    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [json_safe(item) for item in value]

    # numpy scalars (and other scalar-ish objects)
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except Exception:
            pass

    # pathlib.Path
    if hasattr(value, "as_posix") and callable(getattr(value, "as_posix")):
        try:
            return value.as_posix()
        except Exception:
            pass

    return value
