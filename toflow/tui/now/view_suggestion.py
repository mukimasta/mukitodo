"""Suggestion view for NOW."""

from __future__ import annotations

from typing import TYPE_CHECKING

from toflow.tui.item_formatters import format_now_suggestion_item
from toflow.ops.result import Result
from toflow.ops.today import TodayStore
from toflow.registry import EntityType
from toflow.tui.now.suggestion import SuggestionEngine
from toflow.tui.pane.flat_list import FlatListPane
from toflow.tui.view.base import View

if TYPE_CHECKING:
    from toflow.tui.now.state import NowState
    from toflow.tui.state import AppState


class SuggestionView(View):
    title = "What will you focus on?"
    status_hint = "[↑↓] move  [Enter] add and back to Today  [Esc] back"
    entity_type = EntityType.TODO

    def __init__(self, now: NowState, *, today_store: TodayStore, engine: SuggestionEngine) -> None:
        self._now = now
        self._today_store = today_store
        self._engine = engine
        self._pane = FlatListPane(
            item_formatter=format_now_suggestion_item,
            empty_msg="  No suggestion candidates. Add active todos first.",
        )
        self._pane.layout_mode = "zen"
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        in_today = self._today_store.in_today_ids()
        rows = self._engine.load(in_today_ids=in_today)
        self._pane.set_items(rows)

    def confirm_selection(self, state: AppState) -> None:
        item = self._pane.selected_item()
        if not item:
            return
        if item.get("in_today"):
            state.last_result = Result(False, None, "Todo already in Today")
            return
        result = self._today_store.add_item(int(item["id"]))
        state.last_result = result
        if not result.success:
            return
        self._now.today.load_data()
        self.load_data()
        self._now.current = "today"
        self._now.show_today_panel = False

    def go_back(self, state: AppState) -> None:
        if self._today_store.get_items():
            self._now.current = "today"
            self._now.show_today_panel = False
