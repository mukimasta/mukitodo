"""Pane ABC — layout + cursor + render, all in one."""

from abc import ABC, abstractmethod
from typing import Any

FormattedText = list[tuple[str, str]]
Lines = list[FormattedText]


class Pane(ABC):
    """A self-contained renderable panel with cursor state.

    Subclasses: FlatListPane, GroupBoxPane.
    """

    viewport_start: int = 0

    @abstractmethod
    def move(self, delta: int) -> None:
        """Move cursor by delta (up/down)."""

    @abstractmethod
    def selected_id(self) -> int | None:
        """ID of the currently selected item, or None."""

    @abstractmethod
    def selected_item(self) -> dict[str, Any] | None:
        """Currently selected item dict, or None."""

    @abstractmethod
    def render(self) -> Lines:
        """Render content as a list of lines. Does NOT handle viewport clipping."""

    @abstractmethod
    def selected_line_index(self) -> int | None:
        """Line index of the selected item in the last render output. Used by display for viewport."""
