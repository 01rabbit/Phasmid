import os
import tempfile
import unittest

from src.phantasm.record_cypher import RecordCipher


class TestRecordCipher(unittest.TestCase):
    def setUp(self):
        self.container_path = tempfile.mktemp()
        self.container_size = 10 * 1024 * 1024  # 10MB
        self.cipher = RecordCipher(self.container_path, self.container_size)
        # Create a dummy container file
        with open(self.container_path, "wb") as f:
            f.write(os.urandom(self.container_size))

    def tearDown(self):
        if os.path.exists(self.container_path):
            os.unlink(self.container_path)

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt_record and decrypt_record are inverses"""
        key = os.urandom(32)
        plaintext = b"Hello, World!"
        mode = "dummy"
        password_role = "open"
        filename = "test.txt"

        # Encrypt
        salt, nonce, ciphertext = self.cipher.encrypt_record(
            plaintext, key, mode, password_role, filename
        )

        # Decrypt
        decrypted_data, decrypted_filename, metadata = self.cipher.decrypt_record(
            ciphertext, key, salt, nonce, mode, password_role
        )

        self.assertEqual(decrypted_data, plaintext)
        self.assertEqual(decrypted_filename, filename)
        self.assertEqual(metadata["format"], "ghostvault-v3")
        self.assertEqual(metadata["version"], 3)
        self.assertEqual(metadata["password_role"], password_role)
        self.assertEqual(metadata["payload_len"], len(plaintext))

    def test_encrypt_decrypt_different_modes(self):
        """Test encryption/decryption with different modes and roles"""
        key = os.urandom(32)
        plaintext = b"Test data"
        test_cases = [
            ("dummy", "open"),
            ("dummy", "purge"),
            ("secret", "open"),
            ("secret", "purge"),
        ]

        for mode, password_role in test_cases:
            with self.subTest(mode=mode, password_role=password_role):
                salt, nonce, ciphertext = self.cipher.encrypt_record(
                    plaintext, key, mode, password_role
                )
                decrypted_data, _, _ = self.cipher.decrypt_record(
                    ciphertext, key, salt, nonce, mode, password_role
                )
                self.assertEqual(decrypted_data, plaintext)

    def test_decrypt_invalid_ciphertext(self):
        """Test that invalid ciphertext raises appropriate exceptions"""
        key = os.urandom(32)
        salt = os.urandom(16)
        nonce = os.urandom(12)
        invalid_ciphertext = b"invalid"

        with self.assertRaises(Exception):  # Could be InvalidTag or ValueError
            self.cipher.decrypt_record(invalid_ciphertext, key, salt, nonce, "dummy", "open")

    def test_decrypt_wrong_key(self):
        """Test decryption with wrong key fails"""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Secret data"
        mode = "dummy"
        password_role = "open"

        salt, nonce, ciphertext = self.cipher.encrypt_record(
            plaintext, key1, mode, password_role
        )

        with self.assertRaises(Exception):
            self.cipher.decrypt_record(ciphertext, key2, salt, nonce, mode, password_role)

    def test_randomize_slot(self):
        """Test that randomize_slot overwrites the slot with random data"""
        mode = "dummy"
        password_role = "open"

        # Get initial data in slot
        start, length = self.cipher._slot_span(mode, password_role)
        with open(self.container_path, "rb") as f:
            f.seek(start)
            initial_data = f.read(length)

        # Randomize slot
        self.cipher.randomize_slot(mode, password_role)

        # Check that data changed
        with open(self.container_path, "rb") as f:
            f.seek(start)
            randomized_data = f.read(length)

        self.assertNotEqual(initial_data, randomized_data)
        # Should be random, so not all zeros
        self.assertNotEqual(randomized_data, b"\x00" * length)

    def test_encrypt_payload_too_large(self):
        """Test that encrypting payload larger than capacity raises ValueError"""
        key = os.urandom(32)
        # Create a very large payload that exceeds capacity
        large_plaintext = b"x" * (self.container_size // 2)  # Larger than half container
        mode = "dummy"
        password_role = "open"

        with self.assertRaises(ValueError):
            self.cipher.encrypt_record(large_plaintext, key, mode, password_role)

    def test_metadata_validation(self):
        """Test that metadata is properly validated during decryption"""
        key = os.urandom(32)
        plaintext = b"Test"
        mode = "dummy"
        password_role = "open"

        salt, nonce, ciphertext = self.cipher.encrypt_record(
            plaintext, key, mode, password_role
        )

        # Decrypt with correct parameters should work
        data, filename, metadata = self.cipher.decrypt_record(
            ciphertext, key, salt, nonce, mode, password_role
        )
        self.assertEqual(data, plaintext)

        # Decrypt with wrong mode should fail
        with self.assertRaises(Exception):
            self.cipher.decrypt_record(ciphertext, key, salt, nonce, "secret", password_role)

        # Decrypt with wrong password_role should fail
        with self.assertRaises(Exception):
            self.cipher.decrypt_record(ciphertext, key, salt, nonce, mode, "purge")


if __name__ == "__main__":
    unittest.main()