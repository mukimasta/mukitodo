# Developer Guide

**[English](./DEVELOPER.md)** | [简体中文](./DEVELOPER_zh.md)

This document details the system architecture and engineering implementation of ToFlow, aimed at helping developers understand its design philosophy and code structure.

## 1. Project Structure

```text
.
├── pyproject.toml          # uv environment management (project config)
├── README.md               # README documentation
├── CHANGELOG.md            # CHANGELOG documentation
├── main.py                 # Legacy entry point (optional)
├── toflow/
│   ├── __init__.py         # Package init
│   ├── cli.py              # CLI entry point ("toflow" command)
│   ├── actions.py          # Business logic
│   ├── database.py         # Database connection & setup
│   ├── models.py           # SQLAlchemy ORM models
│   └── tui/                # prompt-toolkit Terminal UI Application
│       ├── __init__.py     # TUI package core
│       ├── app.py          # Key bindings, layout, TUI app launcher
│       ├── layout_manager.py    # Dynamic layout computation
│       ├── renderer.py     # Pure rendering routines
│       ├── states/         # State management modules
│       │   ├── app_state.py        # Top-level state coordinator
│       │   ├── input_state.py      # Input MODE state
│       │   ├── now_state.py        # NOW VIEW state
│       │   ├── structure_state.py  # STRUCTURE VIEW state
│       │   ├── info_state.py       # INFO VIEW state
│       │   ├── timeline_state.py   # TIMELINE VIEW state
│       │   ├── archive_state.py    # ARCHIVE VIEW state
│       │   ├── box_state.py        # BOX VIEW state
│       │   └── message_holder.py   # Message/Result manager
```

### Code Style
Self-explanatory code. Minimize unnecessary comments; use English comments only when necessary. Avoid abbreviations unless standard (e.g., use `current_project_id` instead of `cur_proj_id`).

## 2. Architecture Philosophy

### I. Overall Philosophy: Unidirectional Layering

```mermaid
graph TD
    Renderer[Renderer / Layout Manager] -->|Render| State
    State[State Layer] -->|Call| App
    App[App] -->|Interact| Actions
    Actions[Actions] -->|Use| Models
    Models[Models] -->|Map| Database
```

**Core Principle**: Each layer only depends on the layer below it. No circular dependencies.


## 3. Database Design

SQLite Database Path: `~/.toflow/toflow.db`

### Entities

**Track**:
*   `id` PRIMARY KEY
*   `name` NOT NULL
*   `description`
*   `status` NOT NULL, DEFAULT 'active' (active / sleeping)
*   `archived`: boolean, DEFAULT FALSE
*   `created_at_utc` NOT NULL
*   `archived_at_utc`
*   `order_index`

**Project**:
*   `id` PRIMARY KEY
*   `track_id` NOT NULL, FOREIGN KEY
*   `name` NOT NULL
*   `description`
*   `deadline_utc`
*   `willingness_hint` (0-3)
*   `importance_hint` (0-3)
*   `urgency_hint` (0-3)
*   `status` NOT NULL, DEFAULT 'active' (active / sleeping / cancelled / finished)
*   `pinned`: boolean, DEFAULT FALSE (Constraint: pinned => status='active')
*   `archived`: boolean, DEFAULT FALSE
*   `created_at_utc` NOT NULL
*   `started_at_utc`
*   `finished_at_utc`
*   `archived_at_utc`
*   `order_index`

**TodoItem** (Structure Todo / Box Todo):
*   `id` PRIMARY KEY
*   `project_id` FOREIGN KEY (nullable, NULL means Box Todo)
*   `name` NOT NULL
*   `description`
*   `url`
*   `deadline_utc`
*   `status` NOT NULL, DEFAULT 'active' (active / done / sleeping / cancelled)
*   `total_stages`: int, DEFAULT 1
*   `current_stage`: int, DEFAULT 0
*   `pinned`: boolean, DEFAULT FALSE (Constraint: pinned => status='active')
*   `archived`: boolean, DEFAULT FALSE
*   `created_at_utc` NOT NULL
*   `completed_at_utc`
*   `archived_at_utc`
*   `order_index`

**IdeaItem**:
*   `id` PRIMARY KEY
*   `name` NOT NULL
*   `description`
*   `maturity_hint` (0-3)
*   `willingness_hint` (0-3)
*   `status` NOT NULL, DEFAULT 'active' (active / sleeping / deprecated / promoted)
*   `archived`: boolean, DEFAULT FALSE
*   `created_at_utc` NOT NULL
*   `archived_at_utc`
*   `promoted_at_utc`
*   `promoted_to_project_id` FOREIGN KEY (nullable)
*   `order_index`

**NowSession**: (Now Action Session)
*   `id` PRIMARY KEY
*   `description`
*   `project_id` FOREIGN KEY (nullable)
*   `todo_item_id` FOREIGN KEY (nullable)
*   `duration_minutes` NOT NULL
*   `started_at_utc` NOT NULL
*   `ended_at_utc` (NULL means saving on-going session)
*   Constraint: Only one of `project_id` or `todo_item_id` should be provided.

## 4. Environment & Dependencies

*   **Management**: `uv`
*   **Core**: `typer` (CLI), `prompt-toolkit` (TUI), `sqlalchemy` (ORM).
