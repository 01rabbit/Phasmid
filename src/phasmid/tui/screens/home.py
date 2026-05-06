from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Static

from ...services.vessel_service import VesselService
from ...services.profile_service import load_profile
from ...models.vessel import VesselMeta
from ..banner import COMPACT_BANNER, get_banner
from ..widgets.status_panel import VesselSummaryPanel
from ..widgets.vessel_table import VesselTable
from ..widgets.event_log import EventLog


class HomeScreen(Screen):
    BINDINGS = [
        Binding("o", "open_vessel", "Open"),
        Binding("c", "create_vessel", "Create"),
        Binding("i", "inspect_vessel", "Inspect"),
        Binding("f", "face_manager", "Faces"),
        Binding("g", "guided", "Guided"),
        Binding("a", "audit", "Audit"),
        Binding("d", "doctor", "Doctor"),
        Binding("s", "settings", "Settings"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_vessels", "Refresh", show=False),
        Binding("slash", "about", "About", show=False),
    ]

    DEFAULT_CSS = """
    HomeScreen {
        background: $background;
    }
    HomeScreen #compact-banner {
        color: $primary;
        text-align: center;
        padding: 1 2;
        height: auto;
        dock: top;
        background: $background;
    }
    HomeScreen #main-layout {
        height: 1fr;
        layout: horizontal;
    }
    HomeScreen #vessel-panel {
        width: 34;
    }
    HomeScreen #summary-panel {
        width: 1fr;
    }
    HomeScreen #event-log {
        height: 7;
        dock: bottom;
    }
    """

    def __init__(self, initial_vessel_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._vessel_svc = VesselService()
        self._profile = load_profile()
        self._initial_vessel_path = initial_vessel_path
        self._vessels: list[VesselMeta] = []

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal
        yield Static(COMPACT_BANNER, id="compact-banner", markup=False)
        with Horizontal(id="main-layout"):
            yield VesselTable(id="vessel-panel")
            yield VesselSummaryPanel(id="summary-panel")
        yield EventLog(id="event-log")
        yield Footer()

    def on_mount(self) -> None:
        self._update_banner()
        self._refresh_vessels()
        self._log("Phasmid operator console ready.")

    def on_resize(self) -> None:
        self._update_banner()

    def _update_banner(self) -> None:
        force_compact = self._profile.compact_banner if self._profile else False
        banner = get_banner(self.app.size.width, compact=force_compact)
        self.query_one("#compact-banner", Static).update(banner)

    def _refresh_vessels(self) -> None:
        self._vessels = self._vessel_svc.list(self._profile.default_vessel_dir or None)
        table = self.query_one(VesselTable)
        table.update_vessels(self._vessels)
        self._update_summary()

    def _update_summary(self) -> None:
        table = self.query_one(VesselTable)
        vessel = table.selected_vessel
        panel = self.query_one(VesselSummaryPanel)
        panel.update_vessel(vessel)

    def _log(self, msg: str, level: str = "info") -> None:
        try:
            self.query_one(EventLog).log_event(msg, level)
        except Exception:
            pass

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._update_summary()

    def action_refresh_vessels(self) -> None:
        self._refresh_vessels()
        self._log("Vessel list refreshed.")

    def action_open_vessel(self) -> None:
        from .open_vessel import OpenVesselScreen
        table = self.query_one(VesselTable)
        vessel = table.selected_vessel
        path = str(vessel.path) if vessel else ""
        self.app.push_screen(OpenVesselScreen(vessel_path=path))

    def action_create_vessel(self) -> None:
        from .create_vessel import CreateVesselScreen
        self.app.push_screen(CreateVesselScreen())

    def action_inspect_vessel(self) -> None:
        from .inspect_vessel import InspectVesselScreen
        table = self.query_one(VesselTable)
        vessel = table.selected_vessel
        path = str(vessel.path) if vessel else ""
        self.app.push_screen(InspectVesselScreen(vessel_path=path))

    def action_face_manager(self) -> None:
        from .face_manager import FaceManagerScreen
        table = self.query_one(VesselTable)
        vessel = table.selected_vessel
        self.app.push_screen(FaceManagerScreen(vessel=vessel))

    def action_guided(self) -> None:
        from .guided import GuidedScreen
        self.app.push_screen(GuidedScreen())

    def action_audit(self) -> None:
        from .audit import AuditScreen
        self.app.push_screen(AuditScreen())

    def action_doctor(self) -> None:
        from .doctor import DoctorScreen
        self.app.push_screen(DoctorScreen())

    def action_settings(self) -> None:
        from .settings import SettingsScreen

        def _after_settings(_):
            self._profile = load_profile()
            self._refresh_vessels()

        self.app.push_screen(SettingsScreen(), _after_settings)

    def action_about(self) -> None:
        from .about import AboutScreen
        self.app.push_screen(AboutScreen())

    def action_help(self) -> None:
        from .about import AboutScreen
        self.app.push_screen(AboutScreen())

    def action_quit(self) -> None:
        self.app.exit()
