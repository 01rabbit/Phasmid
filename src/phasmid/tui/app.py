from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from .screens.home import HomeScreen
from .theme import PHASMID_DARK, PHASMID_LIGHT


class PhasmidApp(App):
    """Phasmid TUI Operator Console."""

    TITLE = "Phasmid"
    SUB_TITLE = "Janus Eidolon System"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    CSS = """
    Screen {
        background: #0d0d0d;
    }
    """

    def __init__(
        self,
        initial_screen: str = "home",
        vessel_path: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._initial_screen = initial_screen
        self._vessel_path = vessel_path

    def on_mount(self) -> None:
        try:
            self.register_theme(PHASMID_DARK)
            self.register_theme(PHASMID_LIGHT)
            self.theme = "phasmid-dark"
        except Exception:
            pass

        screen_map = {
            "home": self._push_home,
            "guided": self._push_guided,
            "audit": self._push_audit,
            "doctor": self._push_doctor,
            "inspect": self._push_inspect,
            "create": self._push_create,
            "open": self._push_open,
            "about": self._push_about,
        }
        action = screen_map.get(self._initial_screen, self._push_home)
        action()

    def compose(self) -> ComposeResult:
        return iter([])

    def _push_home(self) -> None:
        self.push_screen(HomeScreen(initial_vessel_path=self._vessel_path))

    def _push_guided(self) -> None:
        from .screens.guided import GuidedScreen
        self.push_screen(HomeScreen())
        self.push_screen(GuidedScreen())

    def _push_audit(self) -> None:
        from .screens.audit import AuditScreen
        self.push_screen(HomeScreen())
        self.push_screen(AuditScreen())

    def _push_doctor(self) -> None:
        from .screens.doctor import DoctorScreen
        self.push_screen(HomeScreen())
        self.push_screen(DoctorScreen())

    def _push_inspect(self) -> None:
        from .screens.inspect_vessel import InspectVesselScreen
        self.push_screen(HomeScreen())
        self.push_screen(InspectVesselScreen(vessel_path=self._vessel_path))

    def _push_create(self) -> None:
        from .screens.create_vessel import CreateVesselScreen
        self.push_screen(HomeScreen())
        self.push_screen(CreateVesselScreen(initial_path=self._vessel_path or ""))

    def _push_open(self) -> None:
        from .screens.open_vessel import OpenVesselScreen
        self.push_screen(HomeScreen())
        self.push_screen(OpenVesselScreen(vessel_path=self._vessel_path or ""))

    def _push_about(self) -> None:
        from .screens.about import AboutScreen
        self.push_screen(HomeScreen())
        self.push_screen(AboutScreen())


def run_tui(
    initial_screen: str = "home",
    vessel_path: str | None = None,
) -> None:
    app = PhasmidApp(initial_screen=initial_screen, vessel_path=vessel_path)
    app.run()
