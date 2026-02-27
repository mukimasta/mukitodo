"""Move operations - reorder, reparent."""

from typing import Any

from sqlalchemy.orm import Session as DBSession

from toflow.ops.crud import next_order_index
from toflow.ops.result import Result
from toflow.registry import (
    EntityType,
    get_model_class,
    get_parent_field,
    get_parent_type,
    resolve,
    supports_protocol,
)


def _normalize_order_index(items: list[Any]) -> None:
    """Fill gaps in order_index (0,1,2,...) for in-memory sibling list."""
    for idx, it in enumerate(items):
        if getattr(it, "order_index", None) != idx:
            it.order_index = idx


def _swap_order_index_in_list(
    *,
    items: list[Any],
    item_id: int,
    direction: int,
) -> tuple[bool, str]:
    if direction not in (-1, 1):
        return (False, "direction must be -1 or +1")
    pos = None
    for i, it in enumerate(items):
        if int(getattr(it, "id")) == int(item_id):
            pos = i
            break
    if pos is None:
        return (False, "Item not found")
    nxt = pos + direction
    if nxt < 0 or nxt >= len(items):
        return (False, "Already at boundary")
    a, b = items[pos], items[nxt]
    a.order_index, b.order_index = b.order_index, a.order_index
    return (True, "OK")


def _find_swap_indices(
    *,
    items: list[Any],
    item_id: int,
    direction: int,
) -> tuple[bool, str, int | None, int | None]:
    """Find source/target indices for a move without mutating ORM objects."""
    if direction not in (-1, 1):
        return (False, "direction must be -1 or +1", None, None)
    pos = None
    for i, it in enumerate(items):
        if int(getattr(it, "id")) == int(item_id):
            pos = i
            break
    if pos is None:
        return (False, "Item not found", None, None)
    nxt = pos + direction
    if nxt < 0 or nxt >= len(items):
        return (False, "Already at boundary", None, None)
    return (True, "OK", pos, nxt)


def reorder(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    direction: int,
) -> Result:
    """Swap order with neighbor. direction: -1 up, +1 down."""
    if not supports_protocol(entity_type, "Orderable"):
        return Result(False, None, f"{entity_type.value} does not support reorder")

    model_cls = get_model_class(entity_type)
    entity = resolve(session, entity_type, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    parent_field = get_parent_field(entity_type)
    parent_id = getattr(entity, parent_field, None) if parent_field is not None else None

    q = session.query(model_cls)
    if parent_field is not None:
        q = q.filter(getattr(model_cls, parent_field) == parent_id)
    if hasattr(model_cls, "archived_at_utc"):
        q = q.filter(getattr(model_cls, "archived_at_utc").is_(None))

    items = q.order_by(
        getattr(model_cls, "order_index").asc().nulls_last(),
        model_cls.id,
    ).all()
    ok, reason, pos, nxt = _find_swap_indices(
        items=items,
        item_id=entity_id,
        direction=direction,
    )
    if not ok:
        return Result(False, None, reason)

    # Only normalize when a move is actually valid; failed moves should be side-effect free.
    _normalize_order_index(items)
    assert pos is not None and nxt is not None
    a, b = items[pos], items[nxt]
    a.order_index, b.order_index = b.order_index, a.order_index
    return Result(True, None, f"{entity_type.value} moved")


def reparent(
    session: DBSession,
    entity_type: EntityType,
    entity_id: int,
    new_parent_id: int,
) -> Result:
    """Move entity to new parent (project to track, todo to project)."""
    if not supports_protocol(entity_type, "Parentable"):
        return Result(False, None, f"{entity_type.value} does not support reparent")

    entity = resolve(session, entity_type, entity_id)
    if not entity:
        return Result(False, None, f"{entity_type.value} {entity_id} not found")

    pf = get_parent_field(entity_type)
    parent_type = get_parent_type(entity_type)
    if not parent_type:
        return Result(False, None, "Entity has no parent")

    parent_model = get_model_class(parent_type)
    parent = session.get(parent_model, new_parent_id)
    if not parent:
        return Result(False, None, f"Parent {new_parent_id} not found")

    setattr(entity, pf, new_parent_id)
    if hasattr(entity, "order_index"):
        entity.order_index = next_order_index(session, entity_type, new_parent_id)
    title = getattr(entity, "title", str(entity_id))
    return Result(True, None, f"{entity_type.value} '{title}' moved")
