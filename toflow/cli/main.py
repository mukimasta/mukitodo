"""ToFlow v02 CLI entry point."""

from typing import Annotated

import typer

from toflow.cli._common import format_project, format_track, run_result
from toflow.cli import track, project, todo, box, session as session_cmd, archive, timeline
from toflow.database import db_session
from toflow.ops.query import list_tracks_with_projects


def _run_tui() -> None:
    """Launch TUI."""
    from toflow.tui import run
    run()


app = typer.Typer(
    name="toflow",
    help="ToFlow - 终端里的结构化 Todo 应用",
    no_args_is_help=False,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    no_view: Annotated[
        bool,
        typer.Option("--no-view", help="不打开 TUI，仅执行 CLI 命令"),
    ] = False,
) -> None:
    """ToFlow v02. 无子命令时打开 TUI，带子命令时执行 CLI。"""
    if ctx.invoked_subcommand is None:
        if no_view:
            # 无子命令且 --no-view：静默退出
            raise typer.Exit(0)
        _run_tui()


@app.command()
def view() -> None:
    """打开 TUI 界面。"""
    _run_tui()


@app.command()
def migrate() -> None:
    """从 v1 toflow.db 迁移到 v2 schema，原库备份为 toflow.db.backup。"""
    from toflow.migrate import run_migrate
    run_migrate()


@app.command(name="list")
def list_cmd() -> None:
    """概览：Track → Project 结构。"""
    with db_session() as s:
        result = list_tracks_with_projects(s)
        run_result(result)
        if result.success and result.data:
            for track_dict, projects in result.data:
                print("  " + format_track(track_dict))
                for p in projects:
                    print("    " + format_project(p))


# Mount subcommands
app.add_typer(track.app, name="track")
app.add_typer(project.app, name="project")
app.add_typer(todo.app, name="todo")
app.add_typer(box.app, name="box")
app.add_typer(session_cmd.app, name="session")
app.add_typer(archive.app, name="archive")
app.add_typer(timeline.app, name="timeline")


def run() -> None:
    """Entry point for python -m toflow.cli."""
    app()


if __name__ == "__main__":
    run()
