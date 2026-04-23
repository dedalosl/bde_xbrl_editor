"""Lightweight performance timing helpers for app-visible instrumentation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StageTiming:
    """Elapsed wall time for a named stage."""

    name: str
    elapsed_seconds: float


@dataclass(frozen=True)
class LoadTiming:
    """Elapsed wall time for a load/open flow."""

    total_seconds: float
    stages: tuple[StageTiming, ...] = field(default_factory=tuple)


def format_duration(seconds: float) -> str:
    """Render a short human-readable duration."""
    if seconds < 1:
        return f"{seconds * 1000:.0f} ms"
    if seconds < 10:
        return f"{seconds:.2f} s"
    return f"{seconds:.1f} s"


def format_stage_timings(stage_timings: tuple[StageTiming, ...]) -> str:
    """Render stage timings as a compact comma-separated string."""
    return ", ".join(
        f"{stage.name} {format_duration(stage.elapsed_seconds)}"
        for stage in stage_timings
    )
