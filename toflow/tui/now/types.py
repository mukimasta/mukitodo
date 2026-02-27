"""NOW typed enums and dicts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TypedDict


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class TimerMode(str, Enum):
    WORK = "work"
    REST = "rest"


class TimerEvent(str, Enum):
    WORK_5MIN_LEFT = "work_5min_left"
    WORK_TIME_UP = "work_time_up"
    REST_TIME_UP = "rest_time_up"


class PromodoroPhase(str, Enum):
    FOCUS_WAIT = "focus_wait"
    FOCUS_RUN = "focus_run"
    FOCUS_PAUSED = "focus_paused"
    REFLECT = "reflect"
    REFLECT_NOTE = "reflect_note"
    REST_RUN = "rest_run"
    REST_PAUSED = "rest_paused"


class SuggestionItem(TypedDict):
    id: int
    title: str
    project_title: str | None
    track_title: str | None
    pinned: bool
    deadline_utc: datetime | None
    created_at_utc: datetime | None
    current_stage: int
    total_stages: int
    project_pinned: bool
    project_willingness_hint: int
    project_importance_hint: int
    project_urgency_hint: int
    has_recent_session: bool
    score: float
    reason_tags: list[str]
    in_today: bool
    can_add: bool
