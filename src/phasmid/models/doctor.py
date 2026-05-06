from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DoctorLevel(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    INFO = "INFO"


@dataclass
class DoctorCheck:
    name: str
    level: DoctorLevel
    message: str
    detail: str = ""


@dataclass
class DoctorResult:
    checks: list[DoctorCheck] = field(default_factory=list)
    disclaimer: str = (
        "This check reduces obvious mistakes. "
        "It does not certify the host as secure."
    )

    @property
    def overall_level(self) -> DoctorLevel:
        levels = {c.level for c in self.checks}
        if DoctorLevel.FAIL in levels:
            return DoctorLevel.FAIL
        if DoctorLevel.WARN in levels:
            return DoctorLevel.WARN
        return DoctorLevel.OK
