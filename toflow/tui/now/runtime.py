"""NOW runtime loop: timer tick, notifier dispatch, UI invalidation."""

from __future__ import annotations

import asyncio
from typing import Callable

from prompt_toolkit import Application

from toflow.ops.result import Result
from toflow.tui.now.notifier import activate_terminal_macos, ring
from toflow.tui.now.state import NowState
from toflow.tui.now.types import TimerEvent, TimerState


async def run_timer_runtime(
    *,
    now: NowState,
    app: Application,
    on_result: Callable[[Result], None] | None = None,
    tick_interval_seconds: float = 0.1,
) -> None:
    """Run NOW timer updates and event side effects in background."""
    interval = max(0.01, float(tick_interval_seconds))
    while True:
        await asyncio.sleep(interval)

        timer = now.timer_service
        prev_state = timer.state
        prev_remaining = timer.remaining_seconds

        events = now.timer_tick()

        if (
            prev_state == TimerState.RUNNING
            and timer.state in (TimerState.RUNNING, TimerState.IDLE)
            and timer.remaining_seconds != prev_remaining
        ):
            app.invalidate()

        if not events:
            continue

        for event in events:
            ring(app)
            if event == TimerEvent.WORK_TIME_UP:
                activate_terminal_macos()
            result = now.handle_timer_event(event)
            if result is not None and on_result is not None:
                on_result(result)

        app.invalidate()
