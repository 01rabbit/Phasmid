from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InspectionField:
    label: str
    value: str
    note: str = ""


@dataclass
class InspectionResult:
    path: Path
    fields: list[InspectionField] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error
