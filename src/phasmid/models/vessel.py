from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class VesselPosture(str, Enum):
    OPERATIONAL = "operational"
    UNREGISTERED = "unregistered"
    UNKNOWN = "unknown"


@dataclass
class VesselMeta:
    path: Path
    name: str = ""
    size_bytes: int = 0
    header_status: str = "absent"
    magic_bytes_status: str = "absent"
    face_count: int = 0
    posture: VesselPosture = VesselPosture.UNKNOWN
    label: str = ""
    face_labels: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            self.name = Path(self.path).name

    @property
    def size_human(self) -> str:
        b: float = float(self.size_bytes)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if b < 1024:
                return f"{b:.0f} {unit}" if unit == "B" else f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PiB"
