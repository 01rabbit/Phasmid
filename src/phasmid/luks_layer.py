"""LUKS layer status and availability primitives (non-privileged phase)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

class LuksMode(str, Enum):
    FILE_CONTAINER = "file"
    PARTITION = "partition"
    DISABLED = "disabled"

    @classmethod
    def from_text(cls, value: str) -> "LuksMode":
        normalized = (value or "").strip().lower()
        if normalized == cls.FILE_CONTAINER.value:
            return cls.FILE_CONTAINER
        if normalized == cls.PARTITION.value:
            return cls.PARTITION
        return cls.DISABLED


@dataclass(slots=True)
class LuksMountResult:
    success: bool
    mounted: bool
    mode: LuksMode
    mount_point: str
    error_message: str = ""


@dataclass(slots=True)
class LuksConfig:
    mode: LuksMode
    container_path: str = "/opt/phasmid/luks.img"
    mount_point: str = "/mnt/phasmid-vault"
    iter_time_ms: int = 2000

    @classmethod
    def from_env(cls) -> "LuksConfig":
        return cls(
            mode=LuksMode.from_text(os.getenv("PHASMID_LUKS_MODE", "disabled")),
            container_path=os.getenv("PHASMID_LUKS_CONTAINER", "/opt/phasmid/luks.img"),
            mount_point=os.getenv("PHASMID_LUKS_MOUNT_POINT", "/mnt/phasmid-vault"),
            iter_time_ms=max(1, int(os.getenv("PHASMID_LUKS_ITER_TIME_MS", "2000"))),
        )


class LuksLayer:
    def __init__(self, cfg: LuksConfig | None = None):
        self.cfg = cfg or LuksConfig.from_env()

    def is_available(self) -> bool:
        if self.cfg.mode == LuksMode.DISABLED:
            return False
        return shutil.which("cryptsetup") is not None

    def status(self) -> LuksMountResult:
        if self.cfg.mode == LuksMode.DISABLED:
            return LuksMountResult(
                success=True,
                mounted=False,
                mode=self.cfg.mode,
                mount_point=self.cfg.mount_point,
            )
        if not self.is_available():
            return LuksMountResult(
                success=False,
                mounted=False,
                mode=self.cfg.mode,
                mount_point=self.cfg.mount_point,
                error_message="cryptsetup not available",
            )

        mount_point = self.cfg.mount_point
        probe = subprocess.run(
            ["mountpoint", "-q", mount_point],
            capture_output=True,
            text=True,
            check=False,
        )
        return LuksMountResult(
            success=True,
            mounted=(probe.returncode == 0),
            mode=self.cfg.mode,
            mount_point=mount_point,
        )
