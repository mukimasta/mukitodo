"""Project CLI commands."""

import sys
from typing import Annotated

import typer

from toflow.cli._common import format_project, format_todo, parse_deadline, run_result
from toflow.database import db_session
from toflow.ops import (
    create_entity,
    delete_entity,
    list_entities,
    reparent,
    set_archived,
    set_pinned,
    set_status,
    update_entity,
)
from toflow.registry import EntityType


app = typer.Typer(help="Project 项目管理")


@app.command()
def add(
    title: Annotated[str, typer.Argument(help="Project 标题")],
    parent_id: Annotated[int | None, typer.Option("--parent-id", help="所属 Track ID，省略则为 Box Project")] = None,
) -> None:
    """新增 Project。"""
    with db_session() as s:
        kwargs = {"title": title.strip()}
        if parent_id is not None:
            kwargs["parent_id"] = parent_id
        result = create_entity(s, EntityType.PROJECT, **kwargs)
        run_result(result)


@app.command(name="list")
def list_projects(
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Track ID，省略则列出 Box Projects"),
    ] = None,
) -> None:
    """列出 Box Projects 或指定 Track 下的 Projects。"""
    with db_session() as s:
        result = list_entities(s, EntityType.PROJECT, parent_id=parent_id)
        run_result(result)
        if result.success and result.data:
            for item in result.data:
                print(format_project(item))


@app.command(name="show")
def show_project(
    id: Annotated[int, typer.Argument(help="Project ID")],
) -> None:
    """显示该 Project 下的 Todos（子集）。"""
    with db_session() as s:
        result = list_entities(s, EntityType.TODO, parent_id=id)
        run_result(result)
        if result.success and result.data:
            for item in result.data:
                print(format_todo(item))


@app.command()
def update(
    id: Annotated[int, typer.Argument(help="Project ID")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="标题")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="描述")] = None,
    deadline: Annotated[str | None, typer.Option("--deadline", help="截止日期，本地时间")] = None,
    willingness_hint: Annotated[int | None, typer.Option("--willingness-hint", help="意愿 0-3")] = None,
    importance_hint: Annotated[int | None, typer.Option("--importance-hint", help="重要性 0-3")] = None,
    urgency_hint: Annotated[int | None, typer.Option("--urgency-hint", help="紧迫性 0-3")] = None,
) -> None:
    """更新 Project。"""
    updates = {}
    if title is not None:
        updates["title"] = title.strip()
    if description is not None:
        updates["description"] = description.strip() or None
    if deadline is not None:
        updates["deadline_utc"] = parse_deadline(deadline)
    if willingness_hint is not None:
        updates["willingness_hint"] = willingness_hint
    if importance_hint is not None:
        updates["importance_hint"] = importance_hint
    if urgency_hint is not None:
        updates["urgency_hint"] = urgency_hint
    if not updates:
        print("至少指定一个要更新的字段", file=sys.stderr)
        raise typer.Exit(1)
    with db_session() as s:
        result = update_entity(s, EntityType.PROJECT, id, **updates)
        run_result(result)


@app.command()
def status(
    id: Annotated[int, typer.Argument(help="Project ID")],
    new_status: Annotated[str, typer.Argument(help="active | sleeping | cancelled | finished")],
) -> None:
    """设置 Project 状态。"""
    with db_session() as s:
        result = set_status(s, EntityType.PROJECT, id, new_status)
        run_result(result)


@app.command(name="reparent")
def reparent_project(
    id: Annotated[int, typer.Argument(help="Project ID")],
    parent_id: Annotated[int, typer.Argument(help="目标 Track ID")],
) -> None:
    """移动 Project 到指定 Track。"""
    with db_session() as s:
        result = reparent(s, EntityType.PROJECT, id, parent_id)
        run_result(result)


@app.command()
def pin(id: Annotated[int, typer.Argument(help="Project ID")]) -> None:
    """置顶 Project。"""
    with db_session() as s:
        result = set_pinned(s, EntityType.PROJECT, id, True)
        run_result(result)


@app.command()
def unpin(id: Annotated[int, typer.Argument(help="Project ID")]) -> None:
    """取消置顶 Project。"""
    with db_session() as s:
        result = set_pinned(s, EntityType.PROJECT, id, False)
        run_result(result)


@app.command()
def archive(id: Annotated[int, typer.Argument(help="Project ID")]) -> None:
    """归档 Project。"""
    with db_session() as s:
        result = set_archived(s, EntityType.PROJECT, id, True)
        run_result(result)


@app.command()
def unarchive(id: Annotated[int, typer.Argument(help="Project ID")]) -> None:
    """解档 Project。"""
    with db_session() as s:
        result = set_archived(s, EntityType.PROJECT, id, False)
        run_result(result)


@app.command()
def delete(id: Annotated[int, typer.Argument(help="Project ID")]) -> None:
    """删除 Project（级联删除下属 Todo）。"""
    with db_session() as s:
        result = delete_entity(s, EntityType.PROJECT, id)
        run_result(result)
