"""Ops layer - medium granularity business operations."""

from toflow.ops.archive import set_archived
from toflow.ops.crud import create_entity, delete_entity, update_entity
from toflow.ops.move import reparent, reorder
from toflow.ops.now_query import list_suggestion_candidates
from toflow.ops.pin import set_pinned
from toflow.ops.query import (
    get_entity,
    list_archived_structure,
    list_entities,
    list_timeline_records,
    list_tracks_with_projects,
)
from toflow.ops.result import EmptyResult, Result
from toflow.ops.session import delete_session, save_session, update_session_description
from toflow.ops.status import apply_stage_delta, set_stage, set_status
from toflow.ops.today import TodayStore

__all__ = [
    "Result",
    "EmptyResult",
    "create_entity",
    "update_entity",
    "delete_entity",
    "get_entity",
    "list_entities",
    "list_tracks_with_projects",
    "list_archived_structure",
    "list_timeline_records",
    "set_status",
    "apply_stage_delta",
    "set_stage",
    "set_archived",
    "set_pinned",
    "reorder",
    "reparent",
    "save_session",
    "delete_session",
    "update_session_description",
    "TodayStore",
    "list_suggestion_candidates",
]
