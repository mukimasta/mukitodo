"""TimelineView — completed sessions grouped by local day."""

from __future__ import annotations

from datetime import datetime

from toflow.database import db_session
from toflow.ops import Result, delete_entity, list_timeline_records
from toflow.registry import EntityType
from toflow.tui.item_formatters import format_timeline_item
from toflow.tui.pane.flat_list import FlatListPane
from toflow.tui.view.base import View


class TimelineView(View):
    """Timeline secondary view (session history)."""

    title = "Timeline"
    status_hint = "[↑↓] move  [r] edit desc  [Backspace] delete  [Esc] back"
    can_edit = True
    entity_type = EntityType.SESSION

    def __init__(self) -> None:
        self._pane = FlatListPane(
            item_formatter=format_timeline_item,
            empty_msg="  No timeline records.",
            is_selectable=lambda item: item.get("kind") == "session",
        )
        self.load_data()

    @property
    def pane(self) -> FlatListPane:
        return self._pane

    def load_data(self) -> None:
        with db_session() as s:
            result = list_timeline_records(s)
        self._pane.set_items(_build_timeline_rows(result.data if result.success else []))

    def delete_selected(self) -> Result | None:
        return self._with_selected(
            lambda s, item: delete_entity(s, self.entity_type, item["id"])
        )


def _build_timeline_rows(records: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for record in records:
        ended_at: datetime | None = record.get("ended_at_utc")
        local_day = ended_at.astimezone().strftime("%Y-%m-%d") if ended_at is not None else "Unknown"
        grouped.setdefault(local_day, []).append(record)

    rows: list[dict] = []
    for day in sorted(grouped.keys(), reverse=True):
        rows.append({"kind": "date_header", "date_label": day, "id": None})
        for record in grouped[day]:
            rows.append({**record, "kind": "session"})
    return rows
