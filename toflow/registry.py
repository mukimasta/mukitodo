"""Entity type registry. EntityType enum and minimal mapping."""

from enum import Enum
from typing import Any, Callable

from sqlalchemy.orm import Session as SASession

from toflow.models import Track, Project, TodoItem, Session


class EntityType(str, Enum):
    TRACK = "track"
    PROJECT = "project"
    TODO = "todo"
    SESSION = "session"


MODELS = {
    EntityType.TRACK: Track,
    EntityType.PROJECT: Project,
    EntityType.TODO: TodoItem,
    EntityType.SESSION: Session,
}

PARENT_OF = {
    EntityType.PROJECT: EntityType.TRACK,
    EntityType.TODO: EntityType.PROJECT,
}

# Parent -> child. Used for cascade delete: delete children before parent.
CHILDREN_OF = {parent: child for child, parent in PARENT_OF.items()}

# Entities that reference this entity via FK (non-parent_id). Delete these before self.
# Format: (model_cls, fk_column_name)
REFERENCED_BY: dict[EntityType, list[tuple[type, str]]] = {
    EntityType.TODO: [(Session, "todo_item_id")],
    EntityType.TRACK: [],
    EntityType.PROJECT: [],
    EntityType.SESSION: [],
}


def get_model_class(entity_type: EntityType) -> type:
    """Return ORM model class for entity type."""
    model = MODELS.get(entity_type)
    if model is None:
        raise ValueError(f"Unknown entity type: {entity_type}")
    return model


def resolve(session: SASession, entity_type: EntityType, entity_id: int) -> Any | None:
    """Resolve ORM instance by entity_type and entity_id. Returns None if not found."""
    return session.get(get_model_class(entity_type), entity_id)


def get_parent_type(entity_type: EntityType) -> EntityType | None:
    """Return parent entity type. Returns None if no parent."""
    return PARENT_OF.get(entity_type)


def get_parent_field(entity_type: EntityType) -> str | None:
    """Return parent id column name. Returns None if no parent. Unified as parent_id for Project, TodoItem."""
    return "parent_id" if entity_type in PARENT_OF else None


def get_child_type(entity_type: EntityType) -> EntityType | None:
    """Return child entity type. None if no children."""
    return CHILDREN_OF.get(entity_type)


def get_referrers(entity_type: EntityType) -> list[tuple[type, str]]:
    """Return (model_cls, fk_column) for entities that reference this type."""
    return REFERENCED_BY.get(entity_type, [])


PROTOCOL_CHECKS: dict[str, Callable[[type], bool]] = {
    "Archivable": lambda m: hasattr(m, "archived_at_utc"),
    "Orderable": lambda m: hasattr(m, "order_index"),
    "Statusable": lambda m: hasattr(m, "allowed_statuses"),
    "Parentable": lambda m: hasattr(m, "parent_id"),
    "Pinnable": lambda m: hasattr(m, "pinned"),
}


def supports_protocol(entity_type: EntityType, protocol_name: str) -> bool:
    """Check if entity type supports the given protocol (duck-typed via model)."""
    model = MODELS.get(entity_type)
    if model is None:
        return False
    check = PROTOCOL_CHECKS.get(protocol_name)
    return check(model) if check else False
