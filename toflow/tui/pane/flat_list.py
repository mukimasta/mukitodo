"""FlatListPane — flat list with single cursor."""

from typing import Callable

from toflow.tui.pane.base import FormattedText, Lines, Pane

ItemFormatter = Callable[[dict], FormattedText]
"""(item) -> single-line FormattedText segments."""
SelectablePredicate = Callable[[dict], bool]
"""(item) -> whether this row can be selected."""


class FlatListPane(Pane):
    """Flat list of items with a single cursor index.

    The Pane handles selection prefix (▸) and selected style override.
    The formatter only cares about item content and status styling.
    """

    def __init__(
        self,
        item_formatter: ItemFormatter,
        *,
        empty_msg: str = "  (empty)",
        is_selectable: SelectablePredicate | None = None,
    ):
        self.item_formatter = item_formatter
        self.empty_msg = empty_msg
        self.is_selectable = is_selectable or (lambda _item: True)
        self.items: list[dict] = []
        self._cursor_idx: int | None = None
        self._last_selected_line: int | None = None

    def set_items(self, items: list[dict]) -> None:
        """Replace items and reconcile cursor."""
        old_id = self.selected_id()
        self.items = items
        if not items:
            self._cursor_idx = None
            return
        if old_id is not None:
            for i, it in enumerate(items):
                if it.get("id") == old_id:
                    if self.is_selectable(it):
                        self._cursor_idx = i
                        return
        selectable = self._selectable_indices()
        if selectable:
            if self._cursor_idx is None:
                self._cursor_idx = selectable[0]
                return
            if self._cursor_idx in selectable:
                return
            self._cursor_idx = min(selectable, key=lambda idx: abs(idx - self._cursor_idx))
            return
        self._cursor_idx = None

    def _selectable_indices(self) -> list[int]:
        return [i for i, item in enumerate(self.items) if self.is_selectable(item)]

    def _current_selectable_pos(self) -> int | None:
        selectable = self._selectable_indices()
        if not selectable or self._cursor_idx is None:
            return None
        try:
            return selectable.index(self._cursor_idx)
        except ValueError:
            return None

    def move(self, delta: int) -> None:
        selectable = self._selectable_indices()
        if not selectable:
            return
        if self._cursor_idx is None:
            self._cursor_idx = selectable[0]
            return
        pos = self._current_selectable_pos()
        if pos is None:
            self._cursor_idx = selectable[0]
            return
        new_pos = max(0, min(len(selectable) - 1, pos + delta))
        self._cursor_idx = selectable[new_pos]

    def selected_id(self) -> int | None:
        item = self.selected_item()
        if not item:
            return None
        return item.get("id")

    def selected_item(self) -> dict | None:
        if (
            self._cursor_idx is None
            or not self.items
            or self._cursor_idx >= len(self.items)
        ):
            return None
        item = self.items[self._cursor_idx]
        if not self.is_selectable(item):
            return None
        return item

    def selected_line_index(self) -> int | None:
        return self._last_selected_line

    def render(self) -> Lines:
        self._last_selected_line = None
        if not self.items:
            return [[("class:dim", self.empty_msg)]]

        out: Lines = []
        for i, item in enumerate(self.items):
            is_selected = i == self._cursor_idx and self.is_selectable(item)
            segments = self.item_formatter(item)

            if is_selected:
                text = "".join(t for _, t in segments)
                out.append([("class:selected", f"▸ {text}")])
                self._last_selected_line = i
            else:
                out.append([("", "  "), *segments])

        return out
