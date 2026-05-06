from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuditEntry:
    key: str
    value: str


@dataclass
class AuditSection:
    title: str
    entries: list[AuditEntry] = field(default_factory=list)


@dataclass
class AuditReport:
    sections: list[AuditSection] = field(default_factory=list)
