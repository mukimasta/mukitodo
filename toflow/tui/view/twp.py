"""TWP views — TWPTrackView (group level) + TWPProjectView (row level).

Both share the same GroupBoxPane instance. The visual is identical (box layout),
only the cursor level and entity operations differ.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from toflow.database import db_session
from toflow.ops import list_tracks_with_projects
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_project_row, format_track_group
from toflow.tui.pane.group_box import GroupBoxPane
from toflow.tui.view.base import EntityView

if TYPE_CHECKING:
    from toflow.tui.state import AppState


def _load_twp(pane: GroupBoxPane) -> None:
    """Shared data loader for both views."""
    with db_session() as s:
        result = list_tracks_with_projects(s)
    pane.set_groups(result.data if result.success else [])


class TWPTrackView(EntityView):
    """Group-level view — operates on Tracks."""

    @property
    def title(self) -> str:
        group = self._pane.selected_group()
        if group:
            return group[0].get("title", "?") or "?"
        return "?"

    status_hint = "[↑↓] move  [→] enter  [=/+] add project  [Space] toggle  [r] edit  [s] sleep  [a] archive  [Alt+↑↓] reorder"
    entity_type = EntityType.TRACK
    toggle_target = "sleeping"

    def __init__(self, focus_track_id: int | None = None) -> None:
        self._pane = GroupBoxPane(
            group_formatter=format_track_group,
            row_formatter=format_project_row,
            empty_msg="  No tracks. Press = to add.",
        )
        self.load_data()
        if focus_track_id is not None:
            self._pane.focus_group_by_id(focus_track_id)

    @property
    def pane(self) -> GroupBoxPane:
        return self._pane

    def load_data(self) -> None:
        _load_twp(self._pane)

    def go_deeper(self, state: AppState) -> None:
        if not self._pane.groups:
            return
        if self._pane.drill_in():
            group = self._pane.selected_group()
            track_name = group[0].get("title", "?") if group else "?"
            state.push_structure(TWPProjectView(self._pane, track_name=track_name))

    def go_back(self, state: AppState) -> None:
        state.pop_structure()

    def add_entity_type(self) -> EntityType:
        return EntityType.PROJECT if self._pane.selected_group() else EntityType.TRACK

    def add_parent_id(self) -> int | None:
        group = self._pane.selected_group()
        if not group:
            return None
        return group[0].get("id")


class TWPProjectView(EntityView):
    """Row-level view — operates on Projects within the current Track."""

    status_hint = "[↑↓] move  [→] todos  [←] back  [Space] toggle  [=/+] add  [r] edit  [m] move  [s] sleep  [c] cancel  [p] pin  [a] archive"
    entity_type = EntityType.PROJECT
    toggle_target = "finished"

    def __init__(self, pane: GroupBoxPane, *, track_name: str = "?") -> None:
        self._pane = pane
        self._track_name = track_name

    @property
    def title(self) -> str:
        return self._track_name

    @property
    def pane(self) -> GroupBoxPane:
        return self._pane

    def load_data(self) -> None:
        _load_twp(self._pane)

    def go_deeper(self, state: AppState) -> None:
        item = self._pane.selected_item()
        if item and item.get("id") is not None:
            from toflow.tui.view.todos import TodosView

            state.push_structure(
                TodosView(
                    project_id=item["id"],
                    project_name=item.get("title") or "?",
                    track_name=self._track_name,
                )
            )

    def go_back(self, state: AppState) -> None:
        self._pane.drill_out()
        state.pop_structure()

    def add_parent_id(self) -> int | None:
        group = self._pane.selected_group()
        return group[0].get("id") if group else None
