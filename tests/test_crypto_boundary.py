import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm import crypto_boundary


class CryptoBoundaryTests(unittest.TestCase):
    def tearDown(self):
        crypto_boundary._SELF_TEST_PASSED = False

    def test_self_tests_pass(self):
        self.assertTrue(crypto_boundary.ensure_crypto_self_tests())

    def test_random_bytes_rejects_invalid_length(self):
        with self.assertRaises(ValueError):
            crypto_boundary.random_bytes(0)

    def test_self_test_failure_is_neutral(self):
        with mock.patch.object(
            crypto_boundary, "_check_random_bytes", side_effect=RuntimeError("detail")
        ):
            with self.assertRaises(crypto_boundary.CryptoSelfTestError) as ctx:
                crypto_boundary.ensure_crypto_self_tests()

        self.assertEqual(str(ctx.exception), "cryptographic self-test failed")


if __name__ == "__main__":
    unittest.main()
