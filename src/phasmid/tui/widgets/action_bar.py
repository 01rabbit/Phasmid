from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button

_ACTIONS = [
    ("o", "Open"),
    ("c", "Create"),
    ("i", "Inspect"),
    ("f", "Faces"),
    ("g", "Guided"),
    ("a", "Audit"),
    ("d", "Doctor"),
    ("s", "Settings"),
    ("?", "Help"),
    ("q", "Quit"),
]


class ActionBar(Widget):
    DEFAULT_CSS = """
    ActionBar {
        height: 3;
        dock: bottom;
        layout: horizontal;
        background: $panel;
        padding: 0 1;
    }
    ActionBar Button {
        min-width: 8;
        height: 1;
        margin: 1 0;
        background: transparent;
        border: none;
        color: $primary;
        padding: 0 1;
    }
    ActionBar Button:hover {
        background: $primary 20%;
    }
    ActionBar .key-hint {
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        for key, label in _ACTIONS:
            yield Button(f"[dim]{key}[/dim] {label}", id=f"action-{label.lower()}", classes="key-hint")
