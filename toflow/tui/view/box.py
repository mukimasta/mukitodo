"""Box views — flat lists for box todos/projects (parent_id is NULL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from toflow.database import db_session
from toflow.ops.result import Result
from toflow.ops import list_entities
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_project_row, format_todo_item
from toflow.tui.pane.flat_list import FlatListPane
from toflow.tui.view.base import EntityView

if TYPE_CHECKING:
    from toflow.tui.state import AppState


class BoxTodosView(EntityView):
    """Box todos view (Todo parent_id is NULL)."""

    title = "Box Todos"
    status_hint = "[↑↓] move  [Enter] add to today  [=/+] add  [r] edit  [m] move to project  [Space] toggle  [s] sleep  [c] cancel  [p] pin  [a] archive  [Esc] back"
    entity_type = EntityType.TODO
    toggle_target = "done"

    def __init__(self) -> None:
        self._pane = FlatListPane(
            item_formatter=format_todo_item,
            empty_msg="  No items. Press = to add.",
        )
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_entities(s, EntityType.TODO, parent_id=None)
        self._pane.set_items(result.data if result.success else [])

    def go_deeper(self, state) -> None:
        return

    def confirm_selection(self, state: AppState) -> None:
        item = self._pane.selected_item()
        if item is None:
            return
        if state.now.today_store.is_full():
            state.last_result = Result(False, None, "Today already has 5 items")
            return

        todo_id = int(item["id"])
        state.request_confirm(lambda: state.now.add_todo_from_external(todo_id), "enter")


class BoxProjectsView(EntityView):
    """Box projects view (Project parent_id is NULL)."""

    title = "Box Projects"
    status_hint = "[↑↓] move  [=/+] add  [r] edit  [m] move to track  [Space] toggle  [s] sleep  [c] cancel  [p] pin  [a] archive  [Esc] back"
    entity_type = EntityType.PROJECT
    toggle_target = "finished"

    def __init__(self) -> None:
        self._pane = FlatListPane(
            item_formatter=format_project_row,
            empty_msg="  No items. Press = to add.",
        )
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_entities(s, EntityType.PROJECT, parent_id=None)
        self._pane.set_items(result.data if result.success else [])

    def go_deeper(self, state) -> None:
        return
