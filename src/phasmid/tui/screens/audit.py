from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, RichLog, Static

from ...services.audit_service import AuditService
from .base import OperatorScreen


class AuditScreen(OperatorScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("q", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    AuditScreen {
        background: $background;
        padding: 1 2;
    }
    AuditScreen #audit-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 0 0 1 0;
    }
    AuditScreen #audit-log {
        height: 1fr;
        border: solid $primary 50%;
        background: $surface;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield self.webui_warning_banner()
        yield Static("SECURITY AUDIT MANIFEST", id="audit-title")
        yield RichLog(id="audit-log", highlight=False, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        svc = AuditService()
        report = svc.get_report()
        log = self.query_one(RichLog)
        for section in report.sections:
            log.write(f"\n[bold $primary]{section.title}[/]")
            for entry in section.entries:
                log.write(f"  [dim]{entry.key:<28}[/dim]{entry.value}")
