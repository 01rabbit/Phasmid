from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class PhasmidHeader(Widget):
    DEFAULT_CSS = """
    PhasmidHeader {
        height: 3;
        background: $primary;
        color: $background;
        padding: 0 2;
        dock: top;
    }
    PhasmidHeader .title {
        text-style: bold;
        width: 1fr;
    }
    PhasmidHeader .subtitle {
        color: $background 70%;
        width: 1fr;
        text-align: right;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("PHASMID  ·  JANUS EIDOLON SYSTEM", classes="title")
        yield Static("coercion-aware deniable storage", classes="subtitle")
