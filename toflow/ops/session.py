"""Session operations - save, delete, update_description."""

from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from toflow.ops.crud import create_entity, delete_entity, update_entity
from toflow.ops.result import Result
from toflow.registry import EntityType


def save_session(
    session: DBSession,
    todo_item_id: int,
    duration_minutes: int,
    started_at_utc: datetime,
    ended_at_utc: datetime | None = None,
    title: str | None = None,
    description: str | None = None,
) -> Result:
    """Save a session. Result.data: session id. Uses create_entity for consistency."""
    return create_entity(
        session,
        EntityType.SESSION,
        todo_item_id=todo_item_id,
        duration_minutes=duration_minutes,
        started_at_utc=started_at_utc,
        ended_at_utc=ended_at_utc,
        title=(title or "").strip() or None,
        description=(description or "").strip() or None,
    )


def delete_session(session: DBSession, session_id: int) -> Result:
    """Delete session by id. Wrapper around delete_entity(session, EntityType.SESSION, session_id)."""
    return delete_entity(session, EntityType.SESSION, session_id)


def update_session_description(
    session: DBSession,
    session_id: int,
    description: str | None,
) -> Result:
    """Update session description. Wrapper around update_entity(session, EntityType.SESSION, session_id, description=...)."""
    cleaned = (description or "").strip() or None
    return update_entity(session, EntityType.SESSION, session_id, description=cleaned)
