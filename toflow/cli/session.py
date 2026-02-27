"""Session CLI commands."""

import sys
from typing import Annotated

import typer

from toflow.cli._common import run_result
from toflow.database import db_session
from toflow.ops import delete_session, save_session, update_session_description
from toflow.utils import parse_local_to_utc


app = typer.Typer(help="Session 番茄钟记录")


@app.command()
def add(
    todo: Annotated[int, typer.Option("--todo", "-t", help="关联的 Todo ID")],
    duration: Annotated[int, typer.Option("--duration", "-d", help="持续分钟数")],
    started: Annotated[str, typer.Option("--started", "-s", help="开始时间，本地时间")],
    ended: Annotated[str | None, typer.Option("--ended", "-e", help="结束时间，本地时间")] = None,
    title: Annotated[str | None, typer.Option("--title", help="标题")] = None,
    description: Annotated[str | None, typer.Option("--description", help="描述")] = None,
) -> None:
    """新增 Session。"""
    started_utc = parse_local_to_utc(started)
    ended_utc = parse_local_to_utc(ended) if ended else None
    with db_session() as s:
        result = save_session(
            s,
            todo_item_id=todo,
            duration_minutes=duration,
            started_at_utc=started_utc,
            ended_at_utc=ended_utc,
            title=title,
            description=description,
        )
        run_result(result)


@app.command()
def delete(id: Annotated[int, typer.Argument(help="Session ID")]) -> None:
    """删除 Session。"""
    with db_session() as s:
        result = delete_session(s, id)
        run_result(result)


@app.command()
def update(
    id: Annotated[int, typer.Argument(help="Session ID")],
    description: Annotated[str | None, typer.Option("--description", "-d", help="描述")] = None,
) -> None:
    """更新 Session 描述。"""
    if description is None:
        print("请指定 --description", file=sys.stderr)
        raise typer.Exit(1)
    with db_session() as s:
        result = update_session_description(s, id, description)
        run_result(result)
