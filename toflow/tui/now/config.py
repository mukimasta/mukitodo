"""Configuration constants for NOW."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestionWeights:
    pinned: float = 100.0
    deadline_max: float = 40.0
    project_hints_max: float = 30.0
    stage_progress_max: float = 15.0
    momentum: float = 10.0
    freshness_max: float = 5.0


SUGGESTION_MAX_ITEMS = 10
TODAY_MAX_ITEMS = 5

TODAY_MIN_SESSIONS = 1
TODAY_MAX_SESSIONS = 8

FOCUS_MINUTES_DEFAULT = 25
FOCUS_MINUTES_MIN = 5
FOCUS_MINUTES_MAX = 60
FOCUS_ADJUST_STEP_MINUTES = 5

REST_MINUTES_DEFAULT = 5
REST_MINUTES_MIN = 5
REST_MINUTES_MAX = 60
REST_ADJUST_STEP_MINUTES = 5
