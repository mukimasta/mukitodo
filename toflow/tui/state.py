"""AppState — navigation state, UI mode, message."""

from __future__ import annotations

from enum import Enum
from typing import Callable

from toflow.ops.result import EmptyResult, Result
from toflow.tui.input.form import InputForm
from toflow.tui.input.session import InputSession
from toflow.tui.now.state import NowState
from toflow.tui.view.base import View
from toflow.tui.view.tracks import TracksView
from toflow.tui.view.twp import TWPTrackView


class UIMode(Enum):
    NORMAL = "normal"
    CONFIRM = "confirm"
    INPUT = "input"


class PrimaryView(Enum):
    STRUCTURE = "structure"
    NOW = "now"


class AppState:
    """Application state: structure/primary/secondary + modal management."""

    def __init__(self) -> None:
        # Structure drill stack: Track -> Project -> Todo
        self.structure_stack: list[View] = [TracksView(), TWPTrackView()]
        # NOW aggregate state
        self.now = NowState()
        # Primary view: structure / now
        self.primary: PrimaryView = PrimaryView.STRUCTURE
        # Secondary overlays: box/archive/timeline etc.
        self.secondary: View | None = None
        # Modal overlay: temporary task-oriented view (picker, etc.)
        self.modal: View | None = None
        self.ui_mode: UIMode = UIMode.NORMAL
        self.last_result: Result = EmptyResult

        # Confirm mode state
        self._confirm_action: Callable[[], Result | None] | None = None
        self._confirm_key: str = ""

        # Input mode state
        self._input_session: InputSession | None = None

    @property
    def current_view(self) -> View:
        if self.modal is not None:
            return self.modal
        if self.secondary is not None:
            return self.secondary
        if self.primary == PrimaryView.NOW:
            return self.now.view()
        return self.structure_stack[-1]

    @property
    def has_form(self) -> bool:
        return self._input_session is not None

    @property
    def form(self) -> InputForm | None:
        if self._input_session is None:
            return None
        return self._input_session.form

    @property
    def input_session(self) -> InputSession | None:
        return self._input_session

    def is_now_active(self) -> bool:
        return self.primary == PrimaryView.NOW and self.secondary is None and self.modal is None

    # -- Navigation --

    def push_structure(self, view: View) -> None:
        """Drill deeper inside Structure."""
        self.structure_stack.append(view)
        self.last_result = EmptyResult

    def pop_structure(self) -> None:
        """Go one level up inside Structure."""
        if len(self.structure_stack) > 1:
            self.structure_stack.pop()
            self._refresh_structure_views()
            self.last_result = EmptyResult

    def switch_primary(self) -> None:
        """Switch primary view: structure <-> now. Blocked while modal is open."""
        if self.modal is not None:
            return
        if self.primary == PrimaryView.STRUCTURE:
            self.primary = PrimaryView.NOW
            if not self.now.resume_promodoro_if_active():
                self.now.enter_default_view()
        else:
            self.primary = PrimaryView.STRUCTURE
            self._refresh_structure_views()
        self.last_result = EmptyResult

    def open_secondary(self, view: View) -> None:
        """Open or replace secondary view."""
        self.secondary = view
        self.last_result = EmptyResult

    def toggle_secondary(self, view_cls: type[View]) -> None:
        """Toggle secondary view: same type closes, otherwise open/replace. Blocked while modal is open."""
        if self.modal is not None:
            return
        if isinstance(self.secondary, view_cls):
            self.close_secondary()
            return
        self.open_secondary(view_cls())

    def close_secondary(self) -> None:
        """Close secondary view and return to primary."""
        self.secondary = None
        self._refresh_structure_views()
        self.last_result = EmptyResult

    def go_back(self) -> None:
        """Unified Escape/left behavior."""
        if self.modal is not None:
            self.modal.go_back(self)
            return
        if self.secondary is not None:
            self.close_secondary()
            return
        if self.primary == PrimaryView.NOW:
            self.current_view.go_back(self)
            return
        if self.primary == PrimaryView.STRUCTURE and len(self.structure_stack) > 1:
            self.current_view.go_back(self)

    # -- Modal layer --

    def open_modal(self, view: View) -> None:
        """Show a modal overlay (e.g. picker). Takes priority over secondary."""
        self.modal = view
        self.last_result = EmptyResult

    def close_modal(self) -> None:
        """Dismiss the modal overlay."""
        self.modal = None
        self._refresh_structure_views()
        self.last_result = EmptyResult

    # -- Confirm mode --

    def request_confirm(self, action: Callable[[], Result | None], trigger_key: str) -> None:
        self.ui_mode = UIMode.CONFIRM
        self._confirm_action = action
        self._confirm_key = trigger_key

    def handle_confirm_key(self, pressed_key: str) -> None:
        """Handle a keypress in confirm mode. Same key = execute, other = cancel."""
        normalized = {"c-m": "enter", "c-h": "backspace"}.get(pressed_key, pressed_key)
        expected = {"c-m": "enter", "c-h": "backspace"}.get(self._confirm_key, self._confirm_key)

        if normalized == expected and self._confirm_action is not None:
            result = self._confirm_action()
            if result is not None:
                self.last_result = result

        self._confirm_action = None
        self._confirm_key = ""
        self.ui_mode = UIMode.NORMAL

    # -- Input mode --

    def start_input(
        self,
        session: InputSession,
    ) -> None:
        self.ui_mode = UIMode.INPUT
        self._input_session = session

    def take_input_session(self) -> InputSession | None:
        session = self._input_session
        self._reset_input()
        return session

    def cancel_input(self) -> None:
        self._reset_input()
        self.last_result = EmptyResult

    def _reset_input(self) -> None:
        self._input_session = None
        self.ui_mode = UIMode.NORMAL

    def _refresh_structure_views(self) -> None:
        """Refresh all structure views to avoid stale data after overlay actions."""
        for view in self.structure_stack:
            view.load_data()
