import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.passphrase_policy import check_passphrase, check_store_passphrases


class PassphrasePolicyTests(unittest.TestCase):
    def test_rejects_empty_value(self):
        result = check_passphrase("")

        self.assertFalse(result.ok)
        self.assertIn("must not be empty", result.message)

    def test_rejects_short_value(self):
        with mock.patch.dict(os.environ, {"PHANTASM_MIN_PASSPHRASE_LENGTH": "10"}):
            result = check_passphrase("short")

        self.assertFalse(result.ok)
        self.assertIn("at least 10 characters", result.message)

    def test_rejects_repetitive_value(self):
        with mock.patch.dict(os.environ, {"PHANTASM_MIN_PASSPHRASE_LENGTH": "6"}):
            result = check_passphrase("aaaaaaaa")

        self.assertFalse(result.ok)
        self.assertIn("too repetitive", result.message)

    def test_accepts_reasonable_phrase(self):
        result = check_passphrase("field notes passphrase 2026")

        self.assertTrue(result.ok)

    def test_store_values_must_differ(self):
        result = check_store_passphrases(
            "field notes passphrase",
            "field notes passphrase",
        )

        self.assertFalse(result.ok)
        self.assertIn("must be different", result.message)


if __name__ == "__main__":
    unittest.main()
