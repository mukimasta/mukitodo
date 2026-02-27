"""Item formatters — pure functions for one-row rendering."""

from datetime import datetime
from typing import Any

from toflow.tui.pane.base import FormattedText
from toflow.tui.text_width import text_width, truncate_text
from toflow.tui.types import (
    ArchiveRow,
    ProjectItem,
    TimelineRow,
    TodoViewItem,
    TrackItem,
)
from toflow.utils import as_utc_aware

NOW_TABLE_WIDTH = 64
PROJECT_ROW_WIDTH = 56
TODO_ROW_WIDTH = 56
ARCHIVE_ROW_WIDTH = 56
TIMELINE_ROW_WIDTH = 72

STATUS_ICON = {
    "active": "○",
    "sleeping": "z",
    "finished": "◉",
    "done": "◉",
    "cancelled": "×",
}


def _safe_text(value: Any) -> str:
    text = str(value or "")
    return text.strip()


def _has_text(value: Any) -> bool:
    return bool(_safe_text(value))


def _stage_tag(item: TodoViewItem | ArchiveRow | dict[str, Any]) -> str:
    total = max(1, int(item.get("total_stages") or 1))
    cur = max(0, min(int(item.get("current_stage") or 0), total))
    if total <= 1:
        return ""
    return f"[{cur}/{total}]"


def _deadline_tag(item: dict[str, Any]) -> str:
    deadline = as_utc_aware(item.get("deadline_utc"))
    if deadline is None:
        return ""
    return f"DDL {deadline.astimezone():%m-%d}"


def _session_flag(item: dict[str, Any]) -> str:
    raw_minutes = item.get("session_total_minutes")
    if raw_minutes is None:
        # backward compatibility for in-memory rows not yet migrated
        raw_hours = float(item.get("session_total_hours") or 0.0)
        minutes = int(raw_hours * 60.0)
    else:
        minutes = int(raw_minutes)

    if minutes <= 0:
        return ""

    if minutes < 60:
        return f"[⧗{minutes}m]"

    hours = minutes // 60
    remain = minutes % 60
    return f"[⧗{hours}h{remain}m]"


def _description_flag(item: dict[str, Any]) -> str:
    if _has_text(item.get("description")):
        return "[≡]"
    return ""


def _url_flag(item: dict[str, Any]) -> str:
    if _has_text(item.get("url")):
        return "[↗]"
    return ""


def _project_hints(item: ProjectItem | ArchiveRow | dict[str, Any]) -> str:
    tags: list[str] = []
    if int(item.get("willingness_hint") or 0) >= 2:
        tags.append("♥ ")
    if int(item.get("importance_hint") or 0) >= 2:
        tags.append("⭑ ")
    if int(item.get("urgency_hint") or 0) >= 2:
        tags.append("⚡")
    return "".join(tags)


def _flags_text(*flags: str) -> str:
    return "".join(flag for flag in flags if flag)


def _compose_left(icon: str, title: str) -> str:
    parts: list[str] = []
    if icon:
        parts.append(icon)
    parts.append(title if title else "?")
    return " ".join(parts)


def _compose_right(*parts: str) -> str:
    return " ".join(part for part in parts if part)


def _lr_row(
    left: str,
    right: str = "",
    *,
    width: int,
    left_style: str = "",
    right_style: str = "class:item.meta",
    fill_to_width: bool = False,
    sep: str = "",
) -> FormattedText:
    total_width = max(1, int(width))
    left_text = _safe_text(left)
    right_text = _safe_text(right)
    sep_text = _safe_text(sep)
    sep_width = text_width(sep_text) if sep_text else 0

    if not right_text:
        fitted_left = truncate_text(left_text, total_width)
        if not fill_to_width:
            return [(left_style, fitted_left)]
        pad = " " * max(0, total_width - text_width(fitted_left))
        if pad:
            return [(left_style, fitted_left), ("", pad)]
        return [(left_style, fitted_left)]

    right_width = text_width(right_text)
    if right_width >= total_width:
        return [(right_style, truncate_text(right_text, total_width))]

    max_left_width = total_width - right_width - 1 - sep_width
    if max_left_width <= 0:
        return [(right_style, truncate_text(right_text, total_width))]

    fitted_left = truncate_text(left_text, max_left_width)
    pad = " " * max(1, total_width - text_width(fitted_left) - sep_width - right_width)
    segments: FormattedText = [(left_style, fitted_left)]
    if sep_text:
        segments.append(("class:dim", sep_text))
    segments.append(("", pad))
    segments.append((right_style, right_text))
    return segments


def _project_icon(item: ProjectItem | ArchiveRow | dict[str, Any]) -> str:
    if bool(item.get("pinned")):
        return "✜"
    return STATUS_ICON.get(str(item.get("status") or "active"), "○")


def _todo_icon(item: TodoViewItem | ArchiveRow | dict[str, Any]) -> str:
    if bool(item.get("pinned")):
        return "✜"
    return STATUS_ICON.get(str(item.get("status") or "active"), "○")


def format_track_item(item: TrackItem) -> FormattedText:
    status = str(item.get("status") or "active")
    title = _safe_text(item.get("title")) or "?"
    return [(f"class:track.{status}", title)]


def format_track_group(item: TrackItem) -> FormattedText:
    status = str(item.get("status") or "active")
    title = _safe_text(item.get("title")) or "?"
    return [("bold", title)]


def format_project_row(item: ProjectItem) -> FormattedText:
    status = str(item.get("status") or "active")
    left = _compose_left(_project_icon(item), _safe_text(item.get("title")) or "?")
    right = _compose_right(
        _flags_text(_description_flag(item), _session_flag(item)),
        _project_hints(item),
        _deadline_tag(item),
    )
    left_style = "class:item.pinned" if bool(item.get("pinned")) else f"class:project.{status}"
    return _lr_row(left, right, width=PROJECT_ROW_WIDTH, left_style=left_style)


def format_todo_item(item: TodoViewItem) -> FormattedText:
    status = str(item.get("status") or "active")
    left = _compose_left(_todo_icon(item), _safe_text(item.get("title")) or "?")
    right = _compose_right(
        _flags_text(_description_flag(item), _url_flag(item), _session_flag(item)),
        _stage_tag(item),
        _deadline_tag(item),
    )
    left_style = "class:item.pinned" if bool(item.get("pinned")) else f"class:todo.{status}"
    return _lr_row(left, right, width=TODO_ROW_WIDTH, left_style=left_style)


def format_archive_item(item: ArchiveRow) -> FormattedText:
    kind = _safe_text(item.get("kind"))
    indent = "  " * int(item.get("depth") or 0)
    archived = bool(item.get("archived"))
    archived_suffix = "" if archived else " (has archived children)"

    if kind == "track":
        status = str(item.get("status") or "active")
        title = _safe_text(item.get("title")) or "?"
        base = title
        style = "class:dim" if not archived else f"class:track.{status}"
        return [(style, f"{indent}{base}{archived_suffix}")]

    if kind == "project":
        status = str(item.get("status") or "active")
        left = _compose_left(_project_icon(item), _safe_text(item.get("title")) or "?")
        right = _compose_right(
            _flags_text(_description_flag(item), _session_flag(item)),
            _project_hints(item),
            _deadline_tag(item),
            archived_suffix.strip(),
        )
        left_style = "class:dim" if not archived else ("class:item.pinned" if bool(item.get("pinned")) else f"class:project.{status}")
        row = _lr_row(left, right, width=ARCHIVE_ROW_WIDTH, left_style=left_style)
        return [("", indent), *row]

    status = str(item.get("status") or "active")
    left = _compose_left(_todo_icon(item), _safe_text(item.get("title")) or "?")
    right = _compose_right(
        _flags_text(_description_flag(item), _url_flag(item), _session_flag(item)),
        _stage_tag(item),
        _deadline_tag(item),
        archived_suffix.strip(),
    )
    left_style = "class:dim" if not archived else ("class:item.pinned" if bool(item.get("pinned")) else f"class:todo.{status}")
    row = _lr_row(left, right, width=ARCHIVE_ROW_WIDTH, left_style=left_style)
    return [("", indent), *row]


def format_timeline_item(item: TimelineRow) -> FormattedText:
    if item.get("kind") == "date_header":
        return [("class:dim", f"-- {item.get('date_label', '')} --")]

    ended_at: datetime | None = item.get("ended_at_utc")
    started_at: datetime | None = item.get("started_at_utc")
    time_str = ended_at.astimezone().strftime("%H:%M") if ended_at else "??:??"
    time_str = f"{time_str:>5}"  # column align HH:MM

    duration = item.get("duration_minutes")
    if duration is not None:
        duration_str = f"{int(duration)}m"
    elif started_at is not None and ended_at is not None:
        duration_str = f"{int((ended_at - started_at).total_seconds() // 60)}m"
    else:
        duration_str = "?m"
    duration_str = f"{duration_str:>4}"  # column align 25m, 120m

    parent_info = item.get("parent_info") or "Unknown"
    parts = [p.strip() for p in str(parent_info).split("/") if p.strip()]
    todo_title = parts[-1] if parts else "Unknown"
    context = parts[-2] if len(parts) >= 2 else "Box"

    description = _safe_text(item.get("description"))
    left_parts = [time_str, duration_str, todo_title]
    if description:
        left_parts.append("·")
        left_parts.append(description)
    left = " ".join(left_parts)
    right = context
    return _lr_row(left, right, width=TIMELINE_ROW_WIDTH, right_style="class:item.meta")


def format_now_today_item(item: dict) -> FormattedText:
    if item.get("_virtual") == "add":
        return _lr_row("+ Add...", width=NOW_TABLE_WIDTH, left_style="class:dim", fill_to_width=True)

    planned = max(1, int(item.get("planned_sessions") or 1))
    completed = max(0, min(int(item.get("completed_sessions") or 0), planned))
    dots = " ".join("●" if idx < completed else "○" for idx in range(planned))
    left = f"{'✓ ' if completed >= planned else ''}{_safe_text(item.get('title')) or '?'}"
    project = _safe_text(item.get("project_title"))
    right = _compose_right(dots, project)
    left_style = "class:item.done" if completed >= planned else ""
    return _lr_row(
        left,
        right,
        width=NOW_TABLE_WIDTH,
        left_style=left_style,
        right_style="class:item.meta",
        fill_to_width=True,
    )


def format_now_suggestion_item(item: dict) -> FormattedText:
    title = _safe_text(item.get("title")) or "?"
    context = _safe_text(item.get("project_title") or item.get("track_title") or "Box")
    reason_tags = [str(tag).strip() for tag in (item.get("reason_tags") or []) if str(tag).strip()]
    reason = f"[{reason_tags[0]}]" if reason_tags else ""
    right = _compose_right(context, reason)

    if item.get("in_today"):
        return _lr_row(
            f"✓ {title}",
            right,
            width=NOW_TABLE_WIDTH,
            left_style="class:item.dim",
            right_style="class:item.dim",
            fill_to_width=True,
        )
    return _lr_row(
        title,
        right,
        width=NOW_TABLE_WIDTH,
        right_style="class:item.meta",
        fill_to_width=True,
    )
