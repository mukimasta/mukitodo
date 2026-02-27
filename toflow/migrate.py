"""Schema migrations for v2 database."""

import sqlite3
import sys
from pathlib import Path

from toflow.database import DB_PATH


def _needs_now_today_planned_migration(cursor: sqlite3.Cursor) -> bool:
    """Check if now_today table has old constraint (<= 5)."""
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='now_today'"
    )
    row = cursor.fetchone()
    if row is None:
        return False
    sql = row[0] or ""
    return "planned_sessions <= 5" in sql


def migrate_now_today_planned_sessions() -> bool:
    """
    Migrate now_today planned_sessions constraint from <= 5 to < 10.
    Returns True if migration was performed, False if not needed.
    """
    if not DB_PATH.exists():
        return False

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    try:
        if not _needs_now_today_planned_migration(cur):
            return False

        con.execute("BEGIN")
        cur.execute(
            """CREATE TABLE now_today_new (
                todo_id INTEGER NOT NULL,
                planned_sessions INTEGER NOT NULL DEFAULT 1,
                completed_sessions INTEGER NOT NULL DEFAULT 0,
                order_index INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (todo_id),
                FOREIGN KEY (todo_id) REFERENCES todo_items (id),
                CHECK (planned_sessions >= 1 AND planned_sessions < 10),
                CHECK (completed_sessions >= 0),
                CHECK (completed_sessions <= planned_sessions),
                CHECK (order_index >= 0)
            )"""
        )
        cur.execute("INSERT INTO now_today_new SELECT * FROM now_today")
        cur.execute("DROP TABLE now_today")
        cur.execute("ALTER TABLE now_today_new RENAME TO now_today")
        con.commit()
        return True
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def run_migrate() -> None:
    """Run schema migrations on v2 database."""
    migrated = migrate_now_today_planned_sessions()
    if migrated:
        print("Migrated now_today planned_sessions constraint (5 -> <10)", file=sys.stderr)
        print(f"DB: {DB_PATH}", file=sys.stderr)
    else:
        print("No migration needed.", file=sys.stderr)
