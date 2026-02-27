"""View-layer item TypedDicts — canonical shapes for data flowing through panes and formatters."""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict

from toflow.registry import EntityType


class TrackItem(TypedDict):
    id: int
    title: str
    status: str


class ProjectItem(TypedDict):
    id: int
    title: str
    status: str
    pinned: bool
    parent_id: int | None
    description: NotRequired[str | None]
    deadline_utc: NotRequired[datetime | None]
    willingness_hint: NotRequired[int | None]
    importance_hint: NotRequired[int | None]
    urgency_hint: NotRequired[int | None]
    session_total_minutes: NotRequired[int]


class TodoViewItem(TypedDict):
    id: int
    title: str
    status: str
    pinned: bool
    current_stage: int
    total_stages: int
    description: NotRequired[str | None]
    url: NotRequired[str | None]
    deadline_utc: NotRequired[datetime | None]
    session_total_minutes: NotRequired[int]


class ArchiveRow(TypedDict):
    id: int
    kind: str
    entity_type: EntityType
    archived: bool
    status: str
    title: str
    depth: int
    pinned: NotRequired[bool]
    current_stage: NotRequired[int]
    total_stages: NotRequired[int]
    description: NotRequired[str | None]
    url: NotRequired[str | None]
    deadline_utc: NotRequired[datetime | None]
    willingness_hint: NotRequired[int | None]
    importance_hint: NotRequired[int | None]
    urgency_hint: NotRequired[int | None]
    session_total_minutes: NotRequired[int]


class TimelineRow(TypedDict, total=False):
    """Union-like row for timeline: date_header or session."""

    kind: str
    id: int | None
    date_label: str
    ended_at_utc: datetime | None
    started_at_utc: datetime | None
    duration_minutes: int | None
    parent_info: str | None
    description: str | None
