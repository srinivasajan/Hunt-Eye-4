"""Minimal plugin loader (Dev 1.1 plugin architecture).

Plugins are plain Python modules discovered from configured paths.

A plugin module can optionally define:
- register(context): called once at startup

The register() function may:
- register services in the ServiceRegistry
- add workers to the Orchestrator
- subscribe to the EventBus

This loader is intentionally small and dependency-free.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, List, Optional

from core.logger import Logger
from core.service_registry import get_service_registry


@dataclass
class PluginContext:
    state: Any
    orchestrator: Any
    config: dict[str, Any]
    registry: Any


def load_plugins(
    *,
    state: Any,
    orchestrator: Any,
    config: dict[str, Any],
    paths: Iterable[str],
) -> list[str]:
    """Load plugins from a list of paths.

    Returns list of loaded plugin identifiers.
    """

    registry = get_service_registry()
    context = PluginContext(state=state, orchestrator=orchestrator, config=config, registry=registry)

    loaded: list[str] = []

    for raw in paths:
        path = Path(raw)
        if not path.exists():
            Logger.warning(f"Plugin path missing | path={path}")
            continue

        if path.is_dir():
            for file in sorted(path.glob("*.py")):
                if file.name.startswith("_"):
                    continue
                plugin_id = _load_plugin_file(file, context)
                if plugin_id:
                    loaded.append(plugin_id)
            continue

        if path.is_file() and path.suffix == ".py":
            plugin_id = _load_plugin_file(path, context)
            if plugin_id:
                loaded.append(plugin_id)
            continue

        # Treat as import path
        plugin_id = _load_plugin_module(str(raw), context)
        if plugin_id:
            loaded.append(plugin_id)

    return loaded


def _load_plugin_file(path: Path, context: PluginContext) -> str | None:
    module_name = f"huneye_plugin_{path.stem}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            Logger.error(f"Plugin load failed | file={path} | reason=no_spec")
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        _run_register(module, context)
        Logger.info(f"Plugin loaded | file={path}")
        return str(path)

    except Exception as e:
        Logger.error(f"Plugin load failed | file={path} | error={e}")
        return None


def _load_plugin_module(import_path: str, context: PluginContext) -> str | None:
    try:
        module = importlib.import_module(import_path)
        _run_register(module, context)
        Logger.info(f"Plugin loaded | module={import_path}")
        return import_path
    except Exception as e:
        Logger.error(f"Plugin load failed | module={import_path} | error={e}")
        return None


def _run_register(module: ModuleType, context: PluginContext) -> None:
    register = getattr(module, "register", None)
    if callable(register):
        register(context)
