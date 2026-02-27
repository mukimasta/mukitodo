"""Utilities for terminal display-width aware text operations.

`len()` counts code points, not rendered terminal columns. East Asian text
and some symbols occupy two columns, so all layout math should use these
helpers instead of plain string length/slicing.
"""

from __future__ import annotations

from prompt_toolkit.utils import get_cwidth


def char_width(ch: str) -> int:
    """Return rendered width of a single character in terminal columns."""
    return max(0, get_cwidth(ch))


def text_width(text: str) -> int:
    """Return rendered width of text in terminal columns."""
    return sum(char_width(ch) for ch in text)


def take_by_width(text: str, max_width: int) -> str:
    """Take as many characters as fit into `max_width` columns."""
    if max_width <= 0 or not text:
        return ""

    out: list[str] = []
    used = 0
    for ch in text:
        w = char_width(ch)
        if used + w > max_width:
            break
        out.append(ch)
        used += w
    return "".join(out)


def truncate_text(text: str, max_width: int, ellipsis: str = "…") -> str:
    """Truncate text to display width, appending ellipsis when needed."""
    if max_width <= 0:
        return ""
    if text_width(text) <= max_width:
        return text

    ellipsis_w = text_width(ellipsis)
    if ellipsis_w >= max_width:
        return take_by_width(ellipsis, max_width)

    return take_by_width(text, max_width - ellipsis_w) + ellipsis
