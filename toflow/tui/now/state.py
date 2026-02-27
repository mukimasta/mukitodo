"""NOW aggregate state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from toflow.ops.result import Result
from toflow.ops.today import TodayStore
from toflow.tui.now.config import TODAY_MAX_SESSIONS, TODAY_MIN_SESSIONS
from toflow.tui.now.suggestion import SuggestionEngine
from toflow.tui.now.timer import TimerService
from toflow.tui.now.types import PromodoroPhase, TimerEvent
from toflow.tui.now.view_promodoro import PromodoroView
from toflow.tui.now.view_suggestion import SuggestionView
from toflow.tui.now.view_today import TodayView
from toflow.tui.view.base import View


@dataclass(frozen=True)
class ConfirmRequest:
    action: Callable[[], Result | None]
    trigger_key: str


class NowState:
    """Encapsulated NOW state and view routing."""

    def __init__(
        self,
        *,
        today_store: TodayStore | None = None,
        timer_service: TimerService | None = None,
        suggestion_engine: SuggestionEngine | None = None,
    ) -> None:
        self.today_store = today_store or TodayStore(
            min_sessions=TODAY_MIN_SESSIONS,
            max_sessions=TODAY_MAX_SESSIONS,
        )
        self.timer_service = timer_service or TimerService()
        self.suggestion_engine = suggestion_engine or SuggestionEngine()

        self.current: Literal["today", "suggestion", "promodoro"] = "today"
        self.show_today_panel: bool = False

        self.today = TodayView(self, store=self.today_store)
        self.suggestion = SuggestionView(
            self,
            today_store=self.today_store,
            engine=self.suggestion_engine,
        )
        self.promodoro = PromodoroView(
            self,
            today_store=self.today_store,
            timer=self.timer_service,
        )

        self.enter_default_view()

    def view(self) -> View:
        if self.show_today_panel:
            return self.today
        if self.current == "suggestion":
            return self.suggestion
        if self.current == "promodoro":
            return self.promodoro
        return self.today

    def enter_default_view(self) -> None:
        self.today.load_data()
        if self.today_store.get_items():
            self.current = "today"
        else:
            self.current = "suggestion"
            self.suggestion.load_data()

    def resume_promodoro_if_active(self) -> bool:
        if not self.promodoro.has_active_context():
            return False
        self.current = "promodoro"
        self.show_today_panel = False
        self.promodoro.load_data()
        return True

    def refresh(self) -> None:
        self.today.load_data()
        self.suggestion.load_data()
        self.promodoro.load_data()

    def add_todo_from_external(self, todo_id: int) -> Result:
        result = self.today.add_todo(todo_id)
        self.suggestion.load_data()
        return result

    def timer_tick(self) -> list[TimerEvent]:
        return self.promodoro.timer_tick()

    def is_note_input(self) -> bool:
        return self.promodoro.phase == PromodoroPhase.REFLECT_NOTE

    def toggle_today_panel(self) -> None:
        self.show_today_panel = not self.show_today_panel

    def handle_note_key(self, key: str, char: str | None) -> Result | None:
        if not self.is_note_input():
            return None
        normalized = {"c-m": "enter", "c-h": "backspace"}.get(key, key)
        if normalized == "enter":
            return self.promodoro.save_reflect_and_start_rest()
        if normalized == "escape":
            return self.promodoro.close_note()
        if normalized == "backspace":
            self.promodoro.backspace_note()
            return None
        if char and len(char) == 1 and char.isprintable():
            self.promodoro.append_note_char(char)
        return None

    def consume_note_backspace(self) -> bool:
        if not self.is_note_input():
            return False
        self.promodoro.backspace_note()
        return True

    def close_note_if_open(self) -> Result | None:
        if not self.is_note_input():
            return None
        return self.promodoro.close_note()

    def adjust_current(self, direction: int) -> Result | None:
        view = self.view()
        if isinstance(view, TodayView):
            return view.session_delta(direction)
        if isinstance(view, PromodoroView):
            if view.phase in (PromodoroPhase.REFLECT, PromodoroPhase.REFLECT_NOTE):
                return view.adjust_reflect_stage(direction)
            return view.adjust_time(direction)
        return None

    def open_note(self) -> Result | None:
        view = self.view()
        if isinstance(view, PromodoroView):
            return view.open_note()
        return None

    def reset_confirm_request(self) -> ConfirmRequest | None:
        view = self.view()
        if isinstance(view, TodayView):
            return ConfirmRequest(action=view.clear_all, trigger_key="r")
        if isinstance(view, PromodoroView) and view.phase in (
            PromodoroPhase.FOCUS_WAIT,
            PromodoroPhase.FOCUS_RUN,
            PromodoroPhase.FOCUS_PAUSED,
        ):
            return ConfirmRequest(action=view.reset_focus, trigger_key="r")
        return None

    def handle_timer_event(self, event: TimerEvent) -> Result | None:
        result = self.promodoro.handle_timer_event(event)
        if event in (TimerEvent.WORK_TIME_UP, TimerEvent.REST_TIME_UP):
            self.refresh()
        return result
