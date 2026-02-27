"""CLI entity display formatters - plain text for print()."""

from typing import Any

from toflow.utils import format_utc_to_local


def _format_entity(item: dict[str, Any], *, show_stage: bool = False) -> str:
    """Base format: id title [status] [cur/total]. No [archived] prefix."""
    eid = item.get("id", "?")
    title = item.get("title", "")
    status = item.get("status", "")
    parts = [str(eid), title or "(no title)"]
    if status:
        parts.append(f"[{status}]")
    if show_stage:
        total = item.get("total_stages", 1)
        cur = item.get("current_stage", 0)
        parts.append(f"{cur}/{total}")
    return " ".join(parts)


def format_track(item: dict[str, Any]) -> str:
    """Track: [archived] id title [status]."""
    prefix = "[archived] " if item.get("archived") else ""
    return prefix + _format_entity(item, show_stage=False)


def format_project(item: dict[str, Any]) -> str:
    """Project: [archived] id title [status]."""
    prefix = "[archived] " if item.get("archived") else ""
    return prefix + _format_entity(item, show_stage=False)


def format_todo(item: dict[str, Any]) -> str:
    """Todo: [archived] id title [status] cur/total."""
    prefix = "[archived] " if item.get("archived") else ""
    return prefix + _format_entity(item, show_stage=True)


def format_session_timeline(item: dict[str, Any]) -> str:
    """Session in timeline: id | parent | duration | time_range | desc."""
    sid = item.get("id", "?")
    parent = item.get("parent_info", "")
    duration = item.get("duration_minutes", "")
    started = format_utc_to_local(item.get("started_at_utc"))
    ended = format_utc_to_local(item.get("ended_at_utc"))
    desc = (item.get("description") or "")[:40]
    return f"{sid} | {parent} | {duration}min | {started} ~ {ended} | {desc}"
