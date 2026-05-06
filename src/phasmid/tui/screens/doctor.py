from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, RichLog, Static

from ...models.doctor import DoctorLevel
from ...services.doctor_service import DoctorService

_LEVEL_COLORS = {
    DoctorLevel.OK: "green",
    DoctorLevel.WARN: "yellow",
    DoctorLevel.FAIL: "red",
    DoctorLevel.INFO: "dim",
}

_LEVEL_ICONS = {
    DoctorLevel.OK: "✓",
    DoctorLevel.WARN: "!",
    DoctorLevel.FAIL: "✗",
    DoctorLevel.INFO: "·",
}


class DoctorScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("q", "dismiss", "Back"),
        Binding("r", "rerun", "Re-run"),
    ]

    DEFAULT_CSS = """
    DoctorScreen {
        background: $background;
        padding: 1 2;
    }
    DoctorScreen #doctor-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 0 0 1 0;
    }
    DoctorScreen #doctor-log {
        height: 1fr;
        border: solid $primary 50%;
        background: $surface;
        padding: 1 2;
    }
    DoctorScreen #disclaimer {
        color: $warning;
        padding: 1 0;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("OPERATOR DIAGNOSTICS", id="doctor-title")
        yield RichLog(id="doctor-log", highlight=False, markup=True)
        yield Static("", id="disclaimer")
        yield Footer()

    def on_mount(self) -> None:
        self._run_checks()

    def action_rerun(self) -> None:
        self.query_one(RichLog).clear()
        self._run_checks()

    def _run_checks(self) -> None:
        svc = DoctorService()
        result = svc.run()
        log = self.query_one(RichLog)
        for check in result.checks:
            color = _LEVEL_COLORS[check.level]
            icon = _LEVEL_ICONS[check.level]
            log.write(
                f"[{color}]{icon}[/{color}]  "
                f"[bold]{check.name}[/bold]  "
                f"[dim]{check.message}[/dim]"
            )
            if check.detail:
                log.write(f"   [dim]{check.detail}[/dim]")
        self.query_one("#disclaimer", Static).update(result.disclaimer)

