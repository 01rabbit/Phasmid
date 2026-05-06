from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog, Static


class EventLog(Widget):
    DEFAULT_CSS = """
    EventLog {
        height: 8;
        border: solid $primary 30%;
        padding: 0 0;
    }
    EventLog #event-log-title {
        color: $primary;
        background: $primary 10%;
        padding: 0 1;
        height: 1;
    }
    EventLog RichLog {
        height: 1fr;
        background: transparent;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("OPERATOR LOG", id="event-log-title")
        yield RichLog(id="event-rich-log", highlight=True, markup=True, max_lines=100)

    def log_event(self, message: str, level: str = "info") -> None:
        colors = {"info": "dim", "ok": "green", "warn": "yellow", "error": "red"}
        color = colors.get(level, "dim")
        ts = datetime.now().strftime("%H:%M:%S")
        rich_log = self.query_one(RichLog)
        rich_log.write(f"[dim]{ts}[/dim] [{color}]{message}[/{color}]")
