from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Label, Static

from ...models.vessel import VesselMeta


class FaceManagerScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    FaceManagerScreen {
        background: $background;
        padding: 1 4;
    }
    FaceManagerScreen #face-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 0 0 1 0;
    }
    FaceManagerScreen #face-note {
        color: $text-muted;
        text-style: italic;
        padding: 0 0 1 0;
    }
    FaceManagerScreen #face-table {
        height: 8;
        border: solid $primary 50%;
        margin-bottom: 1;
    }
    FaceManagerScreen .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, vessel: VesselMeta | None = None, **kwargs):
        super().__init__(**kwargs)
        self._vessel = vessel

    def compose(self) -> ComposeResult:
        vessel_name = self._vessel.name if self._vessel else "No vessel selected"
        yield Static("DISCLOSURE FACES", id="face-title")
        yield Static(
            f"Vessel: [bold]{vessel_name}[/bold]\n\n"
            "Face labels are local metadata only. "
            "They do not affect the Vessel file or cryptographic structure.",
            id="face-note",
            markup=True,
        )
        table = DataTable(id="face-table", cursor_type="row")
        yield table
        yield Label("Add face label", classes="field-label")
        yield Input(placeholder="Disclosure Face label (e.g. travel)", id="new-label")
        yield Button("Add Label", id="add-label-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Label", "Note")
        if self._vessel and self._vessel.face_labels:
            for label in self._vessel.face_labels:
                table.add_row(label, "local label")
        else:
            table.add_row("Disclosure Face 1", "default label")
            table.add_row("Disclosure Face 2", "default label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-label-btn":
            label = self.query_one("#new-label", Input).value.strip()
            if label:
                table = self.query_one(DataTable)
                table.add_row(label, "local label")
                self.query_one("#new-label", Input).value = ""
                self.app.notify(f'Face label "{label}" added locally.', severity="information")
