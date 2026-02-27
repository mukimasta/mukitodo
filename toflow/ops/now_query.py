"""NOW-specific query helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from toflow.models import Project, Session as SessionModel, TodoItem, Track
from toflow.ops.result import Result
from toflow.utils import as_utc_aware


def _recent_session_todo_ids(session: DBSession, *, days: int = 7) -> set[int]:
    if days <= 0:
        return set()
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        session.query(SessionModel.todo_item_id)
        .filter(SessionModel.todo_item_id.isnot(None))
        .filter(SessionModel.started_at_utc >= threshold)
        .distinct()
        .all()
    )
    return {int(todo_id) for (todo_id,) in rows if todo_id is not None}


def list_suggestion_candidates(session: DBSession) -> Result:
    """List todos eligible for NOW suggestion scoring."""
    todos = (
        session.query(TodoItem)
        .filter(TodoItem.archived_at_utc.is_(None))
        .filter(TodoItem.status == "active")
        .all()
    )
    if not todos:
        return Result(True, [], "No suggestion candidates")

    project_ids = [int(todo.parent_id) for todo in todos if todo.parent_id is not None]
    projects: dict[int, Project] = {}
    tracks: dict[int, Track] = {}
    if project_ids:
        project_rows = session.query(Project).filter(Project.id.in_(project_ids)).all()
        projects = {int(project.id): project for project in project_rows}
        track_ids = [
            int(project.parent_id)
            for project in project_rows
            if project.parent_id is not None
        ]
        if track_ids:
            track_rows = session.query(Track).filter(Track.id.in_(track_ids)).all()
            tracks = {int(track.id): track for track in track_rows}

    recent_ids = _recent_session_todo_ids(session, days=7)
    out: list[dict[str, Any]] = []
    for todo in todos:
        project = projects.get(int(todo.parent_id)) if todo.parent_id is not None else None
        track = None
        if project is not None and project.parent_id is not None:
            track = tracks.get(int(project.parent_id))

        if project is not None:
            if project.archived_at_utc is not None or str(project.status or "") != "active":
                continue
            if project.parent_id is not None:
                if track is None:
                    continue
                if track.archived_at_utc is not None or str(track.status or "") != "active":
                    continue

        out.append({
            "id": int(todo.id),
            "title": todo.title,
            "status": str(todo.status or "active"),
            "pinned": bool(todo.pinned),
            "deadline_utc": as_utc_aware(todo.deadline_utc),
            "created_at_utc": as_utc_aware(todo.created_at_utc),
            "current_stage": int(todo.current_stage or 0),
            "total_stages": int(todo.total_stages or 1),
            "parent_id": int(todo.parent_id) if todo.parent_id is not None else None,
            "project_id": int(project.id) if project is not None else None,
            "project_title": project.title if project is not None else None,
            "project_pinned": bool(project.pinned) if project is not None else False,
            "project_willingness_hint": (
                int(project.willingness_hint)
                if project is not None and project.willingness_hint is not None
                else 0
            ),
            "project_importance_hint": (
                int(project.importance_hint)
                if project is not None and project.importance_hint is not None
                else 0
            ),
            "project_urgency_hint": (
                int(project.urgency_hint)
                if project is not None and project.urgency_hint is not None
                else 0
            ),
            "track_id": int(track.id) if track is not None else None,
            "track_title": track.title if track is not None else None,
            "has_recent_session": int(todo.id) in recent_ids,
        })

    return Result(True, out, f"Found {len(out)} suggestion candidates")
