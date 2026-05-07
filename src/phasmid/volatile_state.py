"""
Volatile key-material state using tmpfs for appliance deployments.

When ``PHASMID_TMPFS_STATE`` is set, Phasmid uses the specified path as its
state directory.  The intended use is a tmpfs mount so that key material in
``.state/`` disappears on power loss or controlled unmount.

This does NOT protect against:
- Live memory capture by a privileged attacker
- A compromised OS or hypervisor
- Physical access while the system is running

The tmpfs approach provides power-loss key disappearance and reduces the
window during which key material exists on persistent storage.  It does not
provide tamper resistance or hardware-backed secure storage.

Configuration
-------------
Set ``PHASMID_TMPFS_STATE`` to the tmpfs mount point, e.g.::

    PHASMID_TMPFS_STATE=/run/phasmid-keys

The systemd unit should create the mount before the Phasmid service starts.
See ``docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md`` for the recommended setup.

If the variable is set but the path does not exist, the startup check will
fail rather than fall back to persistent storage silently.
"""
from __future__ import annotations

import os
import stat
import sys


def volatile_state_path() -> str | None:
    """Return the configured tmpfs state path, or None if not configured."""
    return os.environ.get("PHASMID_TMPFS_STATE") or None


def check_volatile_state(path: str) -> tuple[bool, str]:
    """
    Validate that *path* is accessible and suitable for volatile key material.

    Returns ``(True, message)`` when the path is usable.
    Returns ``(False, reason)`` when it is not.

    This check does not verify that the path is actually on a tmpfs mount,
    because that requires root-level inspection on Linux and is not portable.
    The caller is responsible for configuring the mount correctly.
    """
    if not os.path.exists(path):
        return False, f"volatile state path does not exist: {path}"
    if not os.path.isdir(path):
        return False, f"volatile state path is not a directory: {path}"
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError as exc:
        return False, f"cannot stat volatile state path: {exc}"
    if mode & 0o077:
        return (
            True,
            f"volatile state path exists but mode is {oct(mode)}; recommend 0700",
        )
    return True, "volatile state path is accessible"


def require_volatile_state() -> None:
    """
    Raise ``RuntimeError`` if ``PHASMID_TMPFS_STATE`` is set but the path
    is not accessible.

    Call this at startup before opening any state files so that a missing
    tmpfs mount produces a clear failure rather than silent fallback to
    persistent storage.
    """
    path = volatile_state_path()
    if path is None:
        return
    ok, message = check_volatile_state(path)
    if not ok:
        raise RuntimeError(
            f"PHASMID_TMPFS_STATE is configured but the path is unavailable: {message}. "
            "Ensure the tmpfs mount is in place before starting Phasmid."
        )


def volatile_state_summary() -> dict[str, object]:
    """Return a status dict for diagnostics (safe to log; contains no key material)."""
    path = volatile_state_path()
    if path is None:
        return {"configured": False}
    ok, message = check_volatile_state(path)
    return {
        "configured": True,
        "path_accessible": ok,
        "message": message,
        "linux": sys.platform == "linux",
    }
