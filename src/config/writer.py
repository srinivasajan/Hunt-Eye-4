"""Write HuntEye config.yaml in a format compatible with config.loader._parse_simple_yaml.

Notes:
- Only supports dicts and scalar/list values.
- Lists are emitted inline: [a, b, c]
"""

from __future__ import annotations

from typing import Any, Dict


def dump_simple_yaml(data: Dict[str, Any]) -> str:
    lines: list[str] = []

    def emit_dict(d: Dict[str, Any], indent: int) -> None:
        for key in sorted(d.keys()):
            value = d[key]
            prefix = " " * indent + f"{key}:"
            if isinstance(value, dict):
                lines.append(prefix)
                emit_dict(value, indent + 2)
            else:
                lines.append(prefix + " " + _format_scalar(value))

    emit_dict(data, 0)
    return "\n".join(lines) + "\n"


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        # keep readable but stable
        return ("%.6f" % value).rstrip("0").rstrip(".") if value != 0 else "0.0"
    if isinstance(value, list):
        inner = ", ".join(_format_scalar(v) for v in value)
        return f"[{inner}]"

    text = str(value)
    # Quote strings to avoid accidental parsing issues
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f"\"{escaped}\""
