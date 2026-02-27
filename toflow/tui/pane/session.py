"""Cursor-less session pane for NOW Promodoro."""

from __future__ import annotations

from typing import Any, Callable

from toflow.tui.pane.base import Lines, Pane


class SessionPane(Pane):
    """Cursor-less pane that renders NOW Promodoro phases."""

    layout_mode = "zen"

    def __init__(
        self,
        *,
        render_fn: Callable[[], Lines],
        selected_id_fn: Callable[[], int | None],
        selected_item_fn: Callable[[], dict[str, Any] | None],
    ) -> None:
        self._render_fn = render_fn
        self._selected_id_fn = selected_id_fn
        self._selected_item_fn = selected_item_fn

    def move(self, delta: int) -> None:
        return

    def selected_id(self) -> int | None:
        return self._selected_id_fn()

    def selected_item(self) -> dict[str, Any] | None:
        return self._selected_item_fn()

    def render(self) -> Lines:
        return self._render_fn()

    def selected_line_index(self) -> int | None:
        return None
