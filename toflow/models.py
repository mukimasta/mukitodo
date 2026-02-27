"""ORM models. Schema per DEVELOP_cn.md."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, ForeignKey, DateTime, Boolean, Integer, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from toflow.database import Base


@dataclass(frozen=True)
class FieldSpec:
    """Editable field declaration for Editable protocol."""
    field: str
    label: str
    widget: str  # "text" | "chip" | "date" | "select" | "stage"
    options: list[str] | None = None


# ---------------------------------------------------------------------------
# Mixins (field reuse)
# ---------------------------------------------------------------------------


class TimestampMixin:
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ArchivableMixin:
    """archived_at_utc: NULL = not archived, non-null = archived. No archived bool field."""

    archived_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OrderableMixin:
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StatusMixin:
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------


class Track(Base, TimestampMixin, ArchivableMixin, OrderableMixin, StatusMixin):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def allowed_statuses(self) -> list[str]:
        return ["active", "sleeping"]

    def editable_fields(self) -> list[FieldSpec]:
        return [
            FieldSpec("title", "Title", "text"),
            FieldSpec("description", "Desc", "text"),
        ]


# ---------------------------------------------------------------------------
# Project (Structure Project / Box Project Idea)
# parent_id nullable: NULL = Box Idea (Box Ideas), FK -> tracks.id
# ---------------------------------------------------------------------------


class Project(Base, TimestampMixin, ArchivableMixin, OrderableMixin, StatusMixin):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "(pinned = false) OR (status = 'active')",
            name="project_pinned_requires_active",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("tracks.id"), nullable=True
    )  # NULL = Box Idea
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    willingness_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    importance_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urgency_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def allowed_statuses(self) -> list[str]:
        return ["active", "sleeping", "cancelled", "finished"]

    def editable_fields(self) -> list[FieldSpec]:
        return [
            FieldSpec("title", "Title", "text"),
            FieldSpec("description", "Desc", "text"),
            FieldSpec("deadline_utc", "Deadline", "date"),
            FieldSpec("willingness_hint", "Will", "chip", options=["0", "1", "2", "3"]),
            FieldSpec("importance_hint", "Imp", "chip", options=["0", "1", "2", "3"]),
            FieldSpec("urgency_hint", "Urg", "chip", options=["0", "1", "2", "3"]),
        ]


# ---------------------------------------------------------------------------
# TodoItem (Structure Todo / Box Todo)
# parent_id nullable: NULL = Box Todo, FK -> projects.id
# ---------------------------------------------------------------------------


class TodoItem(Base, TimestampMixin, ArchivableMixin, OrderableMixin, StatusMixin):
    __tablename__ = "todo_items"
    __table_args__ = (
        CheckConstraint(
            "(status = 'done' AND finished_at_utc IS NOT NULL)"
            " OR (status != 'done' AND finished_at_utc IS NULL)",
            name="todo_item_finished_consistency",
        ),
        CheckConstraint("total_stages >= 1", name="todo_item_total_stages_min_1"),
        CheckConstraint(
            "current_stage >= 0 AND current_stage <= total_stages",
            name="todo_item_stage_range",
        ),
        CheckConstraint(
            "(pinned = false) OR (status = 'active')",
            name="todo_item_pinned_requires_active",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )  # NULL = Box Todo
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deadline_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_stages: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def allowed_statuses(self) -> list[str]:
        return ["active", "done", "sleeping", "cancelled"]

    def editable_fields(self) -> list[FieldSpec]:
        return [
            FieldSpec("title", "Title", "text"),
            FieldSpec("description", "Desc", "text"),
            FieldSpec("url", "URL", "text"),
            FieldSpec("deadline_utc", "Deadline", "date"),
            FieldSpec("current_stage", "Stage", "stage"),
        ]


# ---------------------------------------------------------------------------
# NowTodayItem (NOW Today queue)
# ---------------------------------------------------------------------------


class NowTodayItem(Base):
    __tablename__ = "now_today"
    __table_args__ = (
        CheckConstraint("planned_sessions >= 1 AND planned_sessions < 10", name="now_today_planned_range"),
        CheckConstraint("completed_sessions >= 0", name="now_today_completed_non_negative"),
        CheckConstraint("completed_sessions <= planned_sessions", name="now_today_completed_le_planned"),
        CheckConstraint("order_index >= 0", name="now_today_order_non_negative"),
    )

    todo_id: Mapped[int] = mapped_column(
        ForeignKey("todo_items.id"), primary_key=True
    )
    planned_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# Session (Now Action Session)
# todo_item_id NOT NULL
# ---------------------------------------------------------------------------


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    todo_item_id: Mapped[int] = mapped_column(
        ForeignKey("todo_items.id"), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def editable_fields(self) -> list[FieldSpec]:
        return [
            FieldSpec("description", "Desc", "text"),
        ]
