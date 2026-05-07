from __future__ import annotations

import os
import resource
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..config import state_dir
from ..models.doctor import DoctorCheck, DoctorLevel, DoctorResult
from ..process_hardening import hardening_status
from ..volatile_state import check_volatile_state, volatile_state_path
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
        hist_path = Path(hist_file).expanduser()
        if hist_path.exists():
            try:
                content = hist_path.read_text(encoding="utf-8", errors="ignore")
                if any(term in content for term in ("phasmid", "vault.bin")):
                    return DoctorCheck(
                        name="Shell History",
                        level=DoctorLevel.WARN,
                        message="Shell history contains recent Phasmid-related commands.",
                        detail="Clear history and prefer TUI passphrase input.",
                    )
            except OSError:
                pass
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
            active = [ln for ln in lines[1:] if ln.strip()]
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


def _check_volatile_state() -> DoctorCheck:
    path = volatile_state_path()
    if path is None:
        return DoctorCheck(
            name="Volatile Key Store",
            level=DoctorLevel.INFO,
            message="PHASMID_TMPFS_STATE not configured (persistent state in use)",
        )
    ok, message = check_volatile_state(path)
    if ok:
        return DoctorCheck(
            name="Volatile Key Store",
            level=DoctorLevel.OK,
            message=f"Volatile state path accessible: {path}",
            detail=message,
        )
    return DoctorCheck(
        name="Volatile Key Store",
        level=DoctorLevel.FAIL,
        message=f"Volatile state path unavailable: {message}",
        detail="Ensure the tmpfs mount is in place before starting Phasmid.",
    )


def _check_process_hardening() -> DoctorCheck:
    status = hardening_status()
    if status is None:
        return DoctorCheck(
            name="Process Hardening",
            level=DoctorLevel.INFO,
            message="Process hardening has not been applied yet in this session",
        )
    applied = [k for k, v in status.as_dict().items() if v]
    skipped = [k for k, v in status.as_dict().items() if not v]
    if not skipped:
        return DoctorCheck(
            name="Process Hardening",
            level=DoctorLevel.OK,
            message="All process hardening steps applied",
        )
    return DoctorCheck(
        name="Process Hardening",
        level=DoctorLevel.INFO,
        message=f"Hardening partial: applied={applied}, skipped={skipped} "
        "(skipped steps are platform-dependent best-effort)",
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


def _check_recent_documents_cache() -> DoctorCheck:
    """Best-effort check for recent-document artifact leakage.

    Threat model reference: docs/THREAT_MODEL.md (Attack Surfaces / local passive observer).
    """
    xbel = Path.home() / ".local" / "share" / "recently-used.xbel"
    if not xbel.exists():
        return DoctorCheck(
            name="Recent Documents Cache",
            level=DoctorLevel.INFO,
            message="Recent documents cache not found (unknown on this host).",
        )
    try:
        content = xbel.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError as exc:
        return DoctorCheck(
            name="Recent Documents Cache",
            level=DoctorLevel.INFO,
            message=f"Could not inspect recent documents cache: {exc}",
        )
    if any(term in content for term in ("vault.bin", "phasmid")):
        return DoctorCheck(
            name="Recent Documents Cache",
            level=DoctorLevel.WARN,
            message="Recent documents cache contains Phasmid-related references.",
            detail="Clear recently-used entries before high-risk movement.",
        )
    return DoctorCheck(
        name="Recent Documents Cache",
        level=DoctorLevel.OK,
        message="No obvious Phasmid references in recent documents cache.",
    )


def _check_thumbnail_cache() -> DoctorCheck:
    """Best-effort thumbnail cache leak check using Freedesktop Thumb::URI hints."""
    thumbs_dir = Path.home() / ".cache" / "thumbnails"
    if not thumbs_dir.exists():
        return DoctorCheck(
            name="Thumbnail Cache",
            level=DoctorLevel.INFO,
            message="Thumbnail cache not found (unknown on this host).",
        )
    inspected = 0
    try:
        for candidate in thumbs_dir.rglob("*.png"):
            inspected += 1
            if inspected > 500:
                break
            blob = candidate.read_bytes()
            lowered = blob.lower()
            if any(
                term in lowered for term in (b"thumb::uri", b"phasmid", b"vault.bin")
            ):
                return DoctorCheck(
                    name="Thumbnail Cache",
                    level=DoctorLevel.WARN,
                    message="Thumbnail cache may contain Phasmid-related file traces.",
                    detail="Consider clearing thumbnail cache for local hygiene.",
                )
    except OSError as exc:
        return DoctorCheck(
            name="Thumbnail Cache",
            level=DoctorLevel.INFO,
            message=f"Could not inspect thumbnail cache: {exc}",
        )
    return DoctorCheck(
        name="Thumbnail Cache",
        level=DoctorLevel.OK,
        message="No obvious Phasmid traces detected in thumbnail cache sample.",
    )


def _check_system_journal() -> DoctorCheck:
    """Best-effort systemd journal trace check; non-Linux returns unknown."""
    if sys.platform != "linux":
        return DoctorCheck(
            name="System Journal",
            level=DoctorLevel.INFO,
            message="System journal check is Linux-only (unknown on this platform).",
        )
    try:
        proc = subprocess.run(
            ["journalctl", "--user", "-n", "200", "--no-pager"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return DoctorCheck(
            name="System Journal",
            level=DoctorLevel.INFO,
            message="System journal not accessible for inspection.",
        )
    content = (proc.stdout or "").lower()
    if any(term in content for term in ("phasmid", "vault.bin")):
        return DoctorCheck(
            name="System Journal",
            level=DoctorLevel.WARN,
            message="System journal contains recent Phasmid-related process traces.",
            detail="Review and prune logs as required by local policy.",
        )
    return DoctorCheck(
        name="System Journal",
        level=DoctorLevel.OK,
        message="No obvious Phasmid traces in recent user journal sample.",
    )


def _check_core_dumps() -> DoctorCheck:
    """Check whether process core dumps are disabled (`ulimit -c` equivalent)."""
    try:
        soft, _hard = resource.getrlimit(resource.RLIMIT_CORE)
    except (ValueError, OSError):
        return DoctorCheck(
            name="Core Dumps",
            level=DoctorLevel.INFO,
            message="Core dump limit could not be determined.",
        )
    if soft == 0:
        return DoctorCheck(
            name="Core Dumps",
            level=DoctorLevel.OK,
            message="Core dumps are disabled for this session.",
        )
    return DoctorCheck(
        name="Core Dumps",
        level=DoctorLevel.WARN,
        message=f"Core dump limit is non-zero ({soft}).",
        detail="Set `ulimit -c 0` for sensitive sessions.",
    )


def _check_compressed_swap() -> DoctorCheck:
    """Check zswap/zram posture because compressed swap can retain sensitive pages."""
    if sys.platform != "linux":
        return DoctorCheck(
            name="Compressed Swap",
            level=DoctorLevel.INFO,
            message="Compressed swap check is Linux-only (unknown on this platform).",
        )
    try:
        zswap_flag = Path("/sys/module/zswap/parameters/enabled")
        zswap_enabled = zswap_flag.exists() and zswap_flag.read_text(
            encoding="utf-8", errors="ignore"
        ).strip().upper() in {"Y", "1"}
    except OSError:
        zswap_enabled = False
    zram_devices = list(Path("/sys/block").glob("zram*"))
    if zswap_enabled or zram_devices:
        return DoctorCheck(
            name="Compressed Swap",
            level=DoctorLevel.WARN,
            message="Compressed swap (zswap/zram) appears enabled.",
            detail="Disable compressed swap for stricter local artifact hygiene.",
        )
    return DoctorCheck(
        name="Compressed Swap",
        level=DoctorLevel.OK,
        message="No active zswap/zram indicators detected.",
    )


def _check_recent_file_activity(vault_path: Path) -> DoctorCheck:
    """Warn when vault atime/mtime imply very recent usage exposure."""
    if not vault_path.exists():
        return DoctorCheck(
            name="Recent File Activity",
            level=DoctorLevel.INFO,
            message="Vault file not present; recent activity check unavailable.",
        )
    try:
        st = vault_path.stat()
    except OSError as exc:
        return DoctorCheck(
            name="Recent File Activity",
            level=DoctorLevel.INFO,
            message=f"Could not inspect vault timestamps: {exc}",
        )
    now = time.time()
    threshold = int(os.environ.get("PHASMID_DOCTOR_RECENT_SECONDS", "86400"))
    if now - max(st.st_mtime, st.st_atime) <= threshold:
        return DoctorCheck(
            name="Recent File Activity",
            level=DoctorLevel.WARN,
            message="Vault file timestamps indicate recent local use.",
            detail="Recent atime/mtime can reveal operational timing.",
        )
    return DoctorCheck(
        name="Recent File Activity",
        level=DoctorLevel.OK,
        message="Vault file timestamps are not recent.",
    )


def _check_vault_size_record(vault_path: Path) -> DoctorCheck:
    """Compare vault size against optional local baseline record.

    Baseline file: `<state_dir>/vault.size` (bytes as integer).
    """
    if not vault_path.exists():
        return DoctorCheck(
            name="Vault Size Record",
            level=DoctorLevel.INFO,
            message="Vault file not present; size baseline check unavailable.",
        )
    baseline_file = Path(state_dir()) / "vault.size"
    if not baseline_file.exists():
        return DoctorCheck(
            name="Vault Size Record",
            level=DoctorLevel.INFO,
            message="Vault size baseline is not recorded (unknown).",
        )
    try:
        expected = int(baseline_file.read_text(encoding="utf-8").strip())
        actual = vault_path.stat().st_size
    except (OSError, ValueError) as exc:
        return DoctorCheck(
            name="Vault Size Record",
            level=DoctorLevel.INFO,
            message=f"Vault size baseline could not be parsed: {exc}",
        )
    if actual != expected:
        return DoctorCheck(
            name="Vault Size Record",
            level=DoctorLevel.WARN,
            message=f"Vault size differs from baseline (expected {expected}, actual {actual}).",
            detail="Investigate unexpected container-size drift.",
        )
    return DoctorCheck(
        name="Vault Size Record",
        level=DoctorLevel.OK,
        message="Vault size matches local baseline record.",
    )


def run_doctor_checks(output_dir: str | None = None) -> DoctorResult:
    cfg = config_dir()
    vault_path = Path("vault.bin")
    checks = [
        _check_dir_permissions(cfg, "Configuration directory"),
        _check_dir_permissions(cfg / "profiles", "Profile directory"),
        _check_temp_dir(),
    ]

    if output_dir:
        checks.append(
            _check_dir_permissions(Path(output_dir).expanduser(), "Output directory")
        )

    checks += [
        _check_secure_random(),
        _check_volatile_state(),
        _check_process_hardening(),
        _check_recent_documents_cache(),
        _check_thumbnail_cache(),
        _check_system_journal(),
        _check_core_dumps(),
        _check_compressed_swap(),
        _check_shell_history(),
        _check_recent_file_activity(vault_path),
        _check_vault_size_record(vault_path),
        _check_swap(),
        _check_scrollback(),
        _check_debug_logging(),
    ]

    return DoctorResult(checks=checks)


class DoctorService:
    def run(self, output_dir: str | None = None) -> DoctorResult:
        return run_doctor_checks(output_dir)
