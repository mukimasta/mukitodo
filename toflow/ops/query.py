"""Query operations - get, list entities."""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from toflow.models import Project, Session as SessionModel, Track, TodoItem
from toflow.ops.result import Result
from toflow.registry import EntityType, get_model_class, get_parent_field, resolve, supports_protocol
from toflow.utils import as_utc_aware


def _entity_to_dict(entity: Any) -> dict:
    """Convert ORM entity to dict. Adds archived only for entities with archived_at_utc."""
    d = {}
    for col in entity.__table__.columns:
        val = getattr(entity, col.key, None)
        if isinstance(val, datetime):
            val = as_utc_aware(val)
        d[col.key] = val
    if hasattr(entity, "archived_at_utc"):
        d["archived"] = getattr(entity, "archived_at_utc", None) is not None
    return d


def get_entity(session: DBSession, entity_type: EntityType, entity_id: int) -> Any | None:
    """Resolve ORM instance. Returns None if not found."""
    return resolve(session, entity_type, entity_id)


def list_entities(
    session: DBSession,
    entity_type: EntityType,
    *,
    parent_id: int | None = None,
    include_archived: bool = False,
) -> Result:
    """List entities. Result.data: list[dict]. parent_id filters by parent (parent_id column for Project, TodoItem)."""
    model_cls = get_model_class(entity_type)
    parent_field = get_parent_field(entity_type)

    q = session.query(model_cls)
    if parent_field is not None:
        if parent_id is None:
            q = q.filter(getattr(model_cls, parent_field).is_(None))  # Box items
        else:
            q = q.filter(getattr(model_cls, parent_field) == parent_id)
    if supports_protocol(entity_type, "Archivable") and not include_archived:
        q = q.filter(getattr(model_cls, "archived_at_utc").is_(None))

    order_col = getattr(model_cls, "order_index", None)
    if order_col is not None:
        q = q.order_by(order_col.asc().nulls_last(), model_cls.id)
    items = q.all()
    data = [_entity_to_dict(it) for it in items]
    if entity_type == EntityType.TODO:
        _attach_todo_session_minutes(session, data)
    elif entity_type == EntityType.PROJECT:
        _attach_project_session_minutes(session, data)
    return Result(True, data, f"Found {len(data)} {entity_type.value}s")


def list_tracks_with_projects(session: DBSession) -> Result:
    """List tracks with their projects for TWP view. Result.data: list[(track_dict, list[project_dict])]."""
    tracks_result = list_entities(
        session,
        EntityType.TRACK,
        include_archived=False,
    )
    if not tracks_result.success or not tracks_result.data:
        return Result(True, [], "No tracks")
    tracks = tracks_result.data
    out = []
    for t in tracks:
        tid = t["id"]
        projs_result = list_entities(
            session,
            EntityType.PROJECT,
            parent_id=tid,
            include_archived=False,
        )
        projs = projs_result.data if projs_result.success else []
        out.append((t, projs))
    return Result(True, out, f"Found {len(out)} tracks with projects")


def list_archived_structure(session: DBSession) -> Result:
    """List archived items. Result.data: {tracks: [...], box_projects: [...], box_todos: [...]}."""
    tracks_result = list_entities(
        session, EntityType.TRACK, include_archived=True
    )
    if not tracks_result.success:
        return tracks_result
    all_tracks = tracks_result.data or []

    tracks_out = []
    for t in all_tracks:
        is_archived = t.get("archived", False)
        projs_result = list_entities(
            session,
            EntityType.PROJECT,
            parent_id=t["id"],
            include_archived=True,
        )
        projects = projs_result.data if projs_result.success else []
        projects_out = []
        for p in projects:
            p_archived = p.get("archived", False)
            todos_result = list_entities(
                session,
                EntityType.TODO,
                parent_id=p["id"],
                include_archived=True,
            )
            all_todos = todos_result.data if todos_result.success else []
            archived_todos = [d for d in all_todos if d.get("archived", False)]
            if p_archived or archived_todos:
                projects_out.append({
                    "project": p,
                    "is_archived": p_archived,
                    "todos": archived_todos,
                })
        if is_archived or projects_out:
            tracks_out.append({
                "track": t,
                "is_archived": is_archived,
                "projects": projects_out,
            })

    box_projs_result = list_entities(
        session,
        EntityType.PROJECT,
        parent_id=None,
        include_archived=True,
    )
    box_projects = box_projs_result.data if box_projs_result.success else []
    box_projects = [d for d in box_projects if d.get("archived", False)]

    box_todos_result = list_entities(
        session,
        EntityType.TODO,
        parent_id=None,
        include_archived=True,
    )
    box_todos = box_todos_result.data if box_todos_result.success else []
    box_todos = [d for d in box_todos if d.get("archived", False)]

    data = {
        "tracks": tracks_out,
        "box_projects": box_projects,
        "box_todos": box_todos,
    }
    return Result(
        True,
        data,
        f"Found {len(tracks_out)} tracks, {len(box_projects)} box projects, {len(box_todos)} box todos",
    )


def list_timeline_records(
    session: DBSession,
    limit: int | None = None,
) -> Result:
    """List completed sessions for Timeline. Result.data: list[dict] with parent_info."""
    q = (
        session.query(SessionModel)
        .filter(SessionModel.ended_at_utc.isnot(None))
        .order_by(SessionModel.ended_at_utc.desc())
    )
    if limit is not None:
        q = q.limit(limit)
    sessions = q.all()
    out = []
    for s in sessions:
        d = _entity_to_dict(s)
        todo = session.get(TodoItem, s.todo_item_id) if s.todo_item_id else None
        parts = []
        if todo:
            parts.append(todo.title)
            if todo.parent_id:
                proj = session.get(Project, todo.parent_id)
                if proj:
                    parts.insert(0, proj.title)
                    if proj.parent_id:
                        track = session.get(Track, proj.parent_id)
                        if track:
                            parts.insert(0, track.title)
        d["parent_info"] = "/".join(parts) if parts else "Unknown"
        out.append(d)
    return Result(True, out, f"Found {len(out)} sessions")


def _attach_todo_session_minutes(session: DBSession, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    todo_ids = [int(row["id"]) for row in rows if row.get("id") is not None]
    if not todo_ids:
        return

    sums = (
        session.query(
            SessionModel.todo_item_id,
            func.coalesce(func.sum(SessionModel.duration_minutes), 0),
        )
        .filter(SessionModel.todo_item_id.in_(todo_ids))
        .group_by(SessionModel.todo_item_id)
        .all()
    )
    totals = {int(todo_id): int(total_minutes or 0) for todo_id, total_minutes in sums}
    for row in rows:
        entity_id = row.get("id")
        if entity_id is None:
            row["session_total_minutes"] = 0
            continue
        minutes = totals.get(int(entity_id), 0)
        row["session_total_minutes"] = int(minutes)


def _attach_project_session_minutes(session: DBSession, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    project_ids = [int(row["id"]) for row in rows if row.get("id") is not None]
    if not project_ids:
        return

    sums = (
        session.query(
            TodoItem.parent_id,
            func.coalesce(func.sum(SessionModel.duration_minutes), 0),
        )
        .select_from(TodoItem)
        .outerjoin(SessionModel, SessionModel.todo_item_id == TodoItem.id)
        .filter(TodoItem.parent_id.in_(project_ids))
        .group_by(TodoItem.parent_id)
        .all()
    )
    totals = {int(project_id): int(total_minutes or 0) for project_id, total_minutes in sums if project_id is not None}
    for row in rows:
        entity_id = row.get("id")
        if entity_id is None:
            row["session_total_minutes"] = 0
            continue
        minutes = totals.get(int(entity_id), 0)
        row["session_total_minutes"] = int(minutes)
