"""Common CLI helpers."""

import sys
from datetime import datetime

import typer

from toflow.cli.formatters import (
    format_project,
    format_session_timeline,
    format_track,
    format_todo,
)
from toflow.ops.result import Result
from toflow.utils import parse_local_to_utc


def run_result(result: Result) -> None:
    """Handle Result: success -> stdout, failure -> stderr + exit 1."""
    if result.success:
        if result.message:
            print(result.message)
    else:
        print(result.message or "Operation failed", file=sys.stderr)
        raise typer.Exit(1)


def parse_deadline(s: str | None) -> datetime | None:
    """Parse deadline string to UTC. Returns None if s is None or empty."""
    if not s:
        return None
    return parse_local_to_utc(s)


__all__ = [
    "format_project",
    "format_session_timeline",
    "format_track",
    "format_todo",
    "parse_deadline",
    "run_result",
]
