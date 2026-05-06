from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class MaintenanceLoopResult:
    runs_completed: int


def run_maintenance_loop(
    maintain_once: Callable[[], object],
    interval_seconds: int,
    sleep: Callable[[int], object],
    max_runs: int | None = None,
) -> MaintenanceLoopResult:
    if interval_seconds <= 0:
        raise ValueError("Maintenance interval must be positive.")

    runs_completed = 0
    while max_runs is None or runs_completed < max_runs:
        maintain_once()
        runs_completed += 1
        if max_runs is not None and runs_completed >= max_runs:
            break
        sleep(interval_seconds)

    return MaintenanceLoopResult(runs_completed)
