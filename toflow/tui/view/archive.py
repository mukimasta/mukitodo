"""ArchiveView — archived Track/Project/Todo in a tree-like flat list."""

from __future__ import annotations

from typing import Callable

from toflow.database import db_session
from toflow.ops import Result, delete_entity, list_archived_structure, set_archived
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_archive_item
from toflow.tui.pane.flat_list import FlatListPane
from toflow.tui.types import ArchiveRow
from toflow.tui.view.base import View


class ArchiveView(View):
    """Archive secondary view (read archived structure, unarchive/delete only)."""

    title = "Archive"
    status_hint = "[↑↓] move  [a] unarchive  [Backspace] delete  [Esc] back"
    entity_type = EntityType.TODO

    def __init__(self) -> None:
        self._pane = FlatListPane(
            item_formatter=format_archive_item,
            empty_msg="  No archived items.",
        )
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_archived_structure(s)
        if not result.success or not result.data:
            self._pane.set_items([])
            return
        self._pane.set_items(_flatten_archived_rows(result.data))

    # Archive-specific actions: unarchive via [a], delete via [Backspace].

    def archive_confirm_action(self) -> Callable[[], Result | None] | None:
        return self._unarchive_selected

    def _unarchive_selected(self) -> Result | None:
        item = self.pane.selected_item()
        if not item or not item.get("archived", False):
            return Result(False, None, "Cannot unarchive item with archived children")
        with db_session() as s:
            result = set_archived(s, item["entity_type"], int(item["id"]), archived=False)
        self.load_data()
        return result

    def delete_selected(self) -> Result | None:
        item = self.pane.selected_item()
        if not item or not item.get("archived", False):
            return Result(False, None, "Cannot delete unarchived item")
        with db_session() as s:
            result = delete_entity(s, item["entity_type"], int(item["id"]))
        self.load_data()
        return result


def _flatten_archived_rows(data: dict) -> list[ArchiveRow]:
    rows: list[ArchiveRow] = []

    tracks = sorted(
        data.get("tracks", []),
        key=lambda d: _sort_dt(d.get("track", {}).get("archived_at_utc")),
        reverse=True,
    )
    for t in tracks:
        track = t["track"]
        rows.append(ArchiveRow(
            id=track["id"],
            kind="track",
            entity_type=EntityType.TRACK,
            archived=bool(t.get("is_archived", False)),
            status=track.get("status", "active"),
            title=track.get("title") or "?",
            depth=0,
        ))
        projects = sorted(
            t.get("projects", []),
            key=lambda d: _sort_dt(d.get("project", {}).get("archived_at_utc")),
            reverse=True,
        )
        for p in projects:
            project = p["project"]
            rows.append(ArchiveRow(
                id=project["id"],
                kind="project",
                entity_type=EntityType.PROJECT,
                archived=bool(p.get("is_archived", False)),
                status=project.get("status", "active"),
                pinned=bool(project.get("pinned", False)),
                title=project.get("title") or "?",
                description=project.get("description"),
                deadline_utc=project.get("deadline_utc"),
                willingness_hint=project.get("willingness_hint"),
                importance_hint=project.get("importance_hint"),
                urgency_hint=project.get("urgency_hint"),
                session_total_minutes=int(project.get("session_total_minutes") or 0),
                depth=1,
            ))
            todos = sorted(
                p.get("todos", []),
                key=lambda d: _sort_dt(d.get("archived_at_utc")),
                reverse=True,
            )
            for todo in todos:
                rows.append(ArchiveRow(
                    id=todo["id"],
                    kind="todo",
                    entity_type=EntityType.TODO,
                    archived=True,
                    status=todo.get("status", "active"),
                    pinned=bool(todo.get("pinned", False)),
                    title=todo.get("title") or "?",
                    current_stage=todo.get("current_stage", 0),
                    total_stages=todo.get("total_stages", 1),
                    description=todo.get("description"),
                    url=todo.get("url"),
                    deadline_utc=todo.get("deadline_utc"),
                    session_total_minutes=int(todo.get("session_total_minutes") or 0),
                    depth=2,
                ))

    for project in sorted(
        data.get("box_projects", []),
        key=lambda d: _sort_dt(d.get("archived_at_utc")),
        reverse=True,
    ):
        rows.append(ArchiveRow(
            id=project["id"],
            kind="project",
            entity_type=EntityType.PROJECT,
            archived=True,
            status=project.get("status", "active"),
            pinned=bool(project.get("pinned", False)),
            title=f"[Box] {project.get('title') or '?'}",
            description=project.get("description"),
            deadline_utc=project.get("deadline_utc"),
            willingness_hint=project.get("willingness_hint"),
            importance_hint=project.get("importance_hint"),
            urgency_hint=project.get("urgency_hint"),
            session_total_minutes=int(project.get("session_total_minutes") or 0),
            depth=0,
        ))

    for todo in sorted(
        data.get("box_todos", []),
        key=lambda d: _sort_dt(d.get("archived_at_utc")),
        reverse=True,
    ):
        rows.append(ArchiveRow(
            id=todo["id"],
            kind="todo",
            entity_type=EntityType.TODO,
            archived=True,
            status=todo.get("status", "active"),
            pinned=bool(todo.get("pinned", False)),
            title=f"[Box] {todo.get('title') or '?'}",
            current_stage=todo.get("current_stage", 0),
            total_stages=todo.get("total_stages", 1),
            description=todo.get("description"),
            url=todo.get("url"),
            deadline_utc=todo.get("deadline_utc"),
            session_total_minutes=int(todo.get("session_total_minutes") or 0),
            depth=0,
        ))

    return rows


def _sort_dt(value) -> tuple[int, object]:
    if value is None:
        return (0, "")
    return (1, value)
