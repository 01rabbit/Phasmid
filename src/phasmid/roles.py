"""
Local role store for the optional dual-approval flow (Issue #28).

Defines two roles:
- OPERATOR  — implicit; the normal user of the system (no separate passphrase).
- SUPERVISOR — a second local principal whose passphrase must be entered to
               authorize high-risk actions.

This is local knowledge separation only.  It does not:
- prevent a single person from knowing all credentials
- prevent collusion
- act as a cryptographic factor for vault derivation
- replace hardware-backed approval tokens

The supervisor passphrase hash is stored in an AES-GCM encrypted file under the
configured state directory using :class:`~phasmid.local_state_crypto.LocalStateCipher`.
The hash uses PBKDF2-HMAC-SHA-256 with a random 32-byte salt (100 000 iterations).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from enum import Enum

from . import strings as text
from .config import ROLE_STATE_NAME, STATE_KEY_NAME, state_dir
from .crypto_params import PBKDF2_DKLEN, PBKDF2_ITERATIONS, PBKDF2_SALT_SIZE
from .local_state_crypto import LocalStateCipher

_SCHEMA_VERSION = 1


class Role(str, Enum):
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"


@dataclass(frozen=True)
class RoleVerificationResult:
    """Neutral result of a passphrase verification attempt."""

    verified: bool
    role: Role | None
    reason: str  # "verified" | "not_configured" | "wrong_passphrase" | "store_error"


class RoleStore:
    """
    Encrypted local store for the supervisor passphrase hash.

    A single state file (``roles.bin``) holds a JSON blob with the PBKDF2 salt
    and hash.  The blob is AES-GCM encrypted via :class:`LocalStateCipher`.
    The operator role has no stored passphrase; it is implicit.
    """

    def __init__(self, state_path: str | None = None) -> None:
        self._state_dir = state_path or state_dir()
        os.makedirs(self._state_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self._state_dir, 0o700)
        except OSError:
            pass
        self._role_path = os.path.join(self._state_dir, ROLE_STATE_NAME)
        self._state_key_path = os.path.join(self._state_dir, STATE_KEY_NAME)
        self._cipher = LocalStateCipher(
            state_key_path=self._state_key_path,
            aad=b"phasmid-role-store:v1",
            local_key_suffix=b":roles",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def configure_supervisor(self, passphrase: str) -> tuple[bool, str]:
        """Hash *passphrase* and store it.  Overwrites any previous value."""
        if not passphrase:
            return False, text.DUAL_APPROVAL_SUPERVISOR_NOT_CONFIGURED
        salt = os.urandom(PBKDF2_SALT_SIZE)
        digest = self._hash(passphrase, salt)
        payload = {
            "schema": _SCHEMA_VERSION,
            "supervisor": {
                "salt": salt.hex(),
                "hash": digest.hex(),
            },
        }
        try:
            encrypted = self._cipher.encrypt(json.dumps(payload).encode("utf-8"))
            tmp = self._role_path + ".tmp"
            with open(tmp, "wb") as handle:
                handle.write(encrypted)
            os.replace(tmp, self._role_path)
            try:
                os.chmod(self._role_path, 0o600)
            except OSError:
                pass
        except OSError:
            return False, text.STORE_OPERATION_FAILED
        return True, text.DUAL_APPROVAL_SUPERVISOR_SET

    def verify_supervisor(self, passphrase: str) -> RoleVerificationResult:
        """Return a :class:`RoleVerificationResult` for *passphrase*."""
        if not self.is_configured():
            return RoleVerificationResult(
                verified=False,
                role=None,
                reason="not_configured",
            )
        try:
            stored = self._read_supervisor()
        except (OSError, ValueError, KeyError):
            return RoleVerificationResult(
                verified=False,
                role=None,
                reason="store_error",
            )
        salt = bytes.fromhex(stored["salt"])
        expected = bytes.fromhex(stored["hash"])
        actual = self._hash(passphrase, salt)
        if not hmac.compare_digest(actual, expected):
            return RoleVerificationResult(
                verified=False,
                role=Role.SUPERVISOR,
                reason="wrong_passphrase",
            )
        return RoleVerificationResult(
            verified=True,
            role=Role.SUPERVISOR,
            reason="verified",
        )

    def is_configured(self) -> bool:
        return os.path.exists(self._role_path)

    def clear(self) -> tuple[bool, str]:
        """Overwrite and remove the stored supervisor passphrase."""
        if not os.path.exists(self._role_path):
            return True, text.DUAL_APPROVAL_SUPERVISOR_CLEARED
        try:
            size = max(os.path.getsize(self._role_path), 512)
            with open(self._role_path, "r+b") as handle:
                handle.write(os.urandom(size))
                handle.flush()
                os.fsync(handle.fileno())
            os.remove(self._role_path)
        except OSError:
            return False, text.DUAL_APPROVAL_SUPERVISOR_CLEAR_FAILED
        return True, text.DUAL_APPROVAL_SUPERVISOR_CLEARED

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _hash(self, passphrase: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256",
            passphrase.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
            dklen=PBKDF2_DKLEN,
        )

    def _read_supervisor(self) -> dict[str, str]:
        with open(self._role_path, "rb") as handle:
            data = handle.read()
        plaintext = self._cipher.decrypt(
            data,
            too_short_message="role state is too short",
            auth_failed_message="role state authentication failed",
        )
        payload: dict[str, object] = json.loads(plaintext.decode("utf-8"))
        supervisor = payload["supervisor"]
        if not isinstance(supervisor, dict):
            raise ValueError("role state supervisor entry is not a dict")
        return {str(k): str(v) for k, v in supervisor.items()}


