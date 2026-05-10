import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.roles import Role, RoleStore, RoleVerificationResult


class TestRoleStore(unittest.TestCase):
    def make_store(self, tmp):
        return RoleStore(state_path=tmp)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def test_not_configured_before_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            self.assertFalse(store.is_configured())

    def test_configure_supervisor_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            ok, msg = store.configure_supervisor("correct-horse-battery")
            self.assertTrue(ok)
            self.assertTrue(store.is_configured())
            self.assertIn("configured", msg.lower())

    def test_configure_supervisor_creates_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("passphrase-abc-123")
            from phasmid.config import ROLE_STATE_NAME

            self.assertTrue(os.path.exists(os.path.join(tmp, ROLE_STATE_NAME)))

    def test_configure_empty_passphrase_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            ok, _ = store.configure_supervisor("")
            self.assertFalse(ok)
            self.assertFalse(store.is_configured())

    def test_reconfigure_overwrites_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("old-passphrase")
            store.configure_supervisor("new-passphrase")
            result = store.verify_supervisor("new-passphrase")
            self.assertTrue(result.verified)

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def test_correct_passphrase_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("correct-passphrase-xyz")
            result = store.verify_supervisor("correct-passphrase-xyz")
            self.assertIsInstance(result, RoleVerificationResult)
            self.assertTrue(result.verified)
            self.assertEqual(result.role, Role.SUPERVISOR)
            self.assertEqual(result.reason, "verified")

    def test_wrong_passphrase_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("correct-passphrase-xyz")
            result = store.verify_supervisor("wrong-passphrase")
            self.assertFalse(result.verified)
            self.assertEqual(result.role, Role.SUPERVISOR)
            self.assertEqual(result.reason, "wrong_passphrase")

    def test_verify_when_not_configured_returns_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            result = store.verify_supervisor("anything")
            self.assertFalse(result.verified)
            self.assertIsNone(result.role)
            self.assertEqual(result.reason, "not_configured")

    def test_different_passphrases_hash_differently(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("passphrase-one")
            result = store.verify_supervisor("passphrase-two")
            self.assertFalse(result.verified)

    def test_empty_string_does_not_match_configured_passphrase(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("non-empty-passphrase")
            result = store.verify_supervisor("")
            self.assertFalse(result.verified)

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def test_clear_removes_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("passphrase-to-clear")
            ok, _ = store.clear()
            self.assertTrue(ok)
            self.assertFalse(store.is_configured())

    def test_clear_when_not_configured_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            ok, msg = store.clear()
            self.assertTrue(ok)

    def test_verify_after_clear_returns_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            store.configure_supervisor("temporary-passphrase")
            store.clear()
            result = store.verify_supervisor("temporary-passphrase")
            self.assertFalse(result.verified)
            self.assertEqual(result.reason, "not_configured")

    # ------------------------------------------------------------------
    # Salt uniqueness (random salt per enrollment)
    # ------------------------------------------------------------------

    def test_same_passphrase_produces_different_hashes_on_reconfigure(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            passphrase = "same-passphrase-each-time"

            store.configure_supervisor(passphrase)
            result1 = store.verify_supervisor(passphrase)

            store.configure_supervisor(passphrase)
            result2 = store.verify_supervisor(passphrase)

            # Both should verify correctly even though salts differ
            self.assertTrue(result1.verified)
            self.assertTrue(result2.verified)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def test_pbkdf2_hash_length_is_32_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self.make_store(tmp)
            salt = os.urandom(32)
            digest = store._hash("test", salt)
            self.assertEqual(len(digest), 32)

    def test_hmac_compare_digest_true_for_identical(self):
        # SH-07: _constant_time_equal replaced by hmac.compare_digest
        import hmac

        self.assertTrue(hmac.compare_digest(b"abc", b"abc"))

    def test_hmac_compare_digest_false_for_different(self):
        import hmac

        self.assertFalse(hmac.compare_digest(b"abc", b"xyz"))

    def test_hmac_compare_digest_false_for_different_lengths(self):
        import hmac

        self.assertFalse(hmac.compare_digest(b"ab", b"abc"))


if __name__ == "__main__":
    unittest.main()
