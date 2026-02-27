"""NOW Today queue store."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session as DBSession

from toflow.database import db_session
from toflow.models import NowTodayItem, Project, TodoItem, Track
from toflow.ops.result import Result
from toflow.utils import as_utc_aware


class TodayStore:
    """Persistent queue store for NOW Today."""

    MAX_ITEMS = 5

    def __init__(
        self,
        *,
        min_sessions: int = 1,
        max_sessions: int = 5,
    ) -> None:
        self._min_sessions = min_sessions
        self._max_sessions = max_sessions

    @contextmanager
    def _session_scope(self, session: DBSession | None = None):
        if session is not None:
            yield session
            return
        with db_session() as managed:
            yield managed

    @staticmethod
    def _ordered_rows(session: DBSession) -> list[NowTodayItem]:
        return (
            session.query(NowTodayItem)
            .order_by(NowTodayItem.order_index.asc(), NowTodayItem.todo_id.asc())
            .all()
        )

    @classmethod
    def _reindex_rows(cls, rows: list[NowTodayItem]) -> bool:
        changed = False
        for index, row in enumerate(rows):
            if int(row.order_index) != index:
                row.order_index = index
                changed = True
        return changed

    @classmethod
    def _cleanup_deleted_todos(cls, session: DBSession, rows: list[NowTodayItem]) -> list[NowTodayItem]:
        if not rows:
            return rows
        todo_ids = [int(row.todo_id) for row in rows]
        existing = {
            int(todo_id)
            for (todo_id,) in session.query(TodoItem.id).filter(TodoItem.id.in_(todo_ids)).all()
        }
        missing = [todo_id for todo_id in todo_ids if todo_id not in existing]
        if not missing:
            return rows
        session.query(NowTodayItem).filter(NowTodayItem.todo_id.in_(missing)).delete(
            synchronize_session=False
        )
        return cls._ordered_rows(session)

    @classmethod
    def _normalize_queue(cls, session: DBSession) -> list[NowTodayItem]:
        rows = cls._ordered_rows(session)
        rows = cls._cleanup_deleted_todos(session, rows)
        cls._reindex_rows(rows)
        return rows

    @staticmethod
    def _build_item_maps(
        session: DBSession, todo_ids: list[int]
    ) -> tuple[dict[int, TodoItem], dict[int, Project], dict[int, Track]]:
        todos = session.query(TodoItem).filter(TodoItem.id.in_(todo_ids)).all()
        todo_map = {int(todo.id): todo for todo in todos}

        project_ids = [
            int(todo.parent_id)
            for todo in todos
            if todo.parent_id is not None
        ]
        project_map: dict[int, Project] = {}
        track_map: dict[int, Track] = {}
        if project_ids:
            projects = session.query(Project).filter(Project.id.in_(project_ids)).all()
            project_map = {int(project.id): project for project in projects}
            track_ids = [
                int(project.parent_id)
                for project in projects
                if project.parent_id is not None
            ]
            if track_ids:
                tracks = session.query(Track).filter(Track.id.in_(track_ids)).all()
                track_map = {int(track.id): track for track in tracks}

        return todo_map, project_map, track_map

    @staticmethod
    def _todo_can_enter_today(session: DBSession, todo: TodoItem) -> tuple[bool, str]:
        if todo.archived_at_utc is not None:
            return False, "Todo is archived"
        if str(todo.status or "") != "active":
            return False, "Only active todos can be added"
        if todo.parent_id is None:
            return True, ""

        project = session.get(Project, int(todo.parent_id))
        if project is None or project.archived_at_utc is not None:
            return False, "Project not found"
        if str(project.status or "") != "active":
            return False, "Project must be active"

        if project.parent_id is None:
            return True, ""
        track = session.get(Track, int(project.parent_id))
        if track is None or track.archived_at_utc is not None:
            return False, "Track not found"
        if str(track.status or "") != "active":
            return False, "Track must be active"

        return True, ""

    def in_today_ids(self, *, session: DBSession | None = None) -> set[int]:
        with self._session_scope(session) as s:
            rows = self._normalize_queue(s)
            return {int(row.todo_id) for row in rows}

    def get_items(self, *, session: DBSession | None = None) -> list[dict[str, Any]]:
        with self._session_scope(session) as s:
            rows = self._normalize_queue(s)
            if not rows:
                return []

            todo_ids = [int(row.todo_id) for row in rows]
            todo_map, project_map, track_map = self._build_item_maps(s, todo_ids)

            items: list[dict[str, Any]] = []
            for row in rows:
                todo = todo_map.get(int(row.todo_id))
                if todo is None:
                    continue
                project = project_map.get(int(todo.parent_id)) if todo.parent_id is not None else None
                track = (
                    track_map.get(int(project.parent_id))
                    if project is not None and project.parent_id is not None
                    else None
                )
                planned = int(row.planned_sessions)
                completed = int(row.completed_sessions)
                items.append({
                    "id": int(todo.id),
                    "todo_id": int(todo.id),
                    "title": todo.title,
                    "status": str(todo.status or "active"),
                    "pinned": bool(todo.pinned),
                    "current_stage": int(todo.current_stage or 0),
                    "total_stages": int(todo.total_stages or 1),
                    "deadline_utc": as_utc_aware(todo.deadline_utc),
                    "created_at_utc": as_utc_aware(todo.created_at_utc),
                    "project_id": int(project.id) if project is not None else None,
                    "project_title": project.title if project is not None else "Box",
                    "track_id": int(track.id) if track is not None else None,
                    "track_title": track.title if track is not None else None,
                    "planned_sessions": planned,
                    "completed_sessions": completed,
                    "order_index": int(row.order_index),
                    "is_completed": completed >= planned,
                })
            return items

    def is_full(self, *, session: DBSession | None = None) -> bool:
        with self._session_scope(session) as s:
            rows = self._normalize_queue(s)
            return len(rows) >= self.MAX_ITEMS

    def add_item(
        self,
        todo_id: int,
        *,
        planned_sessions: int = 1,
        session: DBSession | None = None,
    ) -> Result:
        with self._session_scope(session) as s:
            existing = s.get(NowTodayItem, int(todo_id))
            if existing is not None:
                return Result(False, None, "Todo already in Today")

            rows = self._normalize_queue(s)
            if len(rows) >= self.MAX_ITEMS:
                return Result(False, None, "Today already has 5 items")

            todo = s.get(TodoItem, int(todo_id))
            if todo is None:
                return Result(False, None, "Todo not found")

            ok, reason = self._todo_can_enter_today(s, todo)
            if not ok:
                return Result(False, None, reason)

            planned = max(self._min_sessions, min(self._max_sessions, int(planned_sessions)))
            next_index = len(rows)
            s.add(
                NowTodayItem(
                    todo_id=int(todo_id),
                    planned_sessions=planned,
                    completed_sessions=0,
                    order_index=next_index,
                )
            )
            return Result(True, int(todo_id), "Added to Today")

    def remove_item(self, todo_id: int, *, session: DBSession | None = None) -> Result:
        with self._session_scope(session) as s:
            row = s.get(NowTodayItem, int(todo_id))
            if row is None:
                return Result(False, None, "Todo is not in Today")
            s.delete(row)
            self._normalize_queue(s)
            return Result(True, int(todo_id), "Removed from Today")

    def clear_all(self, *, session: DBSession | None = None) -> Result:
        with self._session_scope(session) as s:
            count = s.query(NowTodayItem).delete(synchronize_session=False)
            return Result(True, int(count), "Cleared Today")

    def reorder(self, todo_id: int, direction: int, *, session: DBSession | None = None) -> Result:
        if direction not in (-1, 1):
            return Result(False, None, "direction must be -1 or +1")
        with self._session_scope(session) as s:
            rows = self._normalize_queue(s)
            pos = None
            for index, row in enumerate(rows):
                if int(row.todo_id) == int(todo_id):
                    pos = index
                    break
            if pos is None:
                return Result(False, None, "Todo is not in Today")
            new_pos = pos + direction
            if new_pos < 0 or new_pos >= len(rows):
                return Result(False, None, "Already at boundary")

            rows[pos].order_index, rows[new_pos].order_index = (
                rows[new_pos].order_index,
                rows[pos].order_index,
            )
            self._normalize_queue(s)
            return Result(True, int(todo_id), "Today order updated")

    def adjust_planned(self, todo_id: int, delta: int, *, session: DBSession | None = None) -> Result:
        if delta == 0:
            return Result(True, None, "No change")
        with self._session_scope(session) as s:
            row = s.get(NowTodayItem, int(todo_id))
            if row is None:
                return Result(False, None, "Todo is not in Today")
            planned_now = int(row.planned_sessions)
            completed = int(row.completed_sessions)
            planned_next = max(self._min_sessions, min(self._max_sessions, planned_now + int(delta)))
            if planned_next < completed:
                planned_next = completed
            if planned_next == planned_now:
                return Result(False, None, "Cannot adjust planned sessions")
            row.planned_sessions = planned_next
            return Result(True, int(todo_id), f"Planned sessions: {planned_next}")

    def mark_session_completed(self, todo_id: int, *, session: DBSession | None = None) -> Result:
        with self._session_scope(session) as s:
            row = s.get(NowTodayItem, int(todo_id))
            if row is None:
                return Result(False, None, "Todo is not in Today")

            planned = int(row.planned_sessions)
            completed = int(row.completed_sessions)
            next_completed = min(planned, completed + 1)
            just_finished = completed < planned and next_completed >= planned
            row.completed_sessions = next_completed
            return Result(
                True,
                {
                    "todo_id": int(todo_id),
                    "planned_sessions": planned,
                    "completed_sessions": next_completed,
                    "just_finished": just_finished,
                },
                "Today progress updated",
            )

    def first_unfinished_todo_id(self, *, session: DBSession | None = None) -> int | None:
        items = self.get_items(session=session)
        for item in items:
            if int(item["completed_sessions"]) < int(item["planned_sessions"]):
                return int(item["todo_id"])
        return None

    def next_unfinished_todo_id(
        self, current_todo_id: int, *, session: DBSession | None = None
    ) -> int | None:
        items = self.get_items(session=session)
        start = 0
        for index, item in enumerate(items):
            if int(item["todo_id"]) == int(current_todo_id):
                start = index + 1
                break
        for item in items[start:]:
            if int(item["completed_sessions"]) < int(item["planned_sessions"]):
                return int(item["todo_id"])
        for item in items[:start]:
            if int(item["completed_sessions"]) < int(item["planned_sessions"]):
                return int(item["todo_id"])
        return None
