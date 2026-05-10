"""SH-13: Binary-level headerless container invariant tests.

Claim coverage:
  CLM-05  vault.bin has no plaintext magic header or format marker.

Verifies that:
- The first bytes of vault.bin do not match any known binary magic signatures.
- The format marker ("jes-v3") does not appear as plaintext anywhere in vault.bin.
- Shannon entropy of vault.bin is consistent with random/encrypted data.
- No byte-frequency anomalies that would help a static analysis tool classify
  the file (e.g., all-zeros, repeating patterns).

The tests create a freshly formatted vault and a vault with stored data to
verify both the empty and populated states.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.record_cypher import RecordCipher
from phasmid.vault_core import PhasmidVault
from tests.scenarios.known_magics import KNOWN_SIGNATURES


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


def _shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits per byte (0–8)."""
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


class TestClaimCLM05HeaderlessInvariant(unittest.TestCase):
    """Verifies CLM-05: vault.bin has no plaintext magic header."""

    def _read_vault(self, vault: PhasmidVault) -> bytes:
        with open(vault.path, "rb") as f:
            return f.read()

    # ------------------------------------------------------------------
    # Fresh (empty) vault
    # ------------------------------------------------------------------

    def test_claim_CLM05_fresh_vault_has_no_known_magic_at_offset_0(self):
        """A freshly formatted vault must not start with any known magic signature."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            data = self._read_vault(vault)
            violations: list[str] = []
            for name, offset, sig in KNOWN_SIGNATURES:
                if offset + len(sig) <= len(data):
                    if data[offset : offset + len(sig)] == sig:
                        violations.append(f"  offset={offset}: {name} ({sig!r})")
            self.assertFalse(
                violations,
                "Fresh vault.bin matches known magic signatures:\n"
                + "\n".join(violations),
            )

    def test_claim_CLM05_fresh_vault_contains_no_plaintext_format_marker(self):
        """The internal format marker 'jes-v3' must not appear as plaintext."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            data = self._read_vault(vault)
            marker = RecordCipher.FORMAT_MARKER.encode("utf-8")
            self.assertNotIn(
                marker,
                data,
                f"Format marker {marker!r} found as plaintext in vault.bin",
            )

    def test_scenario_headerless_invariant_fresh_vault_high_entropy(self):
        """Fresh vault.bin must have Shannon entropy >= 7.9 bits/byte (near-random)."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            data = self._read_vault(vault)
            entropy = _shannon_entropy(data)
            self.assertGreaterEqual(
                entropy,
                7.9,
                f"Fresh vault entropy too low: {entropy:.3f} bits/byte (expected >= 7.9)",
            )

    def test_scenario_headerless_invariant_fresh_vault_not_all_zeros(self):
        """Fresh vault.bin must not be zero-filled."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            data = self._read_vault(vault)
            self.assertNotEqual(data, b"\x00" * len(data))

    # ------------------------------------------------------------------
    # Populated vault (after store)
    # ------------------------------------------------------------------

    def test_claim_CLM05_populated_vault_has_no_known_magic(self):
        """A vault with stored data must not start with any known magic signature."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.store(
                "passphrase-xyz-123",
                b"sensitive-content",
                ["ref_matched"],
                filename="data.bin",
                mode="dummy",
            )
            data = self._read_vault(vault)
            violations: list[str] = []
            for name, offset, sig in KNOWN_SIGNATURES:
                if offset + len(sig) <= len(data):
                    if data[offset : offset + len(sig)] == sig:
                        violations.append(f"  offset={offset}: {name} ({sig!r})")
            self.assertFalse(
                violations,
                "Populated vault.bin matches known magic:\n" + "\n".join(violations),
            )

    def test_claim_CLM05_populated_vault_no_plaintext_format_marker(self):
        """Format marker must not appear as plaintext in a populated vault."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.store(
                "passphrase-xyz-123",
                b"sensitive-content",
                ["ref_matched"],
                filename="data.bin",
                mode="dummy",
            )
            data = self._read_vault(vault)
            marker = RecordCipher.FORMAT_MARKER.encode("utf-8")
            self.assertNotIn(
                marker,
                data,
                f"Format marker {marker!r} found as plaintext in populated vault.bin",
            )

    def test_scenario_headerless_invariant_populated_vault_high_entropy(self):
        """Populated vault.bin must have Shannon entropy >= 7.9 bits/byte."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            vault.store(
                "passphrase-xyz-123",
                b"sensitive-content",
                ["ref_matched"],
                filename="data.bin",
                mode="dummy",
            )
            data = self._read_vault(vault)
            entropy = _shannon_entropy(data)
            self.assertGreaterEqual(
                entropy,
                7.9,
                f"Populated vault entropy too low: {entropy:.3f} bits/byte",
            )

    # ------------------------------------------------------------------
    # Statistical checks
    # ------------------------------------------------------------------

    def test_scenario_headerless_invariant_byte_distribution_not_degenerate(self):
        """All 256 byte values must appear at least once in a 1 MB vault."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(tmp)
            data = self._read_vault(vault)
            counts = Counter(data)
            missing = [b for b in range(256) if counts[b] == 0]
            self.assertEqual(
                missing,
                [],
                f"{len(missing)} byte values missing from vault.bin: {missing[:10]}...",
            )

    def test_scenario_headerless_invariant_known_magics_list_size(self):
        """Signature list must contain at least 20 entries."""
        self.assertGreaterEqual(
            len(KNOWN_SIGNATURES),
            20,
            "known_magics.py must define at least 20 signatures",
        )


if __name__ == "__main__":
    unittest.main()
