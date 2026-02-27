"""Archive operations - set_archived."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from toflow.ops.result import Result
from toflow.registry import (
    EntityType,
    get_child_type,
    get_model_class,
    get_parent_field,
    resolve,
    supports_protocol,
)


def _set_archived_cascade(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    archived: bool,
    archived_at_utc: datetime | None = None,
) -> None:
    """Set archived flag for entity and all descendants recursively."""
    entity = resolve(session, entity_type, entity_id)
    if entity is None:
        return

    if archived:
        # Keep existing archived timestamp if already archived.
        if getattr(entity, "archived_at_utc", None) is None:
            entity.archived_at_utc = archived_at_utc
        if hasattr(entity, "pinned") and entity.pinned:
            entity.pinned = False
    else:
        entity.archived_at_utc = None

    child_type = get_child_type(entity_type)
    if child_type is None:
        return
    parent_field = get_parent_field(child_type)
    if parent_field is None:
        return

    child_model = get_model_class(child_type)
    children = session.query(child_model).filter(
        getattr(child_model, parent_field) == entity_id
    ).all()
    for child in children:
        _set_archived_cascade(
            session,
            child_type,
            int(child.id),
            archived=archived,
            archived_at_utc=archived_at_utc,
        )


def set_archived(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    archived: bool,
) -> Result:
    """Set entity archived state. Unpins when archiving."""
    if not supports_protocol(entity_type, "Archivable"):
        return Result(False, None, f"{entity_type.value} does not support archive")

    entity = resolve(session, entity_type, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    title = getattr(entity, "title", str(entity_id))
    if archived:
        archived_at = datetime.now(timezone.utc)
        _set_archived_cascade(
            session,
            entity_type,
            entity_id,
            archived=True,
            archived_at_utc=archived_at,
        )
        return Result(True, None, f"{entity_type.value} '{title}' archived")
    _set_archived_cascade(session, entity_type, entity_id, archived=False)
    return Result(True, None, f"{entity_type.value} '{title}' unarchived")
