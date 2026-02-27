"""Timeline CLI commands."""

from typing import Annotated

import typer

from toflow.cli._common import format_session_timeline, run_result
from toflow.database import db_session
from toflow.ops import list_timeline_records


app = typer.Typer(
    help="Timeline 时间线",
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def timeline(
    ctx: typer.Context,
    limit: Annotated[int | None, typer.Option("--limit", "-n", help="最多显示条数")] = None,
) -> None:
    """查看已完成的 Session 时间线。"""
    if ctx.invoked_subcommand is not None:
        return
    with db_session() as s:
        result = list_timeline_records(s, limit=limit)
        run_result(result)
        if not result.success or not result.data:
            return
        for r in result.data:
            print("  " + format_session_timeline(r))