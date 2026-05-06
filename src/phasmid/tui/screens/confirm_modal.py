from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "confirm", "Confirm"),
        Binding("n", "cancel", "Cancel"),
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }
    ConfirmModal #confirm-container {
        width: 54;
        height: auto;
        background: $surface;
        border: solid $warning;
        padding: 2 4;
    }
    ConfirmModal #confirm-title {
        text-style: bold;
        color: $warning;
        text-align: center;
        padding: 0 0 1 0;
    }
    ConfirmModal #confirm-message {
        text-align: center;
        padding: 0 0 2 0;
        color: $text;
    }
    ConfirmModal #confirm-hint {
        color: $text-muted;
        text-align: center;
        text-style: italic;
    }
    """

    def __init__(self, title: str, message: str, **kwargs):
        super().__init__(**kwargs)
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        from textual.containers import Container

        with Container(id="confirm-container"):
            yield Static(self._title, id="confirm-title")
            yield Static(self._message, id="confirm-message")
            yield Static("[y] Confirm   [n] Cancel", id="confirm-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
