"""Box CLI. Direct mount of todo/project with parent_id=None."""

import typer

from toflow.cli import project, todo
from toflow.cli._common import format_project, format_todo, run_result
from toflow.database import db_session
from toflow.ops import list_entities
from toflow.registry import EntityType


app = typer.Typer(help="Box 收集箱 (box todo/project = todo/project，parent_id 省略)")


@app.command(name="list")
def list_box() -> None:
    """Box 概览：Todos + Projects（自身）。"""
    with db_session() as s:
        todos_result = list_entities(s, EntityType.TODO, parent_id=None)
        projs_result = list_entities(s, EntityType.PROJECT, parent_id=None)
        if not todos_result.success:
            run_result(todos_result)
        elif not projs_result.success:
            run_result(projs_result)
        elif todos_result.data or projs_result.data:
            if todos_result.data:
                print("  [Box Todos]")
                for item in todos_result.data:
                    print("   " + format_todo(item))
            if projs_result.data:
                print("  [Box Projects]")
                for item in projs_result.data:
                    print("   " + format_project(item))
        else:
            print("  Box 为空")


app.add_typer(todo.app, name="todo")
app.add_typer(project.app, name="project")
