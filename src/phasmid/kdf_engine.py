"""Key Derivation Engine for Phasmid cryptographic operations."""

import os

from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from .config import (
    VAULT_KEY_NAME,
    hardware_secret_file,
    hardware_secret_prompt_enabled,
    hardware_secret_value,
)
from .crypto_params import (
    ACCESS_KEY_SIZE,
    ARGON2_ITERATIONS,
    ARGON2_KEY_LENGTH,
    ARGON2_LANES,
    ARGON2_MEMORY_COST,
)
from .kdf_providers import (
    FileSecretProvider,
    HardwareBindingProvider,
    PromptSecretProvider,
    SecretProvider,
    StaticSecretProvider,
)


class KDFEngine:
    """Handles Argon2id key derivation and local access key management."""

    ARGON2_ITERATIONS = ARGON2_ITERATIONS
    ARGON2_LANES = ARGON2_LANES
    ARGON2_MEMORY_COST = ARGON2_MEMORY_COST
    ACCESS_KEY_SIZE = ACCESS_KEY_SIZE

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        self.access_key_path = os.path.join(state_dir, VAULT_KEY_NAME)
        self.providers: list[SecretProvider] = [
            FileSecretProvider(hardware_secret_file()),
            StaticSecretProvider(hardware_secret_value()),
            HardwareBindingProvider(),
        ]
        if hardware_secret_prompt_enabled():
            self.providers.append(PromptSecretProvider())

    def derive_key(
        self,
        password: str,
        gesture_sequence: list[str],
        mode: str,
        salt: bytes,
        password_role: str = "open",
        create_access_key: bool = False,
    ) -> bytes:
        """Derive a 32-byte key using Argon2id."""
        kdf = Argon2id(
            salt=salt,
            length=ARGON2_KEY_LENGTH,
            iterations=self.ARGON2_ITERATIONS,
            lanes=self.ARGON2_LANES,
            memory_cost=self.ARGON2_MEMORY_COST,
            secret=self._kdf_secret(create_access_key=create_access_key),
        )
        context = self._context_password(
            password, gesture_sequence, mode, password_role
        )
        return kdf.derive(context)

    def _context_password(
        self,
        password: str,
        gesture_sequence: list[str],
        mode: str,
        password_role: str,
    ) -> bytes:
        """Combine password components into KDF input."""
        gesture_str = "-".join(gesture_sequence)
        return f"{password}_{gesture_str}_{mode}_{password_role}".encode()

    def _kdf_secret(self, create_access_key: bool = False) -> bytes:
        """Build multi-source KDF input."""
        parts: list[bytes] = []

        local_key = self._load_or_create_access_key(create=create_access_key)
        if local_key is not None:
            parts.append(local_key)

        for provider in self.providers:
            secret = provider.get_secret()
            if secret:
                parts.append(secret)

        return b"".join(parts)

    def _load_or_create_access_key(self, create: bool = False) -> bytes | None:
        """Load existing access key or create new one if requested."""
        if os.path.exists(self.access_key_path):
            with open(self.access_key_path, "rb") as handle:
                key = handle.read()
            if len(key) == self.ACCESS_KEY_SIZE:
                return key
            raise ValueError("invalid local vault access key")

        if not create:
            return None

        return self._write_new_access_key()

    def _write_new_access_key(self) -> bytes:
        """Generate and persist a new access key."""
        os.makedirs(self.state_dir, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.state_dir, 0o700)
        except OSError:
            pass
        key = os.urandom(self.ACCESS_KEY_SIZE)
        with open(self.access_key_path, "wb") as handle:
            handle.write(key)
        try:
            os.chmod(self.access_key_path, 0o600)
        except OSError:
            pass
        return key

    def get_or_create_access_key(self) -> bytes:
        """Get existing access key or create new one."""
        key = self._load_or_create_access_key(create=True)
        if key is None:
            raise RuntimeError("failed to create local vault access key")
        return key

    def rotate_access_key(self) -> None:
        """Replace the current access key with a new random one."""
        if os.path.exists(self.access_key_path):
            os.unlink(self.access_key_path)
        self._write_new_access_key()

    def destroy_access_keys(self) -> None:
        """Securely remove the access key file."""
        if os.path.exists(self.access_key_path):
            try:
                length = os.path.getsize(self.access_key_path)
                with open(self.access_key_path, "r+b") as handle:
                    handle.seek(0)
                    handle.write(os.urandom(max(length, self.ACCESS_KEY_SIZE)))
                os.remove(self.access_key_path)
            except OSError:
                pass
