"""LUKS layer status and availability primitives (non-privileged phase)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum

from . import config
from .luks_key_store import LuksKeyStore


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
            mode=LuksMode.from_text(config.env_text("PHASMID_LUKS_MODE", "disabled")),
            container_path=config.env_text(
                "PHASMID_LUKS_CONTAINER", "/opt/phasmid/luks.img"
            ),
            mount_point=config.env_text(
                "PHASMID_LUKS_MOUNT_POINT", "/mnt/phasmid-vault"
            ),
            iter_time_ms=max(
                1, config.env_int("PHASMID_LUKS_ITER_TIME_MS", 2000, minimum=1)
            ),
        )


class LuksLayer:
    WRAPPER_PATH = "/usr/local/bin/phasmid-luks-mount"

    def __init__(self, cfg: LuksConfig | None = None):
        self.cfg = cfg or LuksConfig.from_env()
        self.key_store = LuksKeyStore()

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

    def mount(self, passphrase: str) -> LuksMountResult:
        if self.cfg.mode == LuksMode.DISABLED:
            return LuksMountResult(
                success=False,
                mounted=False,
                mode=self.cfg.mode,
                mount_point=self.cfg.mount_point,
                error_message="luks mode disabled",
            )
        if not self.is_available():
            return LuksMountResult(
                success=False,
                mounted=False,
                mode=self.cfg.mode,
                mount_point=self.cfg.mount_point,
                error_message="cryptsetup not available",
            )
        try:
            if passphrase:
                os.makedirs(self.key_store.base_dir, mode=0o700, exist_ok=True)
                with open(self.key_store.key_path, "wb") as handle:
                    handle.write(passphrase.encode("utf-8"))
            else:
                self.key_store.generate_and_store()

            cmd = [
                "sudo",
                self.WRAPPER_PATH,
                "mount",
                self.cfg.container_path,
                self.cfg.mount_point,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                return LuksMountResult(
                    success=False,
                    mounted=False,
                    mode=self.cfg.mode,
                    mount_point=self.cfg.mount_point,
                    error_message="mount wrapper failed",
                )
            os.environ["PHASMID_STATE_DIR"] = self.cfg.mount_point
            return LuksMountResult(
                success=True,
                mounted=True,
                mode=self.cfg.mode,
                mount_point=self.cfg.mount_point,
            )
        except OSError:
            return LuksMountResult(
                success=False,
                mounted=False,
                mode=self.cfg.mode,
                mount_point=self.cfg.mount_point,
                error_message="mount operation failed",
            )

    def unmount(self) -> bool:
        if self.cfg.mode == LuksMode.DISABLED:
            return True
        proc = subprocess.run(
            [
                "sudo",
                self.WRAPPER_PATH,
                "unmount",
                self.cfg.container_path,
                self.cfg.mount_point,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False
        if config.env_text("PHASMID_STATE_DIR", "") == self.cfg.mount_point:
            os.environ.pop("PHASMID_STATE_DIR", None)
        return True

    def restricted_clear(self) -> bool:
        key_cleared = self.key_store.destroy()
        proc = subprocess.run(
            [
                "sudo",
                self.WRAPPER_PATH,
                "brick",
                self.cfg.container_path,
                self.cfg.mount_point,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return key_cleared and proc.returncode == 0
