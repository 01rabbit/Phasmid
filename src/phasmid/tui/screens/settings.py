from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static, Switch

from ...services.profile_service import load_profile, save_profile


class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        background: $background;
        padding: 1 4;
    }
    SettingsScreen #settings-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        padding: 0 0 1 0;
    }
    SettingsScreen .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    SettingsScreen .switch-row {
        layout: horizontal;
        height: 3;
        align: left middle;
    }
    SettingsScreen .switch-label {
        width: 30;
        color: $text;
    }
    SettingsScreen #save-btn {
        margin-top: 2;
        width: 100%;
    }
    SettingsScreen #save-status {
        color: $success;
        min-height: 1;
        padding: 0 0 1 0;
    }
    """

    _THEME_OPTIONS = [("Dark", "dark"), ("Light", "light")]

    def __init__(self, profile_name: str = "default", **kwargs):
        super().__init__(**kwargs)
        self._profile = load_profile(profile_name)

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal
        p = self._profile
        yield Static("OPERATOR SETTINGS", id="settings-title")
        yield Label("Default Vessel directory", classes="field-label")
        yield Input(value=p.default_vessel_dir, placeholder="~/Phasmid/vessels", id="vessel-dir")
        yield Label("Default output directory", classes="field-label")
        yield Input(value=p.default_output, placeholder="~/Phasmid/output", id="output-dir")
        yield Label("Default container size", classes="field-label")
        yield Input(value=p.container_size, placeholder="512M", id="container-size")
        yield Label("Theme", classes="field-label")
        yield Select([(label, val) for label, val in self._THEME_OPTIONS], value=p.theme, id="theme")
        with Horizontal(classes="switch-row"):
            yield Label("Track recent Vessels", classes="switch-label")
            yield Switch(value=p.recent_tracking, id="recent-tracking")
        with Horizontal(classes="switch-row"):
            yield Label("Compact banner", classes="switch-label")
            yield Switch(value=p.compact_banner, id="compact-banner")
        yield Static("", id="save-status")
        yield Button("Save Settings", id="save-btn", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()

    def _save(self) -> None:
        p = self._profile
        p.default_vessel_dir = self.query_one("#vessel-dir", Input).value.strip()
        p.default_output = self.query_one("#output-dir", Input).value.strip()
        p.container_size = self.query_one("#container-size", Input).value.strip() or "512M"
        p.theme = self.query_one("#theme", Select).value or "dark"
        p.recent_tracking = self.query_one("#recent-tracking", Switch).value
        p.compact_banner = self.query_one("#compact-banner", Switch).value
        try:
            save_profile(p)
            self.query_one("#save-status", Static).update("Settings saved.")
            self.app.notify("Settings saved.", severity="information")
        except Exception as exc:
            self.query_one("#save-status", Static).update(f"Error: {exc}")
            self.app.notify(f"Could not save settings: {exc}", severity="error")
