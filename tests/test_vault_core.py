import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.vault_core import PhasmidVault


class PhasmidVaultV3Tests(unittest.TestCase):
    def make_vault(self, path):
        vault = PhasmidVault(
            path, size_mb=1, state_dir=os.path.join(os.path.dirname(path), "state")
        )
        vault.ARGON2_MEMORY_COST = 1024
        vault.ARGON2_ITERATIONS = 1
        vault.ARGON2_LANES = 1
        vault.format_container()
        return vault

    def test_default_argon2_parameters_are_pi_zero_profile(self):
        vault = PhasmidVault("unused.bin")
        self.assertEqual(vault.ARGON2_MEMORY_COST, 32768)
        self.assertEqual(vault.ARGON2_ITERATIONS, 2)
        self.assertEqual(vault.ARGON2_LANES, 1)

    def test_round_trip_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="../payload.txt", mode="dummy")

            self.assertEqual(
                vault.retrieve("pw", seq, mode="dummy"), (b"payload", "payload.txt")
            )
            self.assertEqual(vault.retrieve("bad-pw", seq, mode="dummy"), (None, None))

    def test_open_and_restricted_recovery_passwords_share_image_key_but_report_different_policy(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            vault.store(
                "open-pw",
                b"payload",
                seq,
                filename="payload.bin",
                mode="dummy",
                restricted_recovery_password="recovery-pw",
            )

            self.assertEqual(
                vault.retrieve_with_policy("open-pw", seq, mode="dummy"),
                (b"payload", "payload.bin", PhasmidVault.OPEN_ROLE),
            )
            self.assertEqual(
                vault.retrieve_with_policy("recovery-pw", seq, mode="dummy"),
                (b"payload", "payload.bin", PhasmidVault.PURGE_ROLE),
            )

    def test_open_and_restricted_recovery_passwords_must_be_different(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            with self.assertRaises(ValueError):
                vault.store(
                    "same",
                    b"payload",
                    seq,
                    mode="dummy",
                    restricted_recovery_password="same",
                )

    def test_empty_payload_retrieves_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_secret_matched"]

            vault.store("pw", b"", seq, filename="empty.bin", mode="secret")

            self.assertEqual(
                vault.retrieve("pw", seq, mode="secret"), (b"", "empty.bin")
            )

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
            self.assertEqual(
                vault.retrieve("pw", seq, mode="dummy"), (b"payload", "one.bin")
            )

    def test_container_does_not_store_plaintext_magic_or_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vault.bin")
            vault = self.make_vault(path)
            seq = ["reference_dummy_matched"]

            vault.store(
                "pw", b"payload", seq, filename="sensitive-name.txt", mode="dummy"
            )

            with open(path, "rb") as handle:
                raw = handle.read(vault.size // 2)
            self.assertNotIn(b"GVP2", raw)
            self.assertNotIn(b"ghostvault", raw)
            self.assertNotIn(b"jes-v3", raw)
            self.assertNotIn(b"sensitive-name.txt", raw)

    def test_purge_other_mode_disables_alternate_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            dummy_seq = ["reference_dummy_matched"]
            secret_seq = ["reference_secret_matched"]

            vault.store("pw", b"dummy", dummy_seq, filename="dummy.bin", mode="dummy")
            vault.store(
                "pw", b"secret", secret_seq, filename="secret.bin", mode="secret"
            )

            vault.purge_other_mode("dummy")

            self.assertEqual(
                vault.retrieve("pw", dummy_seq, mode="dummy"), (b"dummy", "dummy.bin")
            )
            self.assertEqual(
                vault.retrieve("pw", secret_seq, mode="secret"), (None, None)
            )

    def test_destroy_access_key_disables_retrieval(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="payload.bin", mode="dummy")
            self.assertEqual(
                vault.retrieve("pw", seq, mode="dummy"), (b"payload", "payload.bin")
            )

            vault.destroy_access_keys()

            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (None, None))

    def test_format_container_can_rotate_access_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vault.bin")
            vault = self.make_vault(path)
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="payload.bin", mode="dummy")
            with open(vault.access_key_path, "rb") as handle:
                old_key = handle.read()
            with open(path, "rb") as handle:
                old_container = handle.read()

            vault.format_container(rotate_access_key=True)

            with open(vault.access_key_path, "rb") as handle:
                new_key = handle.read()
            self.assertNotEqual(old_key, new_key)

            with open(path, "wb") as handle:
                handle.write(old_container)
            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (None, None))


    # ------------------------------------------------------------------
    # Key-material invalidation sequence (Issue #4)
    # ------------------------------------------------------------------

    def test_silent_brick_disables_retrieval_for_all_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]

            vault.store("pw", b"payload", seq, filename="f.bin", mode="dummy")
            self.assertIsNotNone(vault.retrieve("pw", seq, mode="dummy")[0])

            vault.silent_brick()

            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (None, None))

    def test_silent_brick_removes_access_key_before_container_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]
            vault.store("pw", b"payload", seq, filename="f.bin", mode="dummy")

            key_path = vault.access_key_path
            destroyed_order = []

            original_destroy = vault.destroy_access_keys
            original_brick = vault.container_layout.silent_brick

            def tracking_destroy():
                destroyed_order.append("key")
                original_destroy()

            def tracking_brick():
                destroyed_order.append("container")
                original_brick()

            vault.destroy_access_keys = tracking_destroy
            vault.container_layout.silent_brick = tracking_brick
            vault.silent_brick()

            self.assertEqual(destroyed_order, ["key", "container"])
            self.assertFalse(os.path.exists(key_path))

    def test_purge_mode_disables_retrieval_for_purged_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            d_seq = ["reference_dummy_matched"]
            s_seq = ["reference_secret_matched"]

            vault.store("pw", b"dummy_data", d_seq, filename="d.bin", mode="dummy")
            vault.store("pw", b"secret_data", s_seq, filename="s.bin", mode="secret")

            vault.purge_mode("dummy")

            self.assertEqual(vault.retrieve("pw", d_seq, mode="dummy"), (None, None))
            self.assertEqual(
                vault.retrieve("pw", s_seq, mode="secret"), (b"secret_data", "s.bin")
            )

    def test_container_overwrite_alone_does_not_restore_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            seq = ["reference_dummy_matched"]
            vault.store("pw", b"payload", seq, filename="f.bin", mode="dummy")

            with open(vault.path, "rb") as handle:
                original_container = handle.read()

            vault.destroy_access_keys()
            with open(vault.path, "wb") as handle:
                handle.write(original_container)

            self.assertEqual(vault.retrieve("pw", seq, mode="dummy"), (None, None))

    def test_restricted_recovery_password_triggers_purge_on_retrieve(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = self.make_vault(os.path.join(tmp, "vault.bin"))
            d_seq = ["reference_dummy_matched"]
            s_seq = ["reference_secret_matched"]
            vault.store(
                "normal-pw",
                b"dummy_data",
                d_seq,
                filename="d.bin",
                mode="dummy",
                restricted_recovery_password="purge-pw",
            )
            vault.store("pw", b"secret_data", s_seq, filename="s.bin", mode="secret")

            _data, _fn, role = vault.retrieve_with_policy("purge-pw", d_seq, mode="dummy")
            self.assertEqual(role, vault.PURGE_ROLE)


if __name__ == "__main__":
    unittest.main()
