from __future__ import annotations

from ..luks_layer import LuksLayer, LuksMode


class LuksService:
    """Service wrapper for operator-facing LUKS actions."""

    def __init__(self):
        self.layer = LuksLayer()

    @property
    def enabled(self) -> bool:
        return self.layer.cfg.mode != LuksMode.DISABLED

    def status(self):
        return self.layer.status()

    def mount(self, passphrase: str):
        return self.layer.mount(passphrase)

    def unmount(self) -> bool:
        return self.layer.unmount()

    def restricted_clear(self) -> bool:
        return self.layer.restricted_clear()
