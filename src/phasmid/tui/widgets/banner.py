from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from ..banner import get_banner, COMPACT_BANNER


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
        yield Static(COMPACT_BANNER, id="banner-text", markup=False)

    def on_mount(self) -> None:
        banner_text = get_banner(self.app.size.width)
        self.query_one("#banner-text", Static).update(banner_text)
