from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, Footer, Input, Label, Static

from ...services.luks_service import LuksService
from .base import OperatorScreen


class LuksScreen(OperatorScreen):
    BINDINGS = [Binding("escape", "dismiss", "Back")]

    DEFAULT_CSS = """
    LuksScreen {
        background: $background;
        padding: 1 4;
    }
    LuksScreen #title {
        color: $primary;
        text-style: bold;
        text-align: center;
        padding-bottom: 1;
    }
    LuksScreen .meta {
        color: $text-muted;
    }
    LuksScreen #status {
        padding: 1 0;
        color: $text;
    }
    LuksScreen #result {
        min-height: 1;
        color: $success;
        padding-top: 1;
    }
    LuksScreen .btn-row {
        padding-top: 1;
        height: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._svc = LuksService()

    def compose(self) -> ComposeResult:
        yield self.webui_warning_banner()
        yield Static("LUKS OPERATOR PANEL", id="title")
        yield Static("", id="mode", classes="meta")
        yield Static("", id="container", classes="meta")
        yield Static("", id="mount-point", classes="meta")
        yield Static("", id="status")
        yield Label("Passphrase (optional)", classes="meta")
        yield Input(password=True, id="passphrase")
        with Horizontal(classes="btn-row"):
            yield Button("Open Local Container", id="mount-btn", variant="primary")
            yield Button("Close Local Container", id="unmount-btn")
            yield Button("Restricted Clear", id="clear-btn", variant="error")
        yield Static("", id="result")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        cfg = self._svc.layer.cfg
        st = self._svc.status()
        self.query_one("#mode", Static).update(f"Mode: {cfg.mode.value}")
        self.query_one("#container", Static).update(f"Container: {cfg.container_path}")
        self.query_one("#mount-point", Static).update(f"Mount point: {cfg.mount_point}")
        mounted = "mounted" if st.mounted else "unmounted"
        self.query_one("#status", Static).update(f"Local container status: {mounted}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "mount-btn":
            pw = self.query_one("#passphrase", Input).value
            result = self._svc.mount(pw)
            if result.success:
                self.query_one("#result", Static).update("local container opened")
            else:
                self.query_one("#result", Static).update("operation failed")
        elif event.button.id == "unmount-btn":
            if self._svc.unmount():
                self.query_one("#result", Static).update("local container closed")
            else:
                self.query_one("#result", Static).update("operation failed")
        elif event.button.id == "clear-btn":
            if self._svc.restricted_clear():
                self.query_one("#result", Static).update(
                    "local access path cleared (best-effort)"
                )
            else:
                self.query_one("#result", Static).update("operation failed")
        self._refresh()
