from __future__ import annotations

import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import state_secret


class LocalStateCipher:
    """Shared AES-GCM helper for local state blobs backed by a state key file."""

    def __init__(
        self,
        *,
        state_key_path: str,
        aad: bytes,
        local_key_suffix: bytes | None = None,
    ) -> None:
        self.state_key_path = state_key_path
        self.aad = aad
        self.local_key_suffix = local_key_suffix

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(12)
        return nonce + AESGCM(self.encryption_key()).encrypt(nonce, plaintext, self.aad)

    def decrypt(
        self,
        payload: bytes,
        *,
        too_short_message: str,
        auth_failed_message: str,
    ) -> bytes:
        if len(payload) <= 12:
            raise ValueError(too_short_message)

        nonce, ciphertext = payload[:12], payload[12:]
        try:
            return AESGCM(self.encryption_key()).decrypt(nonce, ciphertext, self.aad)
        except InvalidTag as exc:
            raise ValueError(auth_failed_message) from exc

    def encryption_key(self) -> bytes:
        external_value = state_secret()
        if external_value:
            return hashlib.sha256(external_value.encode("utf-8")).digest()

        key = self._load_or_create_local_state_key()
        if self.local_key_suffix is None:
            return key
        return hashlib.sha256(key + self.local_key_suffix).digest()

    def _load_or_create_local_state_key(self) -> bytes:
        if os.path.exists(self.state_key_path):
            with open(self.state_key_path, "rb") as handle:
                key = handle.read()
            if len(key) == 32:
                return key

        key = os.urandom(32)
        with open(self.state_key_path, "wb") as handle:
            handle.write(key)
        try:
            os.chmod(self.state_key_path, 0o600)
        except OSError:
            pass
        return key
