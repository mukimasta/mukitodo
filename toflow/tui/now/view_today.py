"""Today queue view for NOW."""

from __future__ import annotations

from typing import TYPE_CHECKING

from toflow.ops.result import Result
from toflow.ops.today import TodayStore
from toflow.registry import EntityType
from toflow.tui.now.config import TODAY_MAX_ITEMS
from toflow.tui.pane.today import TodayPane
from toflow.tui.view.base import View

if TYPE_CHECKING:
    from toflow.tui.now.state import NowState
    from toflow.tui.state import AppState


class TodayView(View):
    title = "Today"
    status_hint = "[↑↓] move  [Alt+↑↓] reorder  [+/-] sessions  [Backspace] remove  [Enter] start  [r] clear"
    entity_type = EntityType.TODO

    def __init__(self, now: NowState, *, store: TodayStore) -> None:
        self._now = now
        self._store = store
        self._pane = TodayPane()
        self.load_data()

    @property
    def pane(self) -> TodayPane:
        return self._pane

    def load_data(self) -> None:
        items = self._store.get_items()
        show_add = len(items) < TODAY_MAX_ITEMS
        self._pane.set_today_items(items, show_add=show_add)

    def confirm_selection(self, state: AppState) -> None:
        item = self._pane.selected_item()
        if item is None:
            return
        if self._pane.selected_is_add():
            self._now.current = "suggestion"
            self._now.show_today_panel = False
            self._now.suggestion.load_data()
            return
        if int(item.get("completed_sessions") or 0) >= int(item.get("planned_sessions") or 1):
            state.last_result = Result(False, None, "Selected todo is already completed in Today")
            return
        state.request_confirm(self._confirm_start_selected, "enter")

    def _confirm_start_selected(self) -> Result | None:
        item = self._pane.selected_item()
        if item is None or self._pane.selected_is_add():
            return Result(False, None, "No todo selected")
        todo_id = int(item["todo_id"])
        result = self._now.promodoro.enter_focus(todo_id)
        if result.success:
            self._now.current = "promodoro"
            self._now.show_today_panel = False
        return result

    def go_back(self, state: AppState) -> None:
        return

    def clear_all(self) -> Result:
        if self._now.promodoro.current_todo_id() is not None:
            return Result(False, None, "Cannot clear: a todo is in focus")
        result = self._store.clear_all()
        self.load_data()
        return result

    def delete_selected(self) -> Result | None:
        item = self._pane.selected_item()
        if item is None or self._pane.selected_is_add():
            return None
        todo_id = int(item["todo_id"])
        if self._now.promodoro.current_todo_id() == todo_id:
            return Result(False, None, "Cannot remove: todo is in focus")
        result = self._store.remove_item(todo_id)
        self.load_data()
        return result

    def reorder_selected(self, direction: int) -> Result | None:
        item = self._pane.selected_item()
        if item is None or self._pane.selected_is_add():
            return None
        result = self._store.reorder(int(item["todo_id"]), int(direction))
        self.load_data()
        return result

    def session_delta(self, delta: int) -> Result | None:
        item = self._pane.selected_item()
        if item is None or self._pane.selected_is_add():
            return None
        result = self._store.adjust_planned(int(item["todo_id"]), int(delta))
        self.load_data()
        return result

    def add_todo(self, todo_id: int) -> Result:
        result = self._store.add_item(int(todo_id))
        self.load_data()
        return result
