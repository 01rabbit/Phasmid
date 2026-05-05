from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ..banner import get_banner


class BannerWidget(Widget):
    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        padding: 1 2;
        color: $primary;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        width = self.app.console.width if hasattr(self.app, "console") else 120
        banner_text = get_banner(width)
        yield Static(banner_text, id="banner-text")
