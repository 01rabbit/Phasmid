import unittest
import os
import tempfile
from src.phantasm.record_cypher import RecordCipher


class TestRecordCipher(unittest.TestCase):
    def setUp(self):
        self.container_size = 1024
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.cipher = RecordCipher(self.temp_file.name, self.container_size)

    def tearDown(self):
        os.unlink(self.temp_file.name)

    def test_encrypt_decrypt_roundtrip(self):
        """Test basic encrypt/decrypt roundtrip"""
        key = os.urandom(32)
        plaintext = b"test data"
        mode = "dummy"
        password_role = "open"

        salt, nonce, ciphertext = self.cipher.encrypt_record(plaintext, key, mode, password_role)
        decrypted, filename, metadata = self.cipher.decrypt_record(ciphertext, key, salt, nonce, mode, password_role)

        self.assertEqual(decrypted, plaintext)
        self.assertEqual(filename, "payload.bin")
        self.assertIsInstance(metadata, dict)

    def test_encrypt_decrypt_with_metadata(self):
        """Test encrypt/decrypt with filename"""
        key = os.urandom(32)
        plaintext = b"test data"
        filename = "test.txt"
        mode = "secret"
        password_role = "open"

        salt, nonce, ciphertext = self.cipher.encrypt_record(plaintext, key, mode, password_role, filename)
        decrypted, dec_filename, dec_metadata = self.cipher.decrypt_record(ciphertext, key, salt, nonce, mode, password_role)

        self.assertEqual(decrypted, plaintext)
        self.assertEqual(dec_filename, filename)
        self.assertEqual(dec_metadata["payload_len"], len(plaintext))

    def test_decrypt_wrong_key(self):
        """Test that decrypting with wrong key fails"""
        key = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"test data"
        mode = "dummy"
        password_role = "open"

        salt, nonce, ciphertext = self.cipher.encrypt_record(plaintext, key, mode, password_role)

        with self.assertRaises(Exception):
            self.cipher.decrypt_record(ciphertext, key2, salt, nonce, mode, password_role)

    def test_decrypt_wrong_password_role(self):
        """Test that decrypting with wrong password_role fails"""
        key = os.urandom(32)
        plaintext = b"test data"
        mode = "dummy"
        password_role = "open"

        salt, nonce, ciphertext = self.cipher.encrypt_record(plaintext, key, mode, password_role)

        # Decrypt with wrong password_role should fail
        with self.assertRaises(Exception):
            self.cipher.decrypt_record(ciphertext, key, salt, nonce, mode, "purge")


if __name__ == "__main__":
    unittest.main()