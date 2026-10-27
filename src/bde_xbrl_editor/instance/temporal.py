"""Lossless XBRL dateUnion boundaries, independent of XPath precision limits.

XBRL 2.1 section 4.7.2: date-only instant/end values denote the following
midnight; start values denote the same midnight. Unzoned values stay unzoned.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import ReportingPeriod

_LEXICAL = re.compile(
    r"(?P<day>\d{4}-\d{2}-\d{2})"
    r"(?:T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d+))?)?(?P<zone>Z|[+-]\d{2}:\d{2})?\Z"
)


@dataclass(frozen=True)
class TemporalBoundary:
    wall: datetime
    fraction: str
    offset: int | None

    def isoformat(self, *, canonical: bool = False) -> str:
        wall = self.wall
        zone = ""
        if self.offset is not None:
            if canonical:
                wall -= timedelta(minutes=self.offset)
                zone = "Z"
            elif not self.offset:
                zone = "Z"
            else:
                zone = f"{'+' if self.offset > 0 else '-'}{abs(self.offset) // 60:02}:{abs(self.offset) % 60:02}"
        fraction = self.fraction.rstrip("0") if canonical else self.fraction
        value = wall.isoformat() + (f".{fraction}" if fraction else "") + zone
        # Retain the historic key form for unzoned integral midnight boundaries.
        if canonical and not zone and not fraction and wall.time() == datetime.min.time():
            return wall.date().isoformat()
        return value


def parse_boundary(lexical: str, *, end: bool = False) -> TemporalBoundary:
    match = _LEXICAL.fullmatch(lexical.strip())
    if match is None:
        raise ValueError(f"Invalid XBRL dateUnion: {lexical!r}")
    parts = match.groupdict()
    hour, minute, second = (int(parts[name] or 0) for name in ("hour", "minute", "second"))
    fraction = parts["fraction"] or ""
    next_day = parts["hour"] is None and end
    if hour == 24:
        if minute or second or fraction.strip("0"):
            raise ValueError("24:00 must have zero minutes, seconds and fraction")
        hour, next_day = 0, True
    wall = datetime.fromisoformat(parts["day"]).replace(hour=hour, minute=minute, second=second)
    if next_day:
        wall += timedelta(days=1)
    zone = parts["zone"]
    offset = None
    if zone:
        offset = 0
        if zone != "Z":
            hours, minutes = int(zone[1:3]), int(zone[4:6])
            if hours > 14 or minutes > 59 or (hours == 14 and minutes):
                raise ValueError(f"Invalid timezone offset: {zone}")
            offset = (hours * 60 + minutes) * (1 if zone[0] == "+" else -1)
    return TemporalBoundary(wall, fraction, offset)


def normalize_lexical(lexical: str) -> str:
    """Validate without losing precision; accept legacy 24:00 but never emit it."""
    lexical = lexical.strip()
    boundary = parse_boundary(lexical)
    return boundary.isoformat() if "T24:" in lexical else lexical


def period_lexical(period: ReportingPeriod, role: str) -> str:
    day = getattr(period, f"{role}_date")
    if day is None:
        raise ValueError(f"Period has no {role} boundary")
    lexical = getattr(period, f"{role}_lexical", None)
    if lexical:
        # Date-only UI edits preserve the original clock, precision and zone.
        lexical = day.isoformat() + lexical[10:]
        return normalize_lexical(lexical)
    date_only = role == "start" or getattr(period, f"{role}_date_only", False)
    return day.isoformat() + ("" if date_only else "T00:00:00")


def period_boundary(period: ReportingPeriod, role: str) -> TemporalBoundary:
    return parse_boundary(period_lexical(period, role), end=role != "start")


def period_key(period: ReportingPeriod) -> tuple:
    if period.period_type == "forever":
        return ("forever",)
    roles = ("instant",) if period.period_type == "instant" else ("start", "end")
    return (
        period.period_type,
        *(period_boundary(period, role).isoformat(canonical=True) for role in roles),
    )


def validate_duration(period: ReportingPeriod) -> None:
    """Check exact bounds without inventing a timezone for an unzoned value."""
    start, end = (period_boundary(period, role) for role in ("start", "end"))
    start_wall, end_wall = start.wall, end.wall
    if (start.offset is None) != (end.offset is None):
        # XML Schema mixed-zone ordering is partial. Reject only a definitely
        # invalid interval; leave indeterminate ordering to instance validation.
        if start.offset is None:
            start_wall -= timedelta(hours=14)
            end_wall -= timedelta(minutes=end.offset)
        else:
            start_wall -= timedelta(minutes=start.offset)
            end_wall += timedelta(hours=14)
    elif start.offset is not None:
        start_wall -= timedelta(minutes=start.offset)
        end_wall -= timedelta(minutes=end.offset)
    # Zero-pad fractions for exact lexicographic comparison (no Decimal context).
    width = max(len(start.fraction), len(end.fraction))
    if (end_wall, end.fraction.ljust(width, "0")) <= (start_wall, start.fraction.ljust(width, "0")):
        raise ValueError("Duration end must be later than start")


def xfi_boundary(period: ReportingPeriod, role: str):
    """Fail explicitly rather than let elementpath truncate fractional seconds."""
    from elementpath.datatypes import DateTime10

    boundary = period_boundary(period, role)
    if len(boundary.fraction.rstrip("0")) > 6:
        raise ValueError(
            "Unsupported XFI dateTime precision: elementpath supports at most microseconds"
        )
    return DateTime10.fromstring(boundary.isoformat())
