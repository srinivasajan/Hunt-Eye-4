"""Audit Documentation/DEV1_STATUS.md against the current repository.

- Verifies backticked `*.py` references exist (relative to repo root)
- Suggests likely intended paths for missing references (core/ui/simulation)
- Verifies table-stated "Lines" values against current file line counts

This is a lightweight, dependency-free script intended for maintainers.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "Documentation" / "DEV1_STATUS.md"


def _line_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    # Keep it consistent across files that may or may not end with newline
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


def _suggest_fix(missing_rel: str) -> str | None:
    name = Path(missing_rel).name
    for candidate in [
        ROOT / "core" / name,
        ROOT / "ui" / name,
        ROOT / "simulation" / name,
        ROOT / name,
    ]:
        if candidate.exists():
            return candidate.relative_to(ROOT).as_posix()
    return None


def main() -> int:
    if not DOC_PATH.exists():
        print(f"ERROR: missing doc: {DOC_PATH}")
        return 2

    doc_text = DOC_PATH.read_text(encoding="utf-8", errors="replace")

    # 1) Backticked python path references
    referenced_py = sorted(set(re.findall(r"`([^`]*?\.py)`", doc_text)))

    inventory: list[tuple[str, bool, int | None]] = []
    for rel in referenced_py:
        abs_path = (ROOT / rel).resolve()
        exists = abs_path.exists()
        lines = _line_count(abs_path) if exists else None
        inventory.append((rel, exists, lines))

    missing = [rel for (rel, exists, _lines) in inventory if not exists]

    # 2) Table row extraction for the line-count column
    table_rows: list[tuple[str, str, int]] = []
    for m in re.finditer(
        r"\|\s*\*\*(?P<component>[^*]+)\*\*\s*\|\s*`(?P<path>[^`]+)`\s*\|\s*(?P<lines>\d+)\s*\|",
        doc_text,
    ):
        table_rows.append(
            (
                m.group("component").strip(),
                m.group("path").strip(),
                int(m.group("lines")),
            )
        )

    mismatches: list[tuple[str, str, int, int]] = []
    for component, rel_path, stated_lines in table_rows:
        abs_path = (ROOT / rel_path).resolve()
        if not abs_path.exists():
            continue
        actual = _line_count(abs_path)
        if actual != stated_lines:
            mismatches.append((component, rel_path, stated_lines, actual))

    # Report
    print("# Dev1 status cross-check (automated)")
    print(f"Doc: {DOC_PATH.relative_to(ROOT).as_posix()}")
    print(f"Timestamp: {datetime.datetime.now().isoformat(timespec='seconds')}")
    print()

    print(f"Backticked .py references found: {len(referenced_py)}")
    print(f"Backticked .py references resolving: {len(referenced_py) - len(missing)}/{len(referenced_py)}")

    if missing:
        print("\n## Missing backticked references (as written)")
        for rel in missing:
            suggestion = _suggest_fix(rel)
            if suggestion:
                print(f"- {rel} (did you mean `{suggestion}`?)")
            else:
                print(f"- {rel}")

    print("\n## Table line-count verification")
    print(f"Table rows parsed: {len(table_rows)}")
    print(f"Exact line-count matches: {len(table_rows) - len(mismatches)}/{len(table_rows)}")

    if mismatches:
        print("\n### Mismatches (stated vs actual)")
        for component, path, stated, actual in mismatches:
            print(f"- {component}: `{path}` stated {stated}, actual {actual}")

    print("\n## Inventory (backticked references)")
    for rel, exists, lines in inventory:
        status = "OK" if exists else "MISSING"
        lines_s = str(lines) if lines is not None else "-"
        print(f"- `{rel}`: {status}, lines={lines_s}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
