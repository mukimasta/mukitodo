"""TracksView — flat list of all tracks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from toflow.database import db_session
from toflow.ops import list_entities
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_track_item
from toflow.tui.pane.flat_list import FlatListPane
from toflow.tui.view.base import EntityView

if TYPE_CHECKING:
    from toflow.tui.state import AppState


class TracksView(EntityView):
    """Root view — flat list of tracks."""

    title = "Tracks"
    status_hint = "[↑↓] move  [→] enter  [=/+] add  [r] rename  [Space] toggle  [s] sleep  [a] archive  [Alt+↑↓] reorder"
    entity_type = EntityType.TRACK
    toggle_target = "sleeping"

    def __init__(self) -> None:
        self._pane = FlatListPane(
            item_formatter=format_track_item,
            empty_msg="  No tracks. Press = to add.",
        )
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_entities(s, EntityType.TRACK)
        self._pane.set_items(result.data if result.success else [])

    def go_deeper(self, state: AppState) -> None:
        item = self._pane.selected_item()
        if not item:
            return
        from toflow.tui.view.twp import TWPTrackView

        state.push_structure(TWPTrackView(focus_track_id=item["id"]))

    def go_back(self, state: AppState) -> None:
        pass
