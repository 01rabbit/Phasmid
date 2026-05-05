from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class WarningBox(Widget):
    DEFAULT_CSS = """
    WarningBox {
        height: auto;
        border: solid $warning;
        padding: 0 2;
        color: $warning;
        background: $warning 10%;
    }
    WarningBox.error {
        border: solid $error;
        color: $error;
        background: $error 10%;
    }
    """

    def __init__(self, message: str, level: str = "warn", **kwargs):
        super().__init__(**kwargs)
        self._message = message
        self._level = level
        if level == "error":
            self.add_class("error")

    def compose(self) -> ComposeResult:
        prefix = "!" if self._level == "warn" else "✗"
        yield Static(f"{prefix}  {self._message}")
