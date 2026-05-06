FULL_BANNER = r"""       ____  __
      / __ \/ /_  ____ __________ ___  (_)____/ /
     / /_/ / __ \/ __ `/ ___/ __ `__ \/ / ___/ /
    / ____/ / / / /_/ (__  ) / / / / / / /  /_/
   /_/   /_/ /_/\__,_/____/_/ /_/ /_/_/_/  (_)

        Janus Eidolon System
        coercion-aware deniable storage

        one vessel / multiple faces / no confession"""

COMPACT_BANNER = """PHASMID
JANUS EIDOLON SYSTEM

coercion-aware deniable storage
one vessel / multiple faces / no confession"""

BANNER_FULL_MIN_WIDTH = 90


def get_banner(width: int, compact: bool = False) -> str:
    if compact or width < BANNER_FULL_MIN_WIDTH:
        return COMPACT_BANNER
    return FULL_BANNER
