from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static
from textual.binding import Binding

from ..banner import get_banner, COMPACT_BANNER


class AboutScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("q", "dismiss", "Back"),
    ]

    DEFAULT_CSS = """
    AboutScreen {
        align: center middle;
        background: $background;
    }
    AboutScreen #about-container {
        width: auto;
        height: auto;
        max-width: 94;
        padding: 2 4;
        background: $surface;
        border: solid $primary;
    }
    AboutScreen #banner-static {
        color: $primary;
        text-align: center;
        padding: 1 0;
    }
    AboutScreen #about-body {
        color: $text;
        padding: 1 0;
    }
    AboutScreen #back-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        from textual.containers import Container
        with Container(id="about-container"):
            yield Static(COMPACT_BANNER, id="banner-static", markup=False)
            yield Static(
                "\n[bold]Phasmid[/bold] is a research-grade prototype for studying and "
                "operating deniable storage under coerced disclosure scenarios.\n\n"
                "A [bold]Vessel[/bold] is a headerless deniable container file. "
                "It carries one or more disclosure faces without exposing metadata, "
                "magic bytes, or an obvious vault structure.\n\n"
                "[dim]Not forensic-proof. Not coercion-proof. Not production-grade.[/dim]",
                id="about-body",
                markup=True,
            )
            yield Button("Back (Esc)", id="back-btn", variant="default")

    def on_mount(self) -> None:
        banner = get_banner(self.app.size.width)
        self.query_one("#banner-static", Static).update(banner)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.dismiss()
