"""Status operations - set_status."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session as DBSession

from toflow.ops.result import Result
from toflow.registry import EntityType, resolve, supports_protocol


def set_status(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    new_status: str,
) -> Result:
    """Set entity status. Handles unpin, finished_at_utc, stage when switching to done."""
    if not supports_protocol(entity_type, "Statusable"):
        return Result(False, None, f"{entity_type.value} does not support status")

    entity = resolve(session, entity_type, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    allowed = entity.allowed_statuses()
    if new_status not in allowed:
        return Result(False, None, f"Invalid status '{new_status}' for {entity_type.value}")

    title = getattr(entity, "title", str(entity_id))

    # Unpin when not active
    if new_status != "active" and hasattr(entity, "pinned") and entity.pinned:
        entity.pinned = False

    # Todo: done -> set finished_at_utc, current_stage=total_stages
    if entity_type == EntityType.TODO and new_status == "done":
        entity.finished_at_utc = datetime.now(timezone.utc)
        entity.current_stage = entity.total_stages
    elif entity_type == EntityType.TODO and new_status != "done":
        entity.finished_at_utc = None

    # Project/Track: finished has no extra field in v0.2
    entity.status = new_status

    return Result(True, None, f"{entity_type.value} '{title}' set to {new_status}")


def apply_stage_delta(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    stages_completed: int,
) -> Result:
    """Apply stage progress (NOW finish flow). Only TodoItem supports stages.
    Delta can be positive (advance) or negative (go back). Reaching total_stages marks done."""
    if entity_type != EntityType.TODO:
        return Result(False, None, f"{entity_type.value} does not support stage")

    try:
        delta = int(stages_completed)
    except Exception:
        return Result(False, None, "stages_completed must be an integer")

    todo = resolve(session, entity_type, entity_id)
    if not todo:
        return Result(False, None, f"Todo {entity_id} not found")

    total = max(1, int(todo.total_stages or 1))
    cur = max(0, min(int(todo.current_stage or 0), total))
    status_str = str(todo.status or "active")
    title = todo.title

    if status_str == "done":
        cur = total  # treat as at max when done

    if status_str in ("sleeping", "cancelled"):
        todo.status = "active"
        todo.finished_at_utc = None

    nxt = cur + delta
    if nxt >= total:
        return set_stage(session, entity_type, entity_id, current_stage=total, total_stages=total)

    # nxt < total: stay active, clamp to [0, total-1]
    new_stage = max(0, min(nxt, total - 1))
    return set_stage(session, entity_type, entity_id, current_stage=new_stage, total_stages=total)


def set_stage(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    *,
    current_stage: int,
    total_stages: int,
) -> Result:
    """Set Todo stage fields and keep status/finished_at_utc consistent.

    Rules:
    - total_stages >= 1
    - current_stage >= 0
    - if current_stage > total_stages, raise total_stages to current_stage
    - if current_stage == total_stages, mark done
    - otherwise, done -> active
    """
    if entity_type != EntityType.TODO:
        return Result(False, None, f"{entity_type.value} does not support stage")

    todo = resolve(session, entity_type, entity_id)
    if not todo:
        return Result(False, None, f"Todo {entity_id} not found")

    try:
        cur = max(0, int(current_stage))
        total = max(1, int(total_stages))
    except Exception:
        return Result(False, None, "current_stage and total_stages must be integers")

    if cur > total:
        total = cur

    todo.current_stage = cur
    todo.total_stages = total

    if cur == total:
        todo.status = "done"
        todo.finished_at_utc = datetime.now(timezone.utc)
        if hasattr(todo, "pinned") and todo.pinned:
            todo.pinned = False
        return Result(True, None, f"Todo '{todo.title}' marked as done ({cur}/{total})")

    if str(todo.status or "") == "done":
        todo.status = "active"
        todo.finished_at_utc = None

    return Result(True, None, f"Todo '{todo.title}' progress {cur}/{total}")
