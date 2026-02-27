"""Todo CLI commands."""

import sys
from typing import Annotated

import typer

from toflow.cli._common import format_todo, parse_deadline, run_result
from toflow.database import db_session
from toflow.ops import (
    apply_stage_delta,
    create_entity,
    delete_entity,
    get_entity,
    list_entities,
    reparent,
    set_archived,
    set_pinned,
    set_status,
    update_entity,
)
from toflow.ops.result import Result
from toflow.registry import EntityType


app = typer.Typer(help="Todo 待办管理")


@app.command()
def add(
    title: Annotated[str, typer.Argument(help="Todo 标题")],
    parent_id: Annotated[int | None, typer.Option("--parent-id", help="所属 Project ID，省略则为 Box Todo")] = None,
    total_stages: Annotated[int | None, typer.Option("--total-stages", help="总阶段数")] = None,
) -> None:
    """新增 Todo。"""
    with db_session() as s:
        kwargs = {"title": title.strip()}
        if parent_id is not None:
            kwargs["parent_id"] = parent_id
        if total_stages is not None:
            kwargs["total_stages"] = total_stages
        result = create_entity(s, EntityType.TODO, **kwargs)
        run_result(result)


@app.command(name="list")
def list_todos(
    parent_id: Annotated[
        int | None,
        typer.Option("--parent-id", help="Project ID，省略则列出 Box Todos"),
    ] = None,
) -> None:
    """列出 Box Todos 或指定 Project 下的 Todos。"""
    with db_session() as s:
        result = list_entities(s, EntityType.TODO, parent_id=parent_id)
        run_result(result)
        if result.success and result.data:
            for item in result.data:
                print(format_todo(item))


@app.command()
def update(
    id: Annotated[int, typer.Argument(help="Todo ID")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="标题")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="描述")] = None,
    url: Annotated[str | None, typer.Option("--url", help="链接")] = None,
    deadline: Annotated[str | None, typer.Option("--deadline", help="截止日期，本地时间")] = None,
    total_stages: Annotated[int | None, typer.Option("--total-stages", help="总阶段数")] = None,
) -> None:
    """更新 Todo。"""
    updates = {}
    if title is not None:
        updates["title"] = title.strip()
    if description is not None:
        updates["description"] = description.strip() or None
    if url is not None:
        updates["url"] = url.strip() or None
    if deadline is not None:
        updates["deadline_utc"] = parse_deadline(deadline)
    if total_stages is not None:
        updates["total_stages"] = total_stages
    if not updates:
        print("至少指定一个要更新的字段", file=sys.stderr)
        raise typer.Exit(1)
    with db_session() as s:
        result = update_entity(s, EntityType.TODO, id, **updates)
        run_result(result)


@app.command()
def status(
    id: Annotated[int, typer.Argument(help="Todo ID")],
    new_status: Annotated[str, typer.Argument(help="active | done | sleeping | cancelled")],
) -> None:
    """设置 Todo 状态。"""
    with db_session() as s:
        result = set_status(s, EntityType.TODO, id, new_status)
        run_result(result)


@app.command()
def done(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """标记 Todo 为完成。"""
    with db_session() as s:
        result = set_status(s, EntityType.TODO, id, "done")
        run_result(result)


@app.command()
def undo(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """撤销完成，恢复为 active。"""
    with db_session() as s:
        result = set_status(s, EntityType.TODO, id, "active")
        run_result(result)


@app.command()
def stage(
    id: Annotated[int, typer.Argument(help="Todo ID")],
    action: Annotated[str, typer.Argument(help="set | add | sub")],
    n: Annotated[int, typer.Argument(help="阶段数")],
) -> None:
    """设置或推进阶段。set: 直接设为 n；add: 增加 n；sub: 减少 n。"""
    with db_session() as s:
        if action == "set":
            ent = get_entity(s, EntityType.TODO, id)
            if not ent:
                run_result(Result(False, None, f"Todo {id} not found"))
            total = ent.total_stages or 1
            cur = ent.current_stage or 0
            delta = max(0, min(n, total)) - cur
            result = apply_stage_delta(s, EntityType.TODO, id, delta)
        elif action == "add":
            result = apply_stage_delta(s, EntityType.TODO, id, n)
        elif action == "sub":
            result = apply_stage_delta(s, EntityType.TODO, id, -n)
        else:
            print(f"未知操作: {action}，应为 set、add 或 sub", file=sys.stderr)
            raise typer.Exit(1)
        run_result(result)


@app.command(name="reparent")
def reparent_todo(
    id: Annotated[int, typer.Argument(help="Todo ID")],
    parent_id: Annotated[int, typer.Argument(help="目标 Project ID")],
) -> None:
    """移动 Todo 到指定 Project。"""
    with db_session() as s:
        result = reparent(s, EntityType.TODO, id, parent_id)
        run_result(result)


@app.command()
def pin(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """置顶 Todo。"""
    with db_session() as s:
        result = set_pinned(s, EntityType.TODO, id, True)
        run_result(result)


@app.command()
def unpin(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """取消置顶 Todo。"""
    with db_session() as s:
        result = set_pinned(s, EntityType.TODO, id, False)
        run_result(result)


@app.command()
def archive(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """归档 Todo。"""
    with db_session() as s:
        result = set_archived(s, EntityType.TODO, id, True)
        run_result(result)


@app.command()
def unarchive(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """解档 Todo。"""
    with db_session() as s:
        result = set_archived(s, EntityType.TODO, id, False)
        run_result(result)


@app.command()
def delete(id: Annotated[int, typer.Argument(help="Todo ID")]) -> None:
    """删除 Todo。"""
    with db_session() as s:
        result = delete_entity(s, EntityType.TODO, id)
        run_result(result)
