"""SH-06: Argon2id parameter centralization and cross-parameter compatibility.

Verifies that:
- KDFEngine and PhasmidVault both read parameters from crypto_params.py.
- crypto_params constants match the values expected by the current format version.
- A key derived with the canonical parameters is stable (deterministic for a
  fixed salt + password + secret).
- Changing any Argon2id parameter produces a different derived key (regression
  guard against accidental parameter drift).
"""

import os

from phasmid.crypto_params import (
    ARGON2_ITERATIONS,
    ARGON2_KEY_LENGTH,
    ARGON2_LANES,
    ARGON2_MEMORY_COST,
    VAULT_FORMAT_VERSION,
)
from phasmid.kdf_engine import KDFEngine
from phasmid.vault_core import PhasmidVault


class TestParamCentralization:
    def test_kdf_engine_reads_from_crypto_params(self):
        assert KDFEngine.ARGON2_ITERATIONS == ARGON2_ITERATIONS
        assert KDFEngine.ARGON2_LANES == ARGON2_LANES
        assert KDFEngine.ARGON2_MEMORY_COST == ARGON2_MEMORY_COST

    def test_vault_core_reads_from_crypto_params(self):
        assert PhasmidVault.ARGON2_ITERATIONS == ARGON2_ITERATIONS
        assert PhasmidVault.ARGON2_LANES == ARGON2_LANES
        assert PhasmidVault.ARGON2_MEMORY_COST == ARGON2_MEMORY_COST
        assert PhasmidVault.FORMAT_VERSION == VAULT_FORMAT_VERSION

    def test_vault_format_version_is_3(self):
        # If this test fails, a format bump was intentional — update this value.
        assert VAULT_FORMAT_VERSION == 3

    def test_argon2_key_length_is_32(self):
        assert ARGON2_KEY_LENGTH == 32

    def test_argon2_memory_cost_meets_owasp_minimum(self):
        # OWASP 2023 minimum: 19 456 KiB.  We must exceed it.
        assert ARGON2_MEMORY_COST >= 19_456

    def test_argon2_iterations_at_least_2(self):
        assert ARGON2_ITERATIONS >= 2


class TestKDFDeterminism:
    """Derived key must be stable for a given (password, salt, secret) tuple."""

    def test_derive_key_deterministic(self, tmp_path):
        engine = KDFEngine(str(tmp_path))
        salt = b"\x00" * 16
        key1 = engine.derive_key("password", [], "normal", salt)
        key2 = engine.derive_key("password", [], "normal", salt)
        assert key1 == key2

    def test_derive_key_length(self, tmp_path):
        engine = KDFEngine(str(tmp_path))
        salt = os.urandom(16)
        key = engine.derive_key("password", [], "normal", salt)
        assert len(key) == ARGON2_KEY_LENGTH

    def test_different_passwords_produce_different_keys(self, tmp_path):
        engine = KDFEngine(str(tmp_path))
        salt = b"\x00" * 16
        k1 = engine.derive_key("password1", [], "normal", salt)
        k2 = engine.derive_key("password2", [], "normal", salt)
        assert k1 != k2

    def test_different_salts_produce_different_keys(self, tmp_path):
        engine = KDFEngine(str(tmp_path))
        k1 = engine.derive_key("password", [], "normal", b"\x00" * 16)
        k2 = engine.derive_key("password", [], "normal", b"\xff" * 16)
        assert k1 != k2


class TestParamChangeProducesDifferentKey:
    """Guard against silent parameter drift between format versions."""

    def _derive(self, tmp_path, iterations, memory_cost, lanes):
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

        kdf = Argon2id(
            salt=b"\x00" * 16,
            length=32,
            iterations=iterations,
            lanes=lanes,
            memory_cost=memory_cost,
        )
        return kdf.derive(b"test-password")

    def test_iterations_change_changes_key(self, tmp_path):
        k1 = self._derive(tmp_path, ARGON2_ITERATIONS, ARGON2_MEMORY_COST, ARGON2_LANES)
        k2 = self._derive(
            tmp_path, ARGON2_ITERATIONS + 1, ARGON2_MEMORY_COST, ARGON2_LANES
        )
        assert k1 != k2

    def test_memory_change_changes_key(self, tmp_path):
        k1 = self._derive(tmp_path, ARGON2_ITERATIONS, ARGON2_MEMORY_COST, ARGON2_LANES)
        k2 = self._derive(
            tmp_path, ARGON2_ITERATIONS, ARGON2_MEMORY_COST + 1024, ARGON2_LANES
        )
        assert k1 != k2
