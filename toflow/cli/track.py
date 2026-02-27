"""Track CLI commands."""

import sys
from typing import Annotated

import typer

from toflow.cli._common import format_project, format_track, run_result
from toflow.database import db_session
from toflow.ops import create_entity, delete_entity, list_entities, set_archived, set_status, update_entity
from toflow.registry import EntityType


app = typer.Typer(help="Track 轨道管理")


@app.command()
def add(title: Annotated[str, typer.Argument(help="Track 标题")]) -> None:
    """新增 Track。"""
    with db_session() as s:
        result = create_entity(s, EntityType.TRACK, title=title.strip())
        run_result(result)


@app.command(name="list")
def list_tracks() -> None:
    """列出所有 Track（自身）。"""
    with db_session() as s:
        result = list_entities(s, EntityType.TRACK)
        run_result(result)
        if result.success and result.data:
            for item in result.data:
                print(format_track(item))


@app.command(name="show")
def show_track(
    id: Annotated[int, typer.Argument(help="Track ID")],
) -> None:
    """显示该 Track 下的 Projects（子集）。"""
    with db_session() as s:
        result = list_entities(s, EntityType.PROJECT, parent_id=id)
        run_result(result)
        if result.success and result.data:
            for item in result.data:
                print(format_project(item))


@app.command()
def update(
    id: Annotated[int, typer.Argument(help="Track ID")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="标题")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="描述")] = None,
) -> None:
    """更新 Track。"""
    updates = {}
    if title is not None:
        updates["title"] = title.strip()
    if description is not None:
        updates["description"] = description.strip() or None
    if not updates:
        print("至少指定一个要更新的字段", file=sys.stderr)
        raise typer.Exit(1)
    with db_session() as s:
        result = update_entity(s, EntityType.TRACK, id, **updates)
        run_result(result)


@app.command()
def status(
    id: Annotated[int, typer.Argument(help="Track ID")],
    new_status: Annotated[str, typer.Argument(help="active | sleeping")],
) -> None:
    """设置 Track 状态。"""
    with db_session() as s:
        result = set_status(s, EntityType.TRACK, id, new_status)
        run_result(result)


@app.command()
def archive(id: Annotated[int, typer.Argument(help="Track ID")]) -> None:
    """归档 Track。"""
    with db_session() as s:
        result = set_archived(s, EntityType.TRACK, id, True)
        run_result(result)


@app.command()
def unarchive(id: Annotated[int, typer.Argument(help="Track ID")]) -> None:
    """解档 Track。"""
    with db_session() as s:
        result = set_archived(s, EntityType.TRACK, id, False)
        run_result(result)


@app.command()
def delete(id: Annotated[int, typer.Argument(help="Track ID")]) -> None:
    """删除 Track（级联删除下属 Project 与 Todo）。"""
    with db_session() as s:
        result = delete_entity(s, EntityType.TRACK, id)
        run_result(result)
