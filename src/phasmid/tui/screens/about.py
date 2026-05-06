from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from ..banner import FULL_BANNER


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
        min-width: 64;
        max-width: 94;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: solid $primary;
    }
    AboutScreen #banner-static {
        color: $primary;
        text-align: left;
        padding: 1 0;
    }
    AboutScreen #about-body {
        color: $text;
        padding: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        from textual.containers import Container

        with Container(id="about-container"):
            yield Static(FULL_BANNER, id="banner-static", markup=False)
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
            yield Footer()
