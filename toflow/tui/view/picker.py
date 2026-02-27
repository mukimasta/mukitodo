"""Picker view — modal target selection for reparent/promote."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from toflow.database import db_session
from toflow.ops import list_tracks_with_projects, reparent
from toflow.ops.result import Result
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_project_row, format_track_group
from toflow.tui.pane.base import FormattedText
from toflow.tui.pane.group_box import GroupBoxPane
from toflow.tui.view.base import View

if TYPE_CHECKING:
    from toflow.tui.state import AppState


@dataclass
class MoveContext:
    entity_type: EntityType
    entity_id: int
    entity_title: str
    current_parent_id: int | None


class PickerView(View):
    """Modal target selector for reparent/promote.

    Reuses GroupBoxPane to display Tracks with Projects.
    - Todo  → pick a Project: drill into Track group, confirm at row level.
    - Project → pick a Track: confirm at group level directly.
    """

    entity_type = EntityType.TRACK

    def __init__(self, ctx: MoveContext) -> None:
        self.ctx = ctx
        self.pick_target = (
            EntityType.PROJECT if ctx.entity_type == EntityType.TODO else EntityType.TRACK
        )
        self.entity_type = self.pick_target
        self.title = f'Move "{ctx.entity_title}"'
        self.status_hint = "[↑↓] navigate  [←/→] drill  [Enter] confirm  [Esc] cancel"
        self._pane = GroupBoxPane(
            group_formatter=self._fmt_group,
            row_formatter=self._fmt_row,
            empty_msg="  No targets available.",
        )
        self.load_data()
        if self.pick_target == EntityType.TRACK and ctx.current_parent_id is not None:
            self._pane.focus_group_by_id(ctx.current_parent_id)

    @property
    def pane(self) -> GroupBoxPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_tracks_with_projects(s)
        self._pane.set_groups(result.data if result.success else [])

    # -- Navigation -----------------------------------------------------------

    def go_deeper(self, state: AppState) -> None:
        if self.pick_target == EntityType.PROJECT and not self._pane.at_row_level:
            self._pane.drill_in()

    def go_back(self, state: AppState) -> None:
        if self._pane.at_row_level:
            self._pane.drill_out()
        else:
            state.close_modal()

    def confirm_selection(self, state: AppState) -> None:
        target_id = self._pane.selected_id()
        if target_id is None:
            return
        if self.pick_target == EntityType.PROJECT and not self._pane.at_row_level:
            return
        if target_id == self.ctx.current_parent_id:
            state.last_result = Result(False, None, "Already under this parent")
            return

        def _do_move() -> Result | None:
            with db_session() as s:
                result = reparent(s, self.ctx.entity_type, self.ctx.entity_id, target_id)
            if result.success:
                state.close_modal()
                cv = state.current_view
                cv.load_data()
                if (
                    hasattr(cv.pane, "at_row_level")
                    and not cv.pane.at_row_level
                    and len(state.structure_stack) > 1
                ):
                    state.structure_stack.pop()
            return result

        state.request_confirm(_do_move, "enter")

    # -- Formatters with (current) marker -------------------------------------

    def _fmt_group(self, item: dict) -> FormattedText:
        segs = list(format_track_group(item))
        if self.pick_target == EntityType.TRACK and item.get("id") == self.ctx.current_parent_id:
            segs.append(("class:dim", " (current)"))
        return segs

    def _fmt_row(self, item: dict) -> FormattedText:
        segs = list(format_project_row(item))
        if self.pick_target == EntityType.PROJECT and item.get("id") == self.ctx.current_parent_id:
            segs.append(("class:dim", " (current)"))
        return segs
