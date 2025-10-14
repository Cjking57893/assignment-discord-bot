from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

import os


def get_local_tz():
    """
    Resolve the local timezone to use for display and local-week calculations.
    Priority:
      1) TIMEZONE env var (IANA tz name like 'America/New_York')
      2) System local timezone via datetime.now().astimezone().tzinfo
    """
    tz_env = os.getenv("TIMEZONE")
    if tz_env and ZoneInfo is not None:
        try:
            return ZoneInfo(tz_env)
        except Exception:
            pass
    # Fallback to system local timezone
    return datetime.now().astimezone().tzinfo or timezone.utc


def parse_canvas_datetime(value: str) -> datetime:
    """
    Parse Canvas ISO8601 datetime strings into timezone-aware datetimes.
    Canvas typically returns UTC with 'Z'. Example: '2025-10-01T03:59:00Z'.
    """
    if not value:
        raise ValueError("Empty datetime string")
    # Normalize trailing Z to +00:00 for fromisoformat
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    # If naive, assume UTC (defensive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_utc_iso_z(dt: datetime) -> str:
    """Convert any datetime to a UTC ISO8601 string with trailing 'Z'."""
    if dt.tzinfo is None:
        # Assume it's local time if naive; attach local tz then convert to UTC
        dt = dt.replace(tzinfo=get_local_tz())
    dt_utc = dt.astimezone(timezone.utc)
    # timespec='seconds' ensures we drop microseconds for consistent storage
    return dt_utc.replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def to_local(dt_or_str: datetime | str) -> datetime:
    """
    Convert a UTC timestamp (datetime or ISO string) to local timezone datetime.
    If a string is provided, it will be parsed via parse_canvas_datetime first.
    """
    if isinstance(dt_or_str, str):
        dt = parse_canvas_datetime(dt_or_str)
    else:
        dt = dt_or_str
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_local_tz())


def format_local(dt_or_str: datetime | str, fmt: str = "%b %d, %Y, %I:%M %p") -> str:
    """Format a UTC datetime (or ISO string) in the local timezone using fmt."""
    return to_local(dt_or_str).strftime(fmt)


def week_start_end_local(reference: Optional[datetime] = None):
    """
    Given a reference datetime (naive treated as local), return the Monday 00:00:00
    and Sunday 23:59:59 in local timezone as aware datetimes.
    """
    ref = reference or datetime.now()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=get_local_tz())
    # Compute Monday 00:00 local
    weekday = ref.weekday()  # Monday=0
    monday = (ref.replace(hour=0, minute=0, second=0, microsecond=0) -
              timedelta(days=weekday))
    # Sunday 23:59:59 local
    sunday = monday.replace(hour=23, minute=59, second=59) + timedelta(days=6)
    return monday, sunday
