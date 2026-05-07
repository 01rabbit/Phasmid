"""SH-10: Scenario tests for brick (local access path clear) irreversibility.

Claim coverage:
  CLM-01  Bricking overwrites vault.bin with random data.
  CLM-02  Bricking preserves the container file size.
  CLM-03  Bricking destroys the local access key file.
  CLM-04  Bricking is idempotent (double-brick is safe).

Scenario phases follow the naming convention from docs/TESTING_GUIDELINES.md.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.config import VAULT_KEY_NAME
from phasmid.vault_core import PhasmidVault


def _make_vault(tmp: str) -> PhasmidVault:
    vault = PhasmidVault(
        os.path.join(tmp, "vault.bin"),
        size_mb=1,
        state_dir=os.path.join(tmp, "state"),
    )
    vault.ARGON2_MEMORY_COST = 1024
    vault.ARGON2_ITERATIONS = 1
    vault.ARGON2_LANES = 1
    vault.format_container()
    return vault


class BrickIrreversibilityScenario(unittest.TestCase):
    """Verifies claims CLM-01 through CLM-04."""

    # ------------------------------------------------------------------
    # CLM-01 + CLM-02: content and size after brick
    # ------------------------------------------------------------------

    def test_claim_CLM01_brick_overwrites_container_with_random_bytes(self):
        """After brick, vault.bin bytes differ from pre-brick content."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            seq = ["ref_matched"]
            vault.store("pw", b"secret-payload", seq, filename="data.bin", mode="dummy")

            before = open(vault.path, "rb").read()
            vault.silent_brick()
            after = open(vault.path, "rb").read()

            self.assertNotEqual(before, after)

    def test_claim_CLM02_brick_preserves_container_file_size(self):
        """After brick, vault.bin file size is unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            seq = ["ref_matched"]
            vault.store("pw", b"secret-payload", seq, filename="data.bin", mode="dummy")

            size_before = os.path.getsize(vault.path)
            vault.silent_brick()
            size_after = os.path.getsize(vault.path)

            self.assertEqual(size_before, size_after)

    # ------------------------------------------------------------------
    # CLM-03: access key destruction
    # ------------------------------------------------------------------

    def test_claim_CLM03_brick_destroys_access_key_file(self):
        """After brick, the local access key file no longer exists."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            access_key_path = os.path.join(tmp, "state", VAULT_KEY_NAME)

            self.assertTrue(
                os.path.exists(access_key_path),
                "Access key must exist before brick",
            )

            vault.silent_brick()

            self.assertFalse(
                os.path.exists(access_key_path),
                "Access key must not exist after brick",
            )

    # ------------------------------------------------------------------
    # Post-brick recovery failure
    # ------------------------------------------------------------------

    def test_scenario_brick_irreversibility_post_brick_retrieve_returns_none(self):
        """After brick, retrieve with original passphrase returns (None, None)."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            seq = ["ref_matched"]
            vault.store("correct-pw", b"secret", seq, filename="data.bin", mode="dummy")

            vault.silent_brick()

            result = vault.retrieve("correct-pw", seq, mode="dummy")
            self.assertEqual(
                result,
                (None, None),
                "Retrieve after brick must fail even with original passphrase",
            )

    def test_scenario_brick_irreversibility_wrong_pw_also_fails(self):
        """After brick, any passphrase fails — brick is not a passphrase gate."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            seq = ["ref_matched"]
            vault.store("correct-pw", b"secret", seq, filename="data.bin", mode="dummy")

            vault.silent_brick()

            result = vault.retrieve("wrong-pw", seq, mode="dummy")
            self.assertEqual(result, (None, None))

    # ------------------------------------------------------------------
    # CLM-04: idempotency
    # ------------------------------------------------------------------

    def test_claim_CLM04_brick_is_idempotent(self):
        """A second brick call on an already-bricked container does not raise."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.silent_brick()
            try:
                vault.silent_brick()
            except Exception as exc:
                self.fail(f"Second brick raised: {exc}")

    def test_scenario_brick_irreversibility_double_brick_size_unchanged(self):
        """Container size remains the same after two consecutive brick calls."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.silent_brick()
            size_after_first = os.path.getsize(vault.path)

            vault.silent_brick()
            size_after_second = os.path.getsize(vault.path)

            self.assertEqual(size_after_first, size_after_second)

    # ------------------------------------------------------------------
    # Container exterior checks (size claim detail)
    # ------------------------------------------------------------------

    def test_scenario_brick_irreversibility_bricked_content_is_not_all_zeros(self):
        """Bricked vault.bin is random bytes, not a zero-fill."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.silent_brick()
            content = open(vault.path, "rb").read()
            self.assertNotEqual(content, b"\x00" * len(content))

    def test_scenario_brick_irreversibility_size_matches_configured_mb(self):
        """Container size after brick equals the size set at creation."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            expected_size = vault.size
            vault.silent_brick()
            actual_size = os.path.getsize(vault.path)
            self.assertEqual(actual_size, expected_size)


if __name__ == "__main__":
    unittest.main()
