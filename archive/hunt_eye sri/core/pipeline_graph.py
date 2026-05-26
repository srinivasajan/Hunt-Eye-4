"""Dependency-aware pipeline execution (DAG) for HuntEye.

This module provides a minimal execution graph that can be used to
sequence perception/tracking/control steps with explicit dependencies.

Design goals:
- No external dependencies
- Simple topological execution order
- Usable from WorkerBase (PipelineExecutor)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import inspect
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from core.logger import Logger
from core.worker_base import WorkerBase


class PipelineGraphError(Exception):
    pass


@dataclass
class PipelineNode:
    name: str
    func: Callable[..., Any]
    deps: Set[str] = field(default_factory=set)
    enabled: bool = True

    last_run_at: float | None = None
    last_duration_ms: float | None = None
    last_error: str | None = None


class PipelineGraph:
    def __init__(self):
        self.nodes: Dict[str, PipelineNode] = {}

    def add_node(self, name: str, func: Callable[..., Any], deps: Iterable[str] = ()) -> None:
        if name in self.nodes:
            raise PipelineGraphError(f"duplicate_node:{name}")
        self.nodes[name] = PipelineNode(name=name, func=func, deps=set(deps))

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name not in self.nodes:
            raise PipelineGraphError(f"unknown_node:{name}")
        self.nodes[name].enabled = bool(enabled)

    def topological_order(self) -> List[str]:
        # Kahn's algorithm
        deps = {name: set(node.deps) for name, node in self.nodes.items()}
        missing = {d for name, ds in deps.items() for d in ds if d not in self.nodes}
        if missing:
            raise PipelineGraphError(f"missing_deps:{sorted(missing)}")

        ready = [name for name, ds in deps.items() if not ds]
        order: List[str] = []

        while ready:
            name = ready.pop()
            order.append(name)

            for other, other_deps in deps.items():
                if name in other_deps:
                    other_deps.remove(name)
                    if not other_deps and other not in order and other not in ready:
                        ready.append(other)

        if len(order) != len(self.nodes):
            # cycle
            remaining = [name for name, ds in deps.items() if ds]
            raise PipelineGraphError(f"cycle_detected:{remaining}")

        return order


class PipelineExecutor(WorkerBase):
    """Executes a PipelineGraph repeatedly in topological order."""

    def __init__(
        self,
        name: str,
        state: Any,
        graph: PipelineGraph,
        loop_interval: float = 0.0,
        restartable: bool = True,
    ):
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.graph = graph
        self._order_cache: List[str] | None = None

    def _order(self) -> List[str]:
        if self._order_cache is None:
            self._order_cache = self.graph.topological_order()
        return self._order_cache

    def invalidate_order(self) -> None:
        self._order_cache = None

    def run_once(self) -> None:
        context: Dict[str, Any] = {}

        for node_name in self._order():
            node = self.graph.nodes[node_name]
            if not node.enabled:
                continue

            start = time.perf_counter()
            try:
                _call_node(node.func, self.state, context)
                node.last_error = None
            except Exception as e:
                node.last_error = str(e)
                Logger.error(f"Pipeline node failed | node={node.name} | error={e}")
            finally:
                duration_ms = (time.perf_counter() - start) * 1000.0
                node.last_duration_ms = duration_ms
                node.last_run_at = time.time()

        self.heartbeat()

    def safe_run(self) -> None:
        while self.running:
            self.run_once()
            self.sleep()


def _call_node(func: Callable[..., Any], state: Any, context: Dict[str, Any]) -> Any:
    sig = None
    try:
        sig = inspect.signature(func)
    except Exception:
        sig = None

    if sig is None:
        return func(state, context)

    params = list(sig.parameters.values())

    # Allow: () | (state) | (state, context)
    if len(params) == 0:
        return func()
    if len(params) == 1:
        return func(state)
    return func(state, context)
