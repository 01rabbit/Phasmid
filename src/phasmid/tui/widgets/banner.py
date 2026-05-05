import shutil

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
        width = shutil.get_terminal_size(fallback=(120, 30)).columns
        banner_text = get_banner(width)
        yield Static(banner_text, id="banner-text", markup=False)
