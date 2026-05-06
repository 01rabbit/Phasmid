from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static


class OpenVesselScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    OpenVesselScreen {
        background: $background;
        padding: 1 4;
    }
    OpenVesselScreen #open-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 0 0 1 0;
    }
    OpenVesselScreen .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    OpenVesselScreen #security-note {
        color: $text-muted;
        text-style: italic;
        padding: 1 0;
    }
    OpenVesselScreen #open-btn {
        margin-top: 2;
        width: 100%;
    }
    """

    _FACE_OPTIONS = [
        ("Disclosure Face 1", "face_1"),
        ("Disclosure Face 2", "face_2"),
    ]

    def __init__(self, vessel_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self._vessel_path = vessel_path

    def compose(self) -> ComposeResult:
        yield Static("OPEN VESSEL", id="open-title")
        yield Label("Vessel path", classes="field-label")
        yield Input(value=self._vessel_path, placeholder="Path to Vessel file", id="vessel-path")
        yield Label("Disclosure Face", classes="field-label")
        yield Select(
            [(label, val) for label, val in self._FACE_OPTIONS],
            id="face-select",
            value="face_1",
        )
        yield Label("Output directory", classes="field-label")
        yield Input(placeholder="~/Documents/output", id="output-dir")
        yield Static(
            "Passphrase is entered securely via the terminal prompt after confirming.",
            id="security-note",
        )
        yield Button("Open Vessel", id="open-btn", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-btn":
            self._attempt_open()

    def _attempt_open(self) -> None:
        path = self.query_one("#vessel-path", Input).value.strip()
        face = self.query_one("#face-select", Select).value
        _ = self.query_one("#output-dir", Input).value.strip()

        if not path:
            self.app.notify("Vessel path is required.", severity="error")
            return

        self.app.notify(
            f"Open workflow: path={path}, face={face}\n\n"
            "Passphrase entry and core decryption require the CLI retrieve command.\n"
            "Use: phasmid retrieve --file <vessel> --out <output>",
            title="Open Vessel",
            severity="information",
            timeout=8,
        )
        self.dismiss()
