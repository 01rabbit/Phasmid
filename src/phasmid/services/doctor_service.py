from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

from ..models.doctor import DoctorCheck, DoctorLevel, DoctorResult
from .profile_service import config_dir


def _check_dir_permissions(path: Path, label: str) -> DoctorCheck:
    if not path.exists():
        return DoctorCheck(
            name=label,
            level=DoctorLevel.INFO,
            message=f"{label} does not exist yet",
        )
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            return DoctorCheck(
                name=label,
                level=DoctorLevel.WARN,
                message=f"{label} is accessible to other users (mode {oct(mode)})",
                detail="Restrict with: chmod 700 " + str(path),
            )
        return DoctorCheck(
            name=label,
            level=DoctorLevel.OK,
            message=f"{label} permissions are restricted",
        )
    except OSError as exc:
        return DoctorCheck(
            name=label,
            level=DoctorLevel.WARN,
            message=f"Could not check {label} permissions: {exc}",
        )


def _check_file_permissions(path: Path, label: str) -> DoctorCheck:
    if not path.exists():
        return DoctorCheck(
            name=label,
            level=DoctorLevel.INFO,
            message=f"{label} does not exist yet",
        )
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            return DoctorCheck(
                name=label,
                level=DoctorLevel.WARN,
                message=f"{label} is readable by others (mode {oct(mode)})",
                detail="Restrict with: chmod 600 " + str(path),
            )
        return DoctorCheck(
            name=label,
            level=DoctorLevel.OK,
            message=f"{label} permissions are restricted",
        )
    except OSError as exc:
        return DoctorCheck(
            name=label,
            level=DoctorLevel.WARN,
            message=f"Could not check {label} permissions: {exc}",
        )


def _check_secure_random() -> DoctorCheck:
    try:
        import secrets
        _ = secrets.token_bytes(32)
        return DoctorCheck(
            name="Secure Randomness",
            level=DoctorLevel.OK,
            message="Secure randomness is available",
        )
    except Exception as exc:
        return DoctorCheck(
            name="Secure Randomness",
            level=DoctorLevel.FAIL,
            message=f"Secure randomness unavailable: {exc}",
        )


def _check_shell_history() -> DoctorCheck:
    shell = os.environ.get("SHELL", "")
    hist_vars = []
    if "bash" in shell:
        hist_vars.append("HISTFILE")
    if "zsh" in shell:
        hist_vars.append("HISTFILE")
    if "fish" in shell:
        hist_vars.append("fish_history")

    hist_file = os.environ.get("HISTFILE", "")
    if hist_file:
        return DoctorCheck(
            name="Shell History",
            level=DoctorLevel.WARN,
            message=f"Shell history is active ({hist_file}). "
                    "CLI passphrase arguments may be recorded.",
            detail="Use the TUI to avoid passing passphrases as arguments.",
        )
    return DoctorCheck(
        name="Shell History",
        level=DoctorLevel.INFO,
        message="Shell history variable not detected. "
                "CLI passphrase arguments may still be recorded by some shells.",
    )


def _check_temp_dir() -> DoctorCheck:
    tmpdir = tempfile.gettempdir()
    p = Path(tmpdir)
    try:
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode & 0o002:
            return DoctorCheck(
                name="Temporary Directory",
                level=DoctorLevel.WARN,
                message=f"Temporary directory {tmpdir} is world-writable",
                detail="Extracted files placed here may be accessible to other users.",
            )
        return DoctorCheck(
            name="Temporary Directory",
            level=DoctorLevel.OK,
            message=f"Temporary directory {tmpdir} permissions appear restricted",
        )
    except OSError:
        return DoctorCheck(
            name="Temporary Directory",
            level=DoctorLevel.INFO,
            message="Could not check temporary directory permissions",
        )


def _check_swap() -> DoctorCheck:
    if sys.platform == "linux":
        try:
            with open("/proc/swaps", "r") as f:
                lines = f.read().strip().splitlines()
            active = [l for l in lines[1:] if l.strip()]
            if active:
                return DoctorCheck(
                    name="Swap",
                    level=DoctorLevel.WARN,
                    message="Swap is active. Sensitive data may be paged to disk.",
                    detail="Consider disabling swap or using encrypted swap.",
                )
            return DoctorCheck(
                name="Swap",
                level=DoctorLevel.OK,
                message="No active swap detected",
            )
        except OSError:
            pass
    return DoctorCheck(
        name="Swap",
        level=DoctorLevel.INFO,
        message="Swap status check not available on this platform (best effort)",
    )


def _check_scrollback() -> DoctorCheck:
    return DoctorCheck(
        name="Terminal Scrollback",
        level=DoctorLevel.INFO,
        message="Terminal scrollback may retain sensitive output. "
                "Clear scrollback after sensitive operations.",
    )


def _check_debug_logging() -> DoctorCheck:
    debug = os.environ.get("PHASMID_DEBUG", "").lower()
    if debug in ("1", "true", "yes"):
        return DoctorCheck(
            name="Debug Logging",
            level=DoctorLevel.WARN,
            message="PHASMID_DEBUG is enabled. Verbose output may leak sensitive data.",
        )
    return DoctorCheck(
        name="Debug Logging",
        level=DoctorLevel.OK,
        message="Debug logging is not enabled",
    )


def run_doctor_checks(output_dir: str | None = None) -> DoctorResult:
    cfg = config_dir()
    checks = [
        _check_dir_permissions(cfg, "Configuration directory"),
        _check_dir_permissions(cfg / "profiles", "Profile directory"),
        _check_temp_dir(),
    ]

    if output_dir:
        checks.append(_check_dir_permissions(Path(output_dir).expanduser(), "Output directory"))

    checks += [
        _check_secure_random(),
        _check_shell_history(),
        _check_swap(),
        _check_scrollback(),
        _check_debug_logging(),
    ]

    return DoctorResult(checks=checks)


class DoctorService:
    def run(self, output_dir: str | None = None) -> DoctorResult:
        return run_doctor_checks(output_dir)
