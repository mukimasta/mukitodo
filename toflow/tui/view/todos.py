"""TodosView — flat list of todos under a project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from toflow.database import db_session
from toflow.ops.result import Result
from toflow.ops import apply_stage_delta, list_entities, set_stage
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_todo_item
from toflow.tui.pane.flat_list import FlatListPane
from toflow.tui.view.base import EntityView

if TYPE_CHECKING:
    from toflow.tui.state import AppState


class TodosView(EntityView):
    status_hint = "[↑↓] move  [←] back  [Enter] add to today  [Space] stage+1/reopen  [=/+] add  [r] edit  [m] move  [s] sleep  [c] cancel  [p] pin  [a] archive"
    entity_type = EntityType.TODO
    toggle_target = "done"

    def __init__(self, project_id: int, project_name: str = "?", *, track_name: str = "?") -> None:
        self.project_id = project_id
        self._track_name = track_name
        self._project_name = project_name
        self.title = f"{track_name} > {project_name}"
        self._pane = FlatListPane(
            item_formatter=format_todo_item,
            empty_msg="  No todos. Press = to add.",
        )
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_entities(s, EntityType.TODO, parent_id=self.project_id)
        self._pane.set_items(result.data if result.success else [])

    def go_deeper(self, state: AppState) -> None:
        pass

    def add_parent_id(self) -> int | None:
        return self.project_id

    def confirm_selection(self, state: AppState) -> None:
        item = self._pane.selected_item()
        if item is None:
            return
        if state.now.today_store.is_full():
            state.last_result = Result(False, None, "Today already has 5 items")
            return

        todo_id = int(item["id"])
        state.request_confirm(lambda: state.now.add_todo_from_external(todo_id), "enter")

    def space_action(self):
        item = self._pane.selected_item()
        if not item:
            return None
        with db_session() as s:
            if str(item.get("status") or "") == "done":
                total = max(1, int(item.get("total_stages") or 1))
                result = set_stage(s, EntityType.TODO, item["id"],
                                   current_stage=max(0, total - 1), total_stages=total)
            else:
                result = apply_stage_delta(s, EntityType.TODO, item["id"], 1)
        self.load_data()
        return result
