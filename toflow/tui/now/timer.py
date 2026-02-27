"""Timer service for NOW focus/rest flows."""

from __future__ import annotations

import time

from toflow.tui.now.types import TimerEvent, TimerMode, TimerState


class TimerService:
    """Countdown timer with one-shot events for NOW."""

    def __init__(self) -> None:
        self.mode: TimerMode = TimerMode.WORK
        self.state: TimerState = TimerState.IDLE

        self.target_seconds: int = 25 * 60
        self.remaining_seconds: int = 25 * 60

        self._started_monotonic: float | None = None
        self._base_seconds_on_start: int = self.target_seconds

        self._work_warned_5min: bool = False
        self._work_timeup_latched: bool = False

    def arm(self, mode: TimerMode, total_seconds: int) -> None:
        total = max(1, int(total_seconds))
        self.mode = mode
        self.state = TimerState.IDLE
        self.target_seconds = total
        self.remaining_seconds = total
        self._started_monotonic = None
        self._base_seconds_on_start = total
        self._work_warned_5min = False
        if mode == TimerMode.REST:
            self._work_timeup_latched = False

    def start(self) -> None:
        if self.state != TimerState.IDLE:
            return
        if self.mode == TimerMode.WORK and self._work_timeup_latched:
            return
        self._base_seconds_on_start = int(self.remaining_seconds)
        self._started_monotonic = time.monotonic()
        self.state = TimerState.RUNNING

    def pause(self) -> None:
        if self.state != TimerState.RUNNING:
            return
        self.update()
        self._started_monotonic = None
        self._base_seconds_on_start = int(self.remaining_seconds)
        self.state = TimerState.PAUSED

    def resume(self) -> None:
        if self.state != TimerState.PAUSED:
            return
        self._base_seconds_on_start = int(self.remaining_seconds)
        self._started_monotonic = time.monotonic()
        self.state = TimerState.RUNNING

    def toggle(self) -> None:
        if self.state == TimerState.IDLE:
            self.start()
            return
        if self.state == TimerState.RUNNING:
            self.pause()
            return
        if self.state == TimerState.PAUSED:
            self.resume()

    def reset(self) -> None:
        self.state = TimerState.IDLE
        self.remaining_seconds = int(self.target_seconds)
        self._started_monotonic = None
        self._base_seconds_on_start = int(self.target_seconds)
        self._work_warned_5min = False
        self._work_timeup_latched = False

    def adjust_total(
        self,
        *,
        delta_seconds: int,
        min_seconds: int,
        max_seconds: int,
        allow_running: bool = False,
    ) -> bool:
        if self.state == TimerState.RUNNING and not allow_running:
            return False
        if self.mode == TimerMode.WORK and self._work_timeup_latched:
            return False

        current = int(self.target_seconds)
        target = max(int(min_seconds), min(int(max_seconds), current + int(delta_seconds)))
        if target == current:
            return False

        self.target_seconds = target
        if self.state == TimerState.IDLE:
            self.remaining_seconds = target
            self._base_seconds_on_start = target
        elif self.state == TimerState.PAUSED:
            self.remaining_seconds = min(target, self.remaining_seconds)
            self._base_seconds_on_start = self.remaining_seconds
        else:
            self.remaining_seconds = min(target, self.remaining_seconds)

        return True

    def update(self, now_monotonic: float | None = None) -> list[TimerEvent]:
        if self.state != TimerState.RUNNING:
            return []
        if self._started_monotonic is None:
            return []

        now_ts = now_monotonic if now_monotonic is not None else time.monotonic()
        elapsed = max(0, int(round(now_ts - self._started_monotonic)))
        old_seconds = int(self.remaining_seconds)
        self.remaining_seconds = max(0, int(self._base_seconds_on_start) - elapsed)

        events: list[TimerEvent] = []
        if (
            self.mode == TimerMode.WORK
            and not self._work_warned_5min
            and old_seconds > 5 * 60
            and self.remaining_seconds <= 5 * 60
        ):
            self._work_warned_5min = True
            events.append(TimerEvent.WORK_5MIN_LEFT)

        if self.remaining_seconds == 0:
            self.state = TimerState.IDLE
            self._started_monotonic = None
            self._base_seconds_on_start = 0
            if self.mode == TimerMode.WORK:
                self._work_timeup_latched = True
                events.append(TimerEvent.WORK_TIME_UP)
            else:
                events.append(TimerEvent.REST_TIME_UP)

        return events

    @property
    def work_timeup_latched(self) -> bool:
        return self._work_timeup_latched
