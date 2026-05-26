"""
Task Scheduler for HuntEye Infrastructure (Dev 1.1).

Provides scheduling capabilities for periodic and one-time tasks
within the runtime system. Tasks run in the scheduler's own thread
or can be executed by worker threads.
"""

import threading
import time
import heapq
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from core.logger import Logger
from core.worker_base import WorkerBase


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 0  # Lower numbers = higher priority
    scheduled_time: float = field(default_factory=time.time)
    interval: Optional[float] = None  # None for one-time, float for repeating (seconds)
    last_run: float = 0.0
    run_count: int = 0
    max_runs: Optional[int] = None  # None for unlimited
    
    def __lt__(self, other):
        """For heap ordering: prioritize by time, then priority."""
        if self.scheduled_time != other.scheduled_time:
            return self.scheduled_time < other.scheduled_time
        return self.priority < other.priority
    
    def is_ready(self, current_time: float) -> bool:
        """Check if task is ready to run."""
        return current_time >= self.scheduled_time
    
    def should_continue(self) -> bool:
        """Check if task should continue running (for repeating tasks)."""
        if self.interval is None:
            # One-time task
            return self.run_count < 1
        if self.max_runs is not None:
            return self.run_count < self.max_runs
        return True  # Unlimited repeating task
    
    def reschedule(self, current_time: float):
        """Reschedule the task for next execution."""
        if self.interval is not None:
            self.scheduled_time = current_time + self.interval
            self.last_run = current_time
            self.run_count += 1
        else:
            # One-time task - mark as completed
            self.run_count = 1


class Scheduler(WorkerBase):
    """
    Task scheduler worker that executes scheduled tasks.
    
    Can be used to schedule maintenance tasks, periodic health checks,
    cleanup operations, etc.
    """
    
    def __init__(self, 
                 name: str = "Scheduler",
                 state: Any = None,
                 loop_interval: float = 0.1,
                 restartable: bool = True):
        """
        Initialize the scheduler.
        
        Args:
            name: Worker name
            state: SharedState instance (optional, for integration)
            loop_interval: Main loop sleep interval (seconds)
            restartable: Whether worker can be auto-restarted
        """
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.tasks: list[ScheduledTask] = []
        self.task_lock = threading.RLock()
        self.next_task_time: float = 0.0
        
    def schedule_task(self, 
                     name: str,
                     func: Callable,
                     delay: float = 0.0,
                     interval: Optional[float] = None,
                     priority: int = 0,
                     args: tuple = (),
                     kwargs: dict = None,
                     max_runs: Optional[int] = None) -> bool:
        """
        Schedule a task for execution.
        
        Args:
            name: Task name (for identification)
            func: Function to call
            delay: Initial delay before first execution (seconds)
            interval: Repeat interval (None for one-time)
            priority: Priority level (lower = higher priority)
            args: Positional arguments for function
            kwargs: Keyword arguments for function
            max_runs: Maximum number of executions (None for unlimited)
            
        Returns:
            True if task was scheduled successfully
        """
        if kwargs is None:
            kwargs = {}
            
        task = ScheduledTask(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_time=time.time() + delay,
            interval=interval,
            max_runs=max_runs
        )
        
        with self.task_lock:
            heapq.heappush(self.tasks, task)
            self._update_next_task_time()
            
        Logger.info(f"Task scheduled | name={name} | delay={delay}s | interval={interval}")
        return True
    
    def cancel_task(self, name: str) -> bool:
        """
        Cancel a scheduled task by name.
        
        Args:
            name: Name of task to cancel
            
        Returns:
            True if task was found and cancelled
        """
        with self.task_lock:
            for i, task in enumerate(self.tasks):
                if task.name == name:
                    del self.tasks[i]
                    heapq.heapify(self.tasks)  # Re-heapify after removal
                    self._update_next_task_time()
                    Logger.info(f"Task cancelled | name={name}")
                    return True
        Logger.warning(f"Task not found for cancellation | name={name}")
        return False
    
    def _update_next_task_time(self):
        """Update the next task time based on the heap."""
        with self.task_lock:
            if self.tasks:
                self.next_task_time = self.tasks[0].scheduled_time
            else:
                self.next_task_time = float('inf')
    
    def safe_run(self) -> None:
        """
        Main scheduler loop. Executes tasks when they are due.
        """
        while self.running:
            current_time = time.time()
            
            # Check if any tasks are ready to run
            ready_tasks = []
            with self.task_lock:
                # Extract all ready tasks
                while (self.tasks and 
                       self.tasks[0].is_ready(current_time) and 
                       self.tasks[0].should_continue()):
                    task = heapq.heappop(self.tasks)
                    ready_tasks.append(task)
                
                # Update next task time
                self._update_next_task_time()
            
            # Execute ready tasks (outside lock to allow rescheduling during execution)
            for task in ready_tasks:
                try:
                    Logger.debug(f"Executing task | name={task.name}")
                    task.func(*task.args, **task.kwargs)
                    task.reschedule(current_time)
                    
                    # Reschedule if it should continue
                    if task.should_continue() and task.interval is not None:
                        with self.task_lock:
                            heapq.heappush(self.tasks, task)
                            self._update_next_task_time()
                            
                except Exception as e:
                    Logger.error(f"Task execution failed | name={task.name} | error={e}")
                    # Don't reschedule failed tasks by default
                    # (could be made configurable)
            
            # Sleep until next task or loop interval
            with self.task_lock:
                if self.tasks:
                    sleep_time = min(
                        self.loop_interval,
                        max(0, self.next_task_time - current_time)
                    )
                else:
                    sleep_time = self.loop_interval
            
            self.sleep(sleep_time)
            
            # Update heartbeat
            self.heartbeat()


# Convenience functions for global scheduler access
_global_scheduler: Optional[Scheduler] = None
_scheduler_lock = threading.RLock()


def get_scheduler(state: Any = None) -> Scheduler:
    """
    Get or create the global scheduler instance.
    
    Args:
        state: SharedState instance (passed to scheduler on creation)
        
    Returns:
        Global Scheduler instance
    """
    global _global_scheduler
    with _scheduler_lock:
        if _global_scheduler is None:
            _global_scheduler = Scheduler(state=state)
        return _global_scheduler


def schedule_task(name: str,
                 func: Callable,
                 delay: float = 0.0,
                 interval: Optional[float] = None,
                 priority: int = 0,
                 args: tuple = (),
                 kwargs: dict = None,
                 max_runs: Optional[int] = None,
                 state: Any = None) -> bool:
    """
    Schedule a task using the global scheduler.
    
    See Scheduler.schedule_task() for parameter details.
    """
    return get_scheduler(state).schedule_task(
        name=name,
        func=func,
        delay=delay,
        interval=interval,
        priority=priority,
        args=args,
        kwargs=kwargs,
        max_runs=max_runs
    )


def cancel_task(name: str, state: Any = None) -> bool:
    """
    Cancel a task using the global scheduler.
    """
    return get_scheduler(state).cancel_task(name)