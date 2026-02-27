"""Pin operations - set_pinned."""

from sqlalchemy.orm import Session as DBSession

from toflow.ops.result import Result
from toflow.registry import EntityType, resolve, supports_protocol


def set_pinned(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    pinned: bool,
) -> Result:
    """Set entity pinned state. Only Project and TodoItem support pinned. pinned requires status='active'."""
    if not supports_protocol(entity_type, "Pinnable"):
        return Result(False, None, f"{entity_type.value} does not support pin")

    entity = resolve(session, entity_type, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    title = getattr(entity, "title", str(entity_id))

    if pinned and getattr(entity, "status", "active") != "active":
        return Result(False, None, f"Can only pin when status is active (current: {entity.status})")

    entity.pinned = pinned
    action = "pinned" if pinned else "unpinned"
    return Result(True, None, f"{entity_type.value} '{title}' {action}")
