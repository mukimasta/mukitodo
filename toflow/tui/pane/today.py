"""Today pane with session dots and optional + Add row."""

from __future__ import annotations

from typing import Any

from toflow.tui.item_formatters import format_now_today_item
from toflow.tui.pane.flat_list import FlatListPane


class TodayPane(FlatListPane):
    """Flat list pane for Today queue."""

    layout_mode = "zen"

    def __init__(self) -> None:
        super().__init__(
            item_formatter=format_now_today_item,
            empty_msg="  No items today.",
        )
        self._show_add = True

    def set_today_items(self, items: list[dict[str, Any]], *, show_add: bool) -> None:
        self._show_add = show_add
        merged = list(items)
        if show_add:
            merged.append({"_virtual": "add", "id": None, "title": "+ Add..."})
        self.set_items(merged)

    def selected_is_add(self) -> bool:
        item = self.selected_item()
        return bool(item and item.get("_virtual") == "add")
