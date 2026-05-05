from __future__ import annotations

from collections import deque
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class EventLog(Widget):
    DEFAULT_CSS = """
    EventLog {
        height: 6;
        border: solid $primary 30%;
        padding: 0 1;
    }
    EventLog RichLog {
        height: 1fr;
        background: transparent;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="event-rich-log", highlight=True, markup=True, max_lines=100)

    def log_event(self, message: str, level: str = "info") -> None:
        colors = {"info": "dim", "ok": "green", "warn": "yellow", "error": "red"}
        color = colors.get(level, "dim")
        ts = datetime.now().strftime("%H:%M:%S")
        rich_log = self.query_one(RichLog)
        rich_log.write(f"[dim]{ts}[/dim] [{color}]{message}[/{color}]")
