import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.gv_core import GhostVault


class GhostVaultV3Tests(unittest.TestCase):
    def make_vault(self, path):
        vault = GhostVault(path, size_mb=1, state_dir=os.path.join(os.path.dirname(path), "state"))
        vault.ARGON2_MEMORY_COST = 1024
        vault.ARGON2_ITERATIONS = 1
        vault.ARGON2_LANES = 1
        vault.format_container()
        return vault

    def test_default_argon2_parameters_are_pi_zero_profile(self):
        vault = GhostVault("unused.bin")
        self.assertEqual(vault.ARGON2_MEMORY_COST, 32768)
        self.assertEqual(vault.ARGON2_ITERATIONS, 2)
        self.assertEqual(vault.ARGON2_LANES, 1)

    def test_round_trip_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="../payload.txt", mode="dummy")

            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (b"payload", "payload.txt"))
            self.assertEqual(vault.retrieve("bad-pw", seq, mode="dummy"), (None, None))

    def test_empty_payload_retrieves_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_secret_matched"]

            vault.store("pw", b"", seq, filename="empty.bin", mode="secret")

            self.assertEqual(vault.retrieve("pw", seq, mode="secret"), (b"", "empty.bin"))

    def test_repeated_store_uses_fresh_salt_and_nonce(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vault.bin")
            vault = self.make_vault(path)
            seq = ["reference_dummy_matched"]
            prefix_len = vault.SALT_SIZE + vault.NONCE_SIZE

            vault.store("pw", b"payload", seq, filename="one.bin", mode="dummy")
            with open(path, "rb") as handle:
                first_record_prefix = handle.read(prefix_len)

            vault.store("pw", b"payload", seq, filename="one.bin", mode="dummy")
            with open(path, "rb") as handle:
                second_record_prefix = handle.read(prefix_len)

            self.assertNotEqual(first_record_prefix, second_record_prefix)
            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (b"payload", "one.bin"))

    def test_container_does_not_store_plaintext_magic_or_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vault.bin")
            vault = self.make_vault(path)
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="sensitive-name.txt", mode="dummy")

            with open(path, "rb") as handle:
                raw = handle.read(vault.size // 2)
            self.assertNotIn(b"GVP2", raw)
            self.assertNotIn(b"ghostvault", raw)
            self.assertNotIn(b"sensitive-name.txt", raw)

    def test_purge_other_mode_disables_alternate_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            dummy_seq = ["reference_dummy_matched"]
            secret_seq = ["reference_secret_matched"]

            vault.store("pw", b"dummy", dummy_seq, filename="dummy.bin", mode="dummy")
            vault.store("pw", b"secret", secret_seq, filename="secret.bin", mode="secret")

            vault.purge_other_mode("dummy")

            self.assertEqual(vault.retrieve("pw", dummy_seq, mode="dummy"), (b"dummy", "dummy.bin"))
            self.assertEqual(vault.retrieve("pw", secret_seq, mode="secret"), (None, None))

    def test_destroy_access_key_disables_retrieval(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="payload.bin", mode="dummy")
            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (b"payload", "payload.bin"))

            vault.destroy_access_keys()

            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (None, None))


if __name__ == "__main__":
    unittest.main()
