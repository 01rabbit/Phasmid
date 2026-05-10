"""SH-11: Forbidden internal terms for Field Mode visibility tests.

This module defines terms that must NOT appear in capture-visible WebUI HTML
or normal CLI output in Field Mode before restricted confirmation is active.

Linked from: docs/TESTING_GUIDELINES.md, tests/scenarios/test_field_mode_visibility.py

Each entry is a (term, reason) pair.  The reason explains why the term is
forbidden from capture-visible surfaces.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Terms forbidden in Field Mode HTML before restricted confirmation
# ---------------------------------------------------------------------------

# Format: (forbidden_term, reason_for_prohibition)
FORBIDDEN_IN_FIELD_MODE_HTML: list[tuple[str, str]] = [
    # Internal slot/mode structure
    ("purge_applied", "Internal flag — reveals restricted recovery execution"),
    ("password_role", "Internal KDF parameter — reveals dual-slot structure"),
    ("PURGE_ROLE", "Internal constant — reveals slot role naming"),
    ("OPEN_ROLE", "Internal constant — reveals slot role naming"),
    # State directory path (hidden until restricted confirmation)
    # Note: the actual state_dir() value is dynamic; the template suppresses it
    # by passing state_path="" in Field Mode. The term ".state" or "access.bin"
    # should not appear in rendered HTML before confirmation.
    ("access.bin", "State directory filename — reveals Phasmid installation"),
    ("store.bin", "State directory filename — reveals ORB state presence"),
    ("lock.bin", "State directory filename — reveals face-lock state presence"),
    # Restricted recovery internal terminology
    ("restricted_recovery", "Internal term — reveals dual-slot recovery model"),
    ("LOCAL_CLEAR", "Action phrase fragment — reveals restricted action model"),
    # Format version / internal format markers
    ("jes-v3", "Internal format marker — reveals vault format details"),
    (
        "phasmid-record-v3",
        "Internal AAD prefix — reveals cryptographic record structure",
    ),
]

# ---------------------------------------------------------------------------
# Terms forbidden in ALL WebUI output (Field Mode and normal mode)
# These reveal internal structure that should never appear in user-facing HTML.
# ---------------------------------------------------------------------------

FORBIDDEN_IN_ALL_MODES_HTML: list[tuple[str, str]] = [
    ("purge_applied", "Internal flag — never visible to WebUI client"),
    ("password_role", "Internal KDF parameter — never user-facing"),
    ("phasmid-record-v3", "Internal AAD prefix — never user-facing"),
    ("jes-v3", "Internal format marker — never user-facing"),
]

# ---------------------------------------------------------------------------
# Terms forbidden in normal (non-debug) CLI output
# ---------------------------------------------------------------------------

FORBIDDEN_IN_CLI_OUTPUT: list[tuple[str, str]] = [
    ("purge_applied", "Internal flag — not user-facing"),
    ("PURGE_ROLE", "Internal constant — not user-facing"),
    ("OPEN_ROLE", "Internal constant — not user-facing"),
    ("password_role", "Internal KDF parameter — not user-facing"),
    ("jes-v3", "Internal format marker — not user-facing"),
]
