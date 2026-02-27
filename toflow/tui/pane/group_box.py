"""GroupBoxPane — groups with rows, two-level cursor (group / row)."""

from typing import Callable

from toflow.tui.pane.base import FormattedText, Lines, Pane
from toflow.tui.text_width import text_width, truncate_text

GroupFormatter = Callable[[dict], FormattedText]
"""(group_header) -> single-line segments."""

RowFormatter = Callable[[dict], FormattedText]
"""(row_item) -> single-line segments."""

BOX_WIDTH = 60


def _truncate(s: str, width: int) -> str:
    return truncate_text(s, width)


class GroupBoxPane(Pane):
    """Grouped box layout with two-level cursor.

    Data: list of (group_dict, list[row_dict]).
    Cursor has two levels:
      - group level: _row_idx is None, cursor highlights the group header
      - row level:   _row_idx is int, cursor highlights a row within current group

    The Pane handles selection style override and truncation to box width.
    Formatters only care about item content.
    """

    def __init__(
        self,
        group_formatter: GroupFormatter,
        row_formatter: RowFormatter,
        *,
        empty_msg: str = "  (empty)",
        box_width: int = BOX_WIDTH,
    ):
        self.group_formatter = group_formatter
        self.row_formatter = row_formatter
        self.empty_msg = empty_msg
        self.box_width = box_width

        self.groups: list[tuple[dict, list[dict]]] = []
        self._group_idx: int = 0
        self._row_idx: int | None = None  # None = group level
        self._last_selected_line: int | None = None
        self._block_ranges: list[tuple[int, int]] = []  # (start, end) per group, for block-aware clipping

    @property
    def at_row_level(self) -> bool:
        return self._row_idx is not None

    def set_groups(self, groups: list[tuple[dict, list[dict]]]) -> None:
        """Replace groups and reconcile cursor."""
        old_gid = self._current_group_id()
        old_rid = self.selected_id() if self.at_row_level else None

        self.groups = groups
        if not groups:
            self._group_idx = 0
            self._row_idx = None
            return

        # Try to keep group selection
        found_group = False
        for i, (g, _) in enumerate(groups):
            if g.get("id") == old_gid:
                self._group_idx = i
                found_group = True
                break
        if not found_group:
            self._group_idx = max(0, min(self._group_idx, len(groups) - 1))
            self._row_idx = None
            return

        # Try to keep row selection
        if self._row_idx is not None and old_rid is not None:
            _, rows = groups[self._group_idx]
            found_row = False
            for j, r in enumerate(rows):
                if r.get("id") == old_rid:
                    self._row_idx = j
                    found_row = True
                    break
            if not found_row:
                if rows:
                    self._row_idx = max(0, min(self._row_idx, len(rows) - 1))
                else:
                    self._row_idx = None

    def move(self, delta: int) -> None:
        if not self.groups:
            return
        if self._row_idx is None:
            # Group level
            self._group_idx = max(0, min(len(self.groups) - 1, self._group_idx + delta))
        else:
            # Row level
            _, rows = self.groups[self._group_idx]
            if rows:
                self._row_idx = max(0, min(len(rows) - 1, self._row_idx + delta))

    def drill_in(self) -> bool:
        """Right: enter row level from group level. Returns True if state changed."""
        if not self.groups:
            return False
        if self._row_idx is not None:
            return False  # Already at row level
        _, rows = self.groups[self._group_idx]
        if not rows:
            return False
        self._row_idx = 0
        return True

    def drill_out(self) -> bool:
        """Left: return to group level from row level. Returns True if state changed."""
        if self._row_idx is None:
            return False
        self._row_idx = None
        return True

    def selected_id(self) -> int | None:
        if not self.groups:
            return None
        if self._row_idx is not None:
            _, rows = self.groups[self._group_idx]
            if rows and 0 <= self._row_idx < len(rows):
                return rows[self._row_idx].get("id")
            return None
        return self._current_group_id()

    def selected_item(self) -> dict | None:
        if not self.groups:
            return None
        if self._row_idx is not None:
            _, rows = self.groups[self._group_idx]
            if rows and 0 <= self._row_idx < len(rows):
                return rows[self._row_idx]
            return None
        g, _ = self.groups[self._group_idx]
        return g

    def selected_group(self) -> tuple[dict, list[dict]] | None:
        if not self.groups or self._group_idx >= len(self.groups):
            return None
        return self.groups[self._group_idx]

    def selected_line_index(self) -> int | None:
        return self._last_selected_line

    def selected_block_range(self) -> tuple[int, int] | None:
        """(start, end) line indices of the block containing the selection. For block-aware viewport clipping."""
        if not self._block_ranges or self._group_idx >= len(self._block_ranges):
            return None
        return self._block_ranges[self._group_idx]

    def render(self) -> Lines:
        self._last_selected_line = None
        self._block_ranges = []
        if not self.groups:
            return [[("class:dim", self.empty_msg)]]

        out: Lines = []
        bw = self.box_width
        content_w = bw - 2  # inside box borders
        indent = "  "

        for gi, (group, rows) in enumerate(self.groups):
            block_start = len(out)
            is_group_selected = gi == self._group_idx
            group_highlight = is_group_selected and self._row_idx is None
            group_style = "class:selected_track" if is_group_selected else "class:unselected_track"

            # Top border with group title
            title_segs = self.group_formatter(group)
            title_text = "".join(t for _, t in title_segs)
            title_text = _truncate(title_text, content_w - 4)
            title_w = text_width(title_text)
            dash_r = max(1, bw - 2 - 1 - title_w - 2)
            header_line = f"{indent}┌─ {title_text} " + "─" * dash_r + "┐"

            if group_highlight:
                out.append([("class:selected_track", header_line)])
                self._last_selected_line = len(out) - 1
            else:
                out.append([(group_style, header_line)])

            # Rows
            if not rows:
                empty_text = "(no items)"
                pad = " " * max(0, content_w - 2 - text_width(empty_text))
                out.append([(group_style, f"{indent}│ {empty_text}{pad} │")])
            else:
                for ri, row in enumerate(rows):
                    is_row_selected = is_group_selected and self._row_idx == ri
                    segs = self.row_formatter(row)
                    # Truncate segments to fit content_w - 2
                    max_w = content_w - 2
                    trunc_segs: FormattedText = []
                    used = 0
                    for style, text in segs:
                        if used >= max_w:
                            break
                        remaining = max_w - used
                        part_w = text_width(text)
                        if part_w > remaining:
                            trunc_segs.append((style, truncate_text(text, remaining)))
                            used = max_w
                        else:
                            trunc_segs.append((style, text))
                            used += part_w
                    pad = " " * max(0, max_w - used)

                    if is_row_selected:
                        row_text = "".join(t for _, t in trunc_segs)
                        out.append([("class:selected", f"{indent}│ {row_text}{pad} │")])
                        self._last_selected_line = len(out) - 1
                    else:
                        out.append([(group_style, f"{indent}│ "), *trunc_segs, (group_style, f"{pad} │")])

            # Bottom border
            out.append([(group_style, f"{indent}└" + "─" * (bw - 2) + "┘")])

            # Spacer
            out.append([("", "")])
            self._block_ranges.append((block_start, len(out) - 1))

        return out

    def focus_group_by_id(self, group_id: int) -> bool:
        """Move group cursor to the group with the given ID. Returns True if found."""
        for i, (g, _) in enumerate(self.groups):
            if g.get("id") == group_id:
                self._group_idx = i
                self._row_idx = None
                return True
        return False

    def _current_group_id(self) -> int | None:
        if not self.groups or self._group_idx >= len(self.groups):
            return None
        return self.groups[self._group_idx][0].get("id")
