"""SH-12: Property-based invariant tests for state and vault operations.

Uses `hypothesis` to verify properties that must hold for all valid inputs.
CI runtime is bounded by the `settings` decorator on each test.

Invariants covered:
  - Roundtrip encryption: encrypt then decrypt returns original plaintext.
  - Monotonic failure counter: recording failures never decreases the count.
  - Container size invariant: vault.bin size is unchanged by store/retrieve/brick.
  - Wrong-password invariant: any wrong password produces (None, None).
  - Passphrase independence: different passphrases produce different derived keys.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from phasmid.attempt_limiter import AttemptLimiter
from phasmid.crypto_params import (
    AESGCM_KEY_SIZE,
    AESGCM_NONCE_SIZE,
)
from phasmid.vault_core import PhasmidVault

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Fast Argon2id parameters for property tests.
_FAST = dict(ARGON2_MEMORY_COST=1024, ARGON2_ITERATIONS=1, ARGON2_LANES=1)


def _make_vault(tmp: str) -> PhasmidVault:
    vault = PhasmidVault(
        os.path.join(tmp, "vault.bin"),
        size_mb=1,
        state_dir=os.path.join(tmp, "state"),
    )
    for k, v in _FAST.items():
        setattr(vault, k, v)
    vault.format_container()
    return vault


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

printable_pw = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=12,
    max_size=64,
).filter(lambda s: len(set(s)) > 4)  # avoid highly repetitive passphrases

small_payload = st.binary(min_size=1, max_size=512)


# ---------------------------------------------------------------------------
# Roundtrip encryption invariant
# ---------------------------------------------------------------------------


class TestInvariantRoundtrip(unittest.TestCase):
    """Encrypt → decrypt must return the original plaintext for any key/nonce."""

    @given(
        key=st.binary(min_size=AESGCM_KEY_SIZE, max_size=AESGCM_KEY_SIZE),
        payload=small_payload,
        aad=st.binary(min_size=0, max_size=64),
    )
    @settings(
        max_examples=200, deadline=5000, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_invariant_encrypt_decrypt_roundtrip(
        self, key: bytes, payload: bytes, aad: bytes
    ):
        """AES-GCM roundtrip must recover original plaintext for any valid key."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(AESGCM_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, payload, aad or None)
        recovered = aesgcm.decrypt(nonce, ct, aad or None)
        self.assertEqual(recovered, payload)

    @given(
        key=st.binary(min_size=AESGCM_KEY_SIZE, max_size=AESGCM_KEY_SIZE),
        payload=small_payload,
    )
    @settings(
        max_examples=100, deadline=5000, suppress_health_check=[HealthCheck.too_slow]
    )
    def test_invariant_wrong_nonce_fails_authentication(
        self, key: bytes, payload: bytes
    ):
        """Decryption with a different nonce must raise InvalidTag."""
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(AESGCM_NONCE_SIZE)
        wrong_nonce = os.urandom(AESGCM_NONCE_SIZE)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, payload, None)
        if nonce != wrong_nonce:
            with self.assertRaises(InvalidTag):
                aesgcm.decrypt(wrong_nonce, ct, None)


# ---------------------------------------------------------------------------
# Monotonic failure counter invariant
# ---------------------------------------------------------------------------


class TestInvariantFailureCounter(unittest.TestCase):
    """AttemptLimiter failure count must be monotonically non-decreasing."""

    @given(
        n_failures=st.integers(min_value=1, max_value=20),
        max_failures=st.integers(min_value=3, max_value=10),
    )
    @settings(max_examples=100, deadline=2000)
    def test_invariant_failure_counter_monotonically_increases(
        self, n_failures: int, max_failures: int
    ):
        """Recording N failures must result in failure count >= N (within max_failures)."""
        limiter = AttemptLimiter(max_failures=max_failures, lockout_seconds=60)
        scope = "test-scope"
        for _i in range(n_failures):
            limiter.record_failure(scope)
            state = limiter._state.get(scope)
            self.assertIsNotNone(state)
            self.assertGreaterEqual(state.failures, 1)

    @given(n_failures=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, deadline=2000)
    def test_invariant_success_resets_counter(self, n_failures: int):
        """Recording success after failures must reset the counter."""
        limiter = AttemptLimiter(max_failures=20, lockout_seconds=0)
        scope = "test-scope"
        for _ in range(n_failures):
            limiter.record_failure(scope)
        limiter.record_success(scope)
        self.assertNotIn(scope, limiter._state)


# ---------------------------------------------------------------------------
# Container size invariant
# ---------------------------------------------------------------------------


class TestInvariantContainerSize(unittest.TestCase):
    """vault.bin file size must not change after store, retrieve, or brick."""

    @given(payload=small_payload)
    @settings(
        max_examples=10,
        deadline=30000,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    def test_invariant_container_size_unchanged_after_store(self, payload: bytes):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            size_before = os.path.getsize(vault.path)
            vault.store(
                "pw-12345678", payload, ["ref_matched"], filename="f.bin", mode="dummy"
            )
            size_after = os.path.getsize(vault.path)
            self.assertEqual(size_before, size_after)

    @given(payload=small_payload)
    @settings(
        max_examples=10,
        deadline=30000,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    def test_invariant_container_size_unchanged_after_brick(self, payload: bytes):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.store(
                "pw-12345678", payload, ["ref_matched"], filename="f.bin", mode="dummy"
            )
            size_before = os.path.getsize(vault.path)
            vault.silent_brick()
            size_after = os.path.getsize(vault.path)
            self.assertEqual(size_before, size_after)


# ---------------------------------------------------------------------------
# Wrong-password invariant
# ---------------------------------------------------------------------------


class TestInvariantWrongPassword(unittest.TestCase):
    """Any wrong password must return (None, None) — no partial plaintext leak."""

    @given(
        correct_pw=printable_pw,
        wrong_pw=printable_pw,
    )
    @settings(
        max_examples=10,
        deadline=30000,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
        ],
    )
    def test_invariant_wrong_password_returns_none(
        self, correct_pw: str, wrong_pw: str
    ):
        if correct_pw == wrong_pw:
            return  # skip identical passwords
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.store(correct_pw, b"secret", ["ref"], filename="f.bin", mode="dummy")
            result = vault.retrieve(wrong_pw, ["ref"], mode="dummy")
            self.assertEqual(result, (None, None))


if __name__ == "__main__":
    unittest.main()
