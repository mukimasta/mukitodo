"""Archive CLI commands."""

import typer

from toflow.cli._common import format_project, format_track, format_todo, run_result
from toflow.database import db_session
from toflow.ops import list_archived_structure


app = typer.Typer(help="Archive 归档视图")


@app.command(name="list")
def list_archive() -> None:
    """列出所有归档项。"""
    with db_session() as s:
        result = list_archived_structure(s)
        run_result(result)
        if not result.success or not result.data:
            return
        data = result.data
        for item in data.get("tracks", []):
            print("  " + format_track(item["track"]))
            for proj_data in item.get("projects", []):
                print("    " + format_project(proj_data["project"]))
                for todo in proj_data.get("todos", []):
                    print("      " + format_todo(todo))
        for p in data.get("box_projects", []):
            print("  [Box] " + format_project(p))
        for t in data.get("box_todos", []):
            print("  [Box] " + format_todo(t))
