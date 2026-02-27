"""Best-effort notifier helpers for NOW timer events."""

from __future__ import annotations

import subprocess
import sys

from prompt_toolkit import Application


def ring(app: Application) -> None:
    """Best-effort terminal bell."""
    try:
        app.output.bell()
        return
    except Exception:
        pass
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        return


def activate_terminal_macos() -> None:
    """Best-effort activate iTerm / iTerm2 on macOS."""
    scripts = [
        'tell application "iTerm" to activate',
        'tell application "iTerm2" to activate',
    ]
    for script in scripts:
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break
        except Exception:
            continue
