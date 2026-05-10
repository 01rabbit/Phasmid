FULL_BANNER = r"""██████╗ ██╗  ██╗ █████╗ ███████╗███╗   ███╗██╗██████╗
██╔══██╗██║  ██║██╔══██╗██╔════╝████╗ ████║██║██╔══██╗
██████╔╝███████║███████║███████╗██╔████╔██║██║██║  ██║
██╔═══╝ ██╔══██║██╔══██║╚════██║██║╚██╔╝██║██║██║  ██║
██║     ██║  ██║██║  ██║███████║██║ ╚═╝ ██║██║██████╔╝
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝╚═════╝

Janus Eidolon System
LOCAL DISCLOSURE CONTROL"""

COMPACT_BANNER = """PHASMID
Janus Eidolon System
LOCAL DISCLOSURE CONTROL"""

BANNER_FULL_MIN_WIDTH = 90


def get_banner(width: int, compact: bool = False) -> str:
    if compact or width < BANNER_FULL_MIN_WIDTH:
        return COMPACT_BANNER
    return FULL_BANNER
