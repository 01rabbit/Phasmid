from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, RichLog, Static

from ...services.inspection_service import InspectionService


class InspectVesselScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("q", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    InspectVesselScreen {
        background: $background;
        padding: 1 2;
    }
    InspectVesselScreen #inspect-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 0 0 1 0;
    }
    InspectVesselScreen #path-input {
        margin-bottom: 1;
    }
    InspectVesselScreen #inspect-btn {
        width: 20;
        margin-bottom: 1;
    }
    InspectVesselScreen #result-log {
        height: 1fr;
        border: solid $primary 50%;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, vessel_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._initial_path = vessel_path

    def compose(self) -> ComposeResult:
        yield Static("VESSEL ANALYSIS", id="inspect-title")
        yield Static("[dim]Vessel path:[/dim]", markup=True)
        yield Input(
            value=self._initial_path or "",
            placeholder="Path to Vessel file",
            id="path-input",
        )
        yield Button("Inspect", id="inspect-btn", variant="primary")
        yield RichLog(id="result-log", highlight=False, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        if self._initial_path:
            self._run_inspection(self._initial_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "inspect-btn":
            path = self.query_one("#path-input", Input).value.strip()
            if path:
                self._run_inspection(path)
            else:
                self._show_error("Please enter a Vessel path.")

    def _run_inspection(self, path: str) -> None:
        svc = InspectionService()
        result = svc.inspect(path)
        log = self.query_one(RichLog)
        log.clear()

        if not result.ok:
            log.write("[red]Could not inspect Vessel.[/red]")
            log.write(f"[red]Reason: {result.error}[/red]")
            log.write("[dim]Next step: verify the path and try again.[/dim]")
            return

        log.write("[bold]Inspection Summary[/bold]\n")
        for field in result.fields:
            note = f"  [dim]{field.note}[/dim]" if field.note else ""
            log.write(f"[dim]{field.label:<20}[/dim]{field.value}{note}")

        if result.notes:
            log.write("\n[bold]Notes[/bold]")
            for note in result.notes:
                log.write(f"[yellow]!  {note}[/yellow]")

    def _show_error(self, msg: str) -> None:
        log = self.query_one(RichLog)
        log.clear()
        log.write(f"[red]{msg}[/red]")
