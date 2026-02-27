"""Suggestion scoring engine for NOW."""

from __future__ import annotations

from datetime import datetime, timezone

from toflow.database import db_session
from toflow.ops import list_suggestion_candidates
from toflow.tui.now.config import SUGGESTION_MAX_ITEMS, SuggestionWeights
from toflow.tui.now.types import SuggestionItem
from toflow.utils import as_utc_aware


class SuggestionEngine:
    """Build ranked suggestion rows from NOW candidate query."""

    def __init__(self, *, weights: SuggestionWeights | None = None) -> None:
        self.weights = weights or SuggestionWeights()

    @staticmethod
    def _days_until_deadline(now_utc: datetime, deadline_utc: datetime | None) -> float | None:
        if deadline_utc is None:
            return None
        due = as_utc_aware(deadline_utc)
        if due is None:
            return None
        return (due - now_utc).total_seconds() / 86400.0

    @staticmethod
    def _age_days(now_utc: datetime, created_at_utc: datetime | None) -> float:
        if created_at_utc is None:
            return 365.0
        created = as_utc_aware(created_at_utc)
        if created is None:
            return 365.0
        return max(0.0, (now_utc - created).total_seconds() / 86400.0)

    @staticmethod
    def _deadline_reason(now_utc: datetime, deadline_utc: datetime | None) -> str | None:
        due = as_utc_aware(deadline_utc)
        if due is None:
            return None
        local_due = due.astimezone()
        delta_days = (local_due.date() - now_utc.astimezone().date()).days
        if delta_days == 0:
            return f"DDL {local_due:%m-%d} today"
        return f"DDL {local_due:%m-%d} ({delta_days:+d}d)"

    def _reason_tags(self, row: dict, *, now_utc: datetime) -> list[str]:
        tags: list[str] = []
        if bool(row.get("pinned")) or bool(row.get("project_pinned")):
            tags.append("PIN")

        deadline_reason = self._deadline_reason(now_utc, row.get("deadline_utc"))
        if deadline_reason:
            tags.append(deadline_reason)

        total = max(1, int(row.get("total_stages") or 1))
        cur = max(0, min(int(row.get("current_stage") or 0), total))
        if total > 1 and cur > 0:
            tags.append(f"STAGE {cur}/{total}")

        if bool(row.get("has_recent_session")):
            tags.append("MOMENTUM")

        return tags[:1]

    def _score(self, row: dict, *, now_utc: datetime) -> float:
        pinned_score = self.weights.pinned if (row.get("pinned") or row.get("project_pinned")) else 0.0

        deadline_score = 0.0
        days_until = self._days_until_deadline(now_utc, row.get("deadline_utc"))
        if days_until is not None:
            deadline_score = self.weights.deadline_max * max(0.0, 1.0 - (days_until / 30.0))

        w = int(row.get("project_willingness_hint") or 0)
        i = int(row.get("project_importance_hint") or 0)
        u = int(row.get("project_urgency_hint") or 0)
        hints_score = ((w + i + u) / 9.0) * self.weights.project_hints_max

        total = max(1, int(row.get("total_stages") or 1))
        cur = max(0, min(int(row.get("current_stage") or 0), total))
        stage_score = (cur / total) * self.weights.stage_progress_max

        momentum_score = self.weights.momentum if bool(row.get("has_recent_session")) else 0.0

        age_days = self._age_days(now_utc, row.get("created_at_utc"))
        freshness_score = self.weights.freshness_max * max(0.0, 1.0 - (age_days / 365.0))

        return (
            pinned_score
            + deadline_score
            + hints_score
            + stage_score
            + momentum_score
            + freshness_score
        )

    def load(self, *, in_today_ids: set[int], limit: int = SUGGESTION_MAX_ITEMS) -> list[SuggestionItem]:
        with db_session() as s:
            result = list_suggestion_candidates(s)
        if not result.success or not result.data:
            return []

        now_utc = datetime.now(timezone.utc)
        rows: list[SuggestionItem] = []
        for raw in result.data:
            todo_id = int(raw["id"])
            if todo_id in in_today_ids:
                continue
            score = self._score(raw, now_utc=now_utc)
            rows.append(
                SuggestionItem(
                    id=todo_id,
                    title=str(raw.get("title") or "?"),
                    project_title=raw.get("project_title"),
                    track_title=raw.get("track_title"),
                    pinned=bool(raw.get("pinned")),
                    deadline_utc=as_utc_aware(raw.get("deadline_utc")),
                    created_at_utc=as_utc_aware(raw.get("created_at_utc")),
                    current_stage=int(raw.get("current_stage") or 0),
                    total_stages=max(1, int(raw.get("total_stages") or 1)),
                    project_pinned=bool(raw.get("project_pinned")),
                    project_willingness_hint=int(raw.get("project_willingness_hint") or 0),
                    project_importance_hint=int(raw.get("project_importance_hint") or 0),
                    project_urgency_hint=int(raw.get("project_urgency_hint") or 0),
                    has_recent_session=bool(raw.get("has_recent_session")),
                    score=float(score),
                    reason_tags=self._reason_tags(raw, now_utc=now_utc),
                    in_today=False,
                    can_add=True,
                )
            )

        rows.sort(
            key=lambda item: (
                float(item["score"]),
                item["created_at_utc"] or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )
        return rows[: max(0, int(limit))]
