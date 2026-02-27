"""Shared utilities."""

from datetime import datetime, timezone


def as_utc_aware(dt: datetime | None) -> datetime | None:
    """Ensure datetime has tzinfo (UTC)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def parse_local_to_utc(s: str) -> datetime:
    """Parse local time string to UTC datetime for DB storage.
    Accepts: '2025-02-14 18:00', '2025-02-14T18:00', '2025-02-14T18:00:00+08:00'.
    Naive strings are treated as local time."""
    s = s.strip()
    if not s:
        raise ValueError("Empty datetime string")
    # Try ISO with timezone first
    if "T" in s or "+" in s or "-" in s[-6:]:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo:
                return dt.astimezone(timezone.utc)
            # Naive from isoformat -> treat as local
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    # Try common formats (local naive)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            # Assume local
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s}")


def format_utc_to_local(dt: datetime | None) -> str:
    """Format UTC datetime to local time string for display."""
    if dt is None:
        return ""
    utc = as_utc_aware(dt)
    local = utc.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")
