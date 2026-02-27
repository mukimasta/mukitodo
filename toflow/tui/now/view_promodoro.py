"""Promodoro view for Focus / Reflect / Rest."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from toflow.database import db_session
from toflow.ops import apply_stage_delta, save_session
from toflow.ops.result import Result
from toflow.ops.today import TodayStore
from toflow.registry import EntityType
from toflow.tui.now.config import (
    FOCUS_ADJUST_STEP_MINUTES,
    FOCUS_MINUTES_DEFAULT,
    FOCUS_MINUTES_MAX,
    FOCUS_MINUTES_MIN,
    REST_ADJUST_STEP_MINUTES,
    REST_MINUTES_DEFAULT,
    REST_MINUTES_MAX,
    REST_MINUTES_MIN,
)
from toflow.tui.now.timer import TimerService
from toflow.tui.now.types import PromodoroPhase, TimerEvent, TimerMode, TimerState
from toflow.tui.pane.session import SessionPane
from toflow.tui.view.base import View

if TYPE_CHECKING:
    from toflow.tui.now.state import NowState
    from toflow.tui.state import AppState


def _format_mmss(seconds: int) -> str:
    total = max(0, int(seconds))
    minutes = total // 60
    sec = total % 60
    return f"{minutes:02d}:{sec:02d}"


class PromodoroView(View):
    title = ""
    status_hint = "[Space] start/pause  [Enter] confirm/finish  [Backspace] cancel  [r] reset  [+/-] adjust  [t] today panel"
    entity_type = EntityType.TODO

    def __init__(self, now: NowState, *, today_store: TodayStore, timer: TimerService) -> None:
        self._now = now
        self._today_store = today_store
        self._timer = timer

        self.phase = PromodoroPhase.FOCUS_WAIT

        self._current_todo_id: int | None = None
        self._current_item: dict[str, Any] | None = None

        self._focus_minutes = FOCUS_MINUTES_DEFAULT
        self._rest_minutes = REST_MINUTES_DEFAULT
        self._session_started_at_utc: datetime | None = None

        self._reflect_stage_delta = 0
        self._reflect_note = ""
        self._reflect_base_stage = 0
        self._reflect_total_stages = 1

        self._pane = SessionPane(
            render_fn=self._render_lines,
            selected_id_fn=lambda: self._current_todo_id,
            selected_item_fn=self._selected_item,
        )

    @property
    def pane(self) -> SessionPane:
        return self._pane

    @property
    def timer(self) -> TimerService:
        return self._timer

    def load_data(self) -> None:
        if self._current_todo_id is None:
            self._current_item = None
            return
        for item in self._today_store.get_items():
            if int(item["todo_id"]) == int(self._current_todo_id):
                self._current_item = item
                return
        self._current_item = None

    def _selected_item(self) -> dict[str, Any] | None:
        return self._current_item

    def current_todo_id(self) -> int | None:
        return self._current_todo_id

    def has_active_context(self) -> bool:
        if self._current_todo_id is None:
            return False
        return self.phase in (
            PromodoroPhase.FOCUS_WAIT,
            PromodoroPhase.FOCUS_RUN,
            PromodoroPhase.FOCUS_PAUSED,
            PromodoroPhase.REFLECT,
            PromodoroPhase.REFLECT_NOTE,
            PromodoroPhase.REST_RUN,
            PromodoroPhase.REST_PAUSED,
        )

    def is_focus_phase(self) -> bool:
        return self.phase in (
            PromodoroPhase.FOCUS_WAIT,
            PromodoroPhase.FOCUS_RUN,
            PromodoroPhase.FOCUS_PAUSED,
        )

    def enter_focus(self, todo_id: int) -> Result:
        self.load_data()
        item = None
        for candidate in self._today_store.get_items():
            if int(candidate["todo_id"]) == int(todo_id):
                item = candidate
                break
        if item is None:
            return Result(False, None, "Todo not found in Today")
        if int(item.get("completed_sessions") or 0) >= int(item.get("planned_sessions") or 1):
            return Result(False, None, "Todo already completed in Today")

        self._current_todo_id = int(todo_id)
        self._current_item = item
        self._session_started_at_utc = None
        self._reflect_stage_delta = 0
        self._reflect_note = ""

        self._focus_minutes = max(FOCUS_MINUTES_MIN, min(FOCUS_MINUTES_MAX, int(self._focus_minutes)))
        self._timer.arm(TimerMode.WORK, self._focus_minutes * 60)
        self.phase = PromodoroPhase.FOCUS_WAIT
        return Result(True, int(todo_id), "Focus ready")

    def space_action(self) -> Result | None:
        if self.phase == PromodoroPhase.FOCUS_WAIT:
            self._timer.start()
            if self._timer.state == TimerState.RUNNING:
                if self._session_started_at_utc is None:
                    self._session_started_at_utc = datetime.now(timezone.utc)
                self.phase = PromodoroPhase.FOCUS_RUN
            return Result(True, None, "")

        if self.phase == PromodoroPhase.FOCUS_RUN:
            self._timer.pause()
            self.phase = PromodoroPhase.FOCUS_PAUSED
            return Result(True, None, "Paused")

        if self.phase == PromodoroPhase.FOCUS_PAUSED:
            self._timer.resume()
            self.phase = PromodoroPhase.FOCUS_RUN
            return Result(True, None, "Resumed")

        if self.phase == PromodoroPhase.REST_RUN:
            self._timer.pause()
            self.phase = PromodoroPhase.REST_PAUSED
            return Result(True, None, "Rest paused")

        if self.phase == PromodoroPhase.REST_PAUSED:
            if self._timer.state == TimerState.IDLE:
                self._timer.start()
            else:
                self._timer.resume()
            if self._timer.state == TimerState.RUNNING:
                self.phase = PromodoroPhase.REST_RUN
                return Result(True, None, "Rest started")
            return Result(False, None, "Cannot start rest")

        return None

    def confirm_selection(self, state: AppState) -> None:
        if self.phase in (PromodoroPhase.FOCUS_RUN, PromodoroPhase.FOCUS_PAUSED):
            state.request_confirm(self.finish_focus_early, "enter")
            return
        if self.phase in (PromodoroPhase.REFLECT, PromodoroPhase.REFLECT_NOTE):
            result = self.save_reflect_and_start_rest()
            state.last_result = result
            return
        if self.phase in (PromodoroPhase.REST_RUN, PromodoroPhase.REST_PAUSED):
            result = self.finish_rest(skip=True)
            state.last_result = result

    def finish_focus_early(self) -> Result | None:
        if self.phase not in (PromodoroPhase.FOCUS_RUN, PromodoroPhase.FOCUS_PAUSED):
            return Result(False, None, "Focus is not running")
        self._timer.update()
        if self._timer.state == TimerState.RUNNING:
            self._timer.pause()
        return self._enter_reflect("Focus finished")

    def reset_focus(self) -> Result:
        if self.phase not in (
            PromodoroPhase.FOCUS_WAIT,
            PromodoroPhase.FOCUS_RUN,
            PromodoroPhase.FOCUS_PAUSED,
        ):
            return Result(False, None, "Focus is not active")
        self._timer.arm(TimerMode.WORK, self._focus_minutes * 60)
        self.phase = PromodoroPhase.FOCUS_WAIT
        self._session_started_at_utc = None
        self._reflect_stage_delta = 0
        self._reflect_note = ""
        return Result(True, None, "Focus reset")

    def delete_selected(self) -> Result | None:
        """Cancel focus and return to Today (Backspace)."""
        if not self.is_focus_phase() or self._current_todo_id is None:
            return None
        self._timer.arm(TimerMode.WORK, self._focus_minutes * 60)
        self.phase = PromodoroPhase.FOCUS_WAIT
        self._current_todo_id = None
        self._current_item = None
        self._session_started_at_utc = None
        self._reflect_note = ""
        self._reflect_stage_delta = 0
        self._now.current = "today"
        self._now.show_today_panel = False
        self._now.today.load_data()
        self._now.suggestion.load_data()
        return Result(True, None, "Focus cancelled")

    def adjust_time(self, direction: int) -> Result | None:
        if direction not in (-1, 1):
            return None

        if self.phase in (PromodoroPhase.FOCUS_WAIT, PromodoroPhase.FOCUS_PAUSED):
            changed = self._timer.adjust_total(
                delta_seconds=direction * FOCUS_ADJUST_STEP_MINUTES * 60,
                min_seconds=FOCUS_MINUTES_MIN * 60,
                max_seconds=FOCUS_MINUTES_MAX * 60,
                allow_running=False,
            )
            if not changed:
                return Result(False, None, "Cannot adjust focus minutes")
            self._focus_minutes = self._timer.target_seconds // 60
            return Result(True, self._focus_minutes, f"Focus: {self._focus_minutes} min")

        if self.phase in (PromodoroPhase.REST_RUN, PromodoroPhase.REST_PAUSED):
            changed = self._timer.adjust_total(
                delta_seconds=direction * REST_ADJUST_STEP_MINUTES * 60,
                min_seconds=REST_MINUTES_MIN * 60,
                max_seconds=REST_MINUTES_MAX * 60,
                allow_running=True,
            )
            if not changed:
                return Result(False, None, "Cannot adjust rest minutes")
            self._rest_minutes = self._timer.target_seconds // 60
            return Result(True, self._rest_minutes, f"Rest: {self._rest_minutes} min")

        return None

    def open_note(self) -> Result | None:
        if self.phase != PromodoroPhase.REFLECT:
            return None
        self.phase = PromodoroPhase.REFLECT_NOTE
        return Result(True, None, "Note input")

    def close_note(self) -> Result | None:
        if self.phase != PromodoroPhase.REFLECT_NOTE:
            return None
        self.phase = PromodoroPhase.REFLECT
        return Result(True, None, "")

    def append_note_char(self, ch: str) -> None:
        if self.phase != PromodoroPhase.REFLECT_NOTE:
            return
        if not ch or len(ch) != 1 or not ch.isprintable():
            return
        self._reflect_note += ch

    def backspace_note(self) -> None:
        if self.phase != PromodoroPhase.REFLECT_NOTE:
            return
        self._reflect_note = self._reflect_note[:-1]

    def adjust_reflect_stage(self, direction: int) -> Result | None:
        if self.phase not in (PromodoroPhase.REFLECT, PromodoroPhase.REFLECT_NOTE):
            return None
        if direction not in (-1, 1):
            return None

        next_delta = self._reflect_stage_delta + direction
        next_stage = self._reflect_base_stage + next_delta
        if next_stage < 0 or next_stage > self._reflect_total_stages:
            return Result(False, None, "Stage boundary reached")
        self._reflect_stage_delta = next_delta
        return Result(True, next_delta, f"Stage delta: {next_delta:+d}")

    def timer_tick(self) -> list[TimerEvent]:
        return self._timer.update()

    def handle_timer_event(self, event: TimerEvent) -> Result | None:
        if event == TimerEvent.WORK_5MIN_LEFT:
            return Result(True, None, "5 minutes left")
        if event == TimerEvent.WORK_TIME_UP:
            return self._enter_reflect("Time's up")
        if event == TimerEvent.REST_TIME_UP:
            return self.finish_rest(skip=False)
        return None

    def _enter_reflect(self, message: str) -> Result:
        if self._session_started_at_utc is None:
            self._session_started_at_utc = datetime.now(timezone.utc)
        self.load_data()
        current_stage = int(self._current_item.get("current_stage") or 0) if self._current_item else 0
        total_stages = max(1, int(self._current_item.get("total_stages") or 1)) if self._current_item else 1
        self._reflect_base_stage = current_stage
        self._reflect_total_stages = total_stages
        self._reflect_stage_delta = 0
        self._reflect_note = ""
        self.phase = PromodoroPhase.REFLECT
        return Result(True, None, message)

    def _compute_duration_minutes(self) -> int:
        """Use timer consumed time (target - remaining), not wall-clock elapsed.
        Excludes pause time; equals session configured duration when timer completes."""
        total = int(self._timer.target_seconds)
        remaining = int(self._timer.remaining_seconds)
        consumed = total - remaining
        return max(1, int(round(consumed / 60.0)))

    def save_reflect_and_start_rest(self) -> Result:
        if self.phase not in (PromodoroPhase.REFLECT, PromodoroPhase.REFLECT_NOTE):
            return Result(False, None, "Not in reflect phase")
        if self._current_todo_id is None:
            return Result(False, None, "No active todo")
        if self._session_started_at_utc is None:
            return Result(False, None, "Session was not started")

        duration = self._compute_duration_minutes()
        ended_at = datetime.now(timezone.utc)
        note = self._reflect_note.strip() or None
        todo_id = int(self._current_todo_id)

        with db_session() as s:
            save_result = save_session(
                s,
                todo_item_id=todo_id,
                duration_minutes=duration,
                started_at_utc=self._session_started_at_utc,
                ended_at_utc=ended_at,
                description=note,
            )
            if not save_result.success:
                return save_result

            stage_result = apply_stage_delta(s, EntityType.TODO, todo_id, self._reflect_stage_delta)
            if not stage_result.success:
                return stage_result

            progress_result = self._today_store.mark_session_completed(todo_id, session=s)
            if not progress_result.success:
                return progress_result

        self._session_started_at_utc = None
        self._reflect_note = ""
        self._reflect_stage_delta = 0

        self._timer.arm(TimerMode.REST, self._rest_minutes * 60)
        self.phase = PromodoroPhase.REST_PAUSED
        self._now.today.load_data()
        self._now.suggestion.load_data()

        return Result(True, save_result.data, "Session saved. Rest ready (press Space)")

    def finish_rest(self, *, skip: bool) -> Result:
        self._now.today.load_data()
        self._timer.arm(TimerMode.WORK, self._focus_minutes * 60)
        self.phase = PromodoroPhase.FOCUS_WAIT
        self._current_todo_id = None
        self._current_item = None
        self._session_started_at_utc = None
        self._reflect_note = ""
        self._reflect_stage_delta = 0
        self._now.current = "today"
        self._now.show_today_panel = False
        self._now.suggestion.load_data()
        if skip:
            return Result(True, None, "Rest skipped. Back to Today.")
        return Result(True, None, "Rest finished. Back to Today.")

    def _render_lines(self):
        title = self._current_item.get("title") if self._current_item else "No todo selected"
        timer_text = _format_mmss(self._timer.remaining_seconds)

        if self.phase == PromodoroPhase.FOCUS_WAIT:
            return [
                [("", title)],
                [("", "")],
                [("", timer_text)],
                [("class:dim", "Space to start")],
            ]

        if self.phase == PromodoroPhase.FOCUS_RUN:
            return [
                [("", title)],
                [("", "")],
                [("", timer_text)],
            ]

        if self.phase == PromodoroPhase.FOCUS_PAUSED:
            return [
                [("", title)],
                [("", "")],
                [("", timer_text)],
                [("class:dim", "paused")],
            ]

        if self.phase in (PromodoroPhase.REFLECT, PromodoroPhase.REFLECT_NOTE):
            base = self._reflect_base_stage
            total = self._reflect_total_stages
            nxt = base + self._reflect_stage_delta
            stage_line = f"stage {base}/{total}" if self._reflect_stage_delta == 0 else f"stage {base}→{nxt}/{total}"
            delta_line = f"{self._reflect_stage_delta:+d}"
            lines = [
                [("", f"✓ {title}")],
                [("", "")],
                [("", f"{self._compute_duration_minutes()} min")],
                [("", stage_line)],
                [("", "")],
                [("", delta_line)],
                [("", "")],
            ]
            if self.phase == PromodoroPhase.REFLECT_NOTE:
                lines.append([("", f"> {self._reflect_note}_")])
                lines.append([("", "")])
                lines.append([("class:dim", "Enter save  ·  Esc cancel note")])
            else:
                lines.append([("class:dim", "Enter save  ·  n note  ·  +/- stage")])
            return lines

        if self.phase in (PromodoroPhase.REST_RUN, PromodoroPhase.REST_PAUSED):
            lines = [
                [("", "☕")],
                [("", "")],
                [("", timer_text)],
            ]
            if self.phase == PromodoroPhase.REST_PAUSED:
                lines.append([("class:dim", "Space to start")])
            return lines

        return [[("class:dim", "Loading...")]]
