"""
Best-effort process hardening for Linux/Raspberry Pi Zero 2 W deployments.

All operations are attempted with silent fallback on failure so that
development on macOS and other non-Linux platforms is unaffected.

This module does NOT protect against:
- A compromised OS or compromised kernel
- Live memory capture by a privileged attacker
- Keyloggers or screen capture tools
- Physical access to the device while running

These limits apply regardless of whether every hardening step succeeds.
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass


@dataclass
class HardeningStatus:
    """Result of a single attempt to apply all process hardening steps."""

    umask_applied: bool
    core_dumps_disabled: bool
    dumpable_cleared: bool
    memory_locked: bool

    def all_applied(self) -> bool:
        return all(asdict(self).values())

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)


_cached_status: HardeningStatus | None = None


def apply_process_hardening() -> HardeningStatus:
    """
    Apply all available process hardening steps and cache the result.

    Safe to call multiple times; subsequent calls return the cached status
    from the first application.
    """
    global _cached_status
    if _cached_status is not None:
        return _cached_status

    _cached_status = HardeningStatus(
        umask_applied=_apply_umask(),
        core_dumps_disabled=_disable_core_dumps(),
        dumpable_cleared=_clear_dumpable(),
        memory_locked=_lock_memory(),
    )
    return _cached_status


def hardening_status() -> HardeningStatus | None:
    """Return the cached status from the last call to apply_process_hardening()."""
    return _cached_status


def _apply_umask() -> bool:
    """Set umask to 0o077 so new files are owner-only by default."""
    try:
        os.umask(0o077)
        return True
    except Exception:
        return False


def _disable_core_dumps() -> bool:
    """Disable core dump generation via RLIMIT_CORE."""
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        return True
    except Exception:
        return False


def _clear_dumpable() -> bool:
    """
    Mark the process as non-dumpable via prctl(PR_SET_DUMPABLE, 0).

    Linux only.  Prevents /proc/<pid>/mem reads and ptrace attachment
    by unprivileged processes.  Does not protect against root or kernel attacks.
    """
    if sys.platform != "linux":
        return False
    try:
        import ctypes
        import ctypes.util

        PR_SET_DUMPABLE = 4
        libc_name = ctypes.util.find_library("c")
        if not libc_name:
            return False
        libc = ctypes.CDLL(libc_name, use_errno=True)
        result = libc.prctl(PR_SET_DUMPABLE, ctypes.c_ulong(0), 0, 0, 0)
        return int(result) == 0
    except Exception:
        return False


def _lock_memory() -> bool:
    """
    Request that all current and future pages stay in RAM via mlockall.

    Linux only.  Reduces accidental swap exposure of key material.
    Requires CAP_IPC_LOCK or a permissive RLIMIT_MEMLOCK; silently skips
    if the capability is absent.  Does NOT protect against live memory capture
    by a privileged attacker.
    """
    if sys.platform != "linux":
        return False
    try:
        import ctypes
        import ctypes.util

        MCL_CURRENT = 1
        MCL_FUTURE = 2
        libc_name = ctypes.util.find_library("c")
        if not libc_name:
            return False
        libc = ctypes.CDLL(libc_name, use_errno=True)
        result = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
        return int(result) == 0
    except Exception:
        return False
