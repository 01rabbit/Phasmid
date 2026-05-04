import os
import tempfile
import unittest

from src.phantasm.container_layout import ContainerLayout


class TestContainerLayout(unittest.TestCase):
    def setUp(self):
        self.container_path = tempfile.mktemp()
        self.container_size = 10 * 1024 * 1024  # 10MB
        self.layout = ContainerLayout(self.container_path, self.container_size)

    def tearDown(self):
        if os.path.exists(self.container_path):
            os.unlink(self.container_path)

    def test_get_mode_span_dummy(self):
        """Test get_mode_span for dummy mode"""
        start, length = self.layout.get_mode_span("dummy")
        self.assertEqual(start, 0)
        self.assertEqual(length, self.container_size // 2)

    def test_get_mode_span_secret(self):
        """Test get_mode_span for secret mode"""
        start, length = self.layout.get_mode_span("secret")
        self.assertEqual(start, self.container_size // 2)
        self.assertEqual(length, self.container_size - (self.container_size // 2))

    def test_get_mode_span_invalid(self):
        """Test get_mode_span raises ValueError for invalid mode"""
        with self.assertRaises(ValueError):
            self.layout.get_mode_span("invalid")

    def test_get_slot_span_open_dummy(self):
        """Test get_slot_span for open role in dummy mode"""
        start, length = self.layout.get_slot_span("dummy", "open")
        expected_start = 0
        expected_length = (self.container_size // 2) // 2
        self.assertEqual(start, expected_start)
        self.assertEqual(length, expected_length)

    def test_get_slot_span_purge_secret(self):
        """Test get_slot_span for purge role in secret mode"""
        start, length = self.layout.get_slot_span("secret", "purge")
        mode_start = self.container_size // 2
        mode_length = self.container_size - mode_start
        expected_start = mode_start + (mode_length // 2)
        expected_length = mode_length - (mode_length // 2)
        self.assertEqual(start, expected_start)
        self.assertEqual(length, expected_length)

    def test_get_slot_span_invalid_role(self):
        """Test get_slot_span raises ValueError for invalid role"""
        with self.assertRaises(ValueError):
            self.layout.get_slot_span("dummy", "invalid")

    def test_get_plaintext_capacity(self):
        """Test get_plaintext_capacity calculation"""
        capacity = self.layout.get_plaintext_capacity("dummy", "open")
        RECORD_OVERHEAD = 16 + 12 + 16  # SALT + NONCE + TAG
        expected_capacity = ((self.container_size // 2) // 2) - RECORD_OVERHEAD
        self.assertEqual(capacity, expected_capacity)

    def test_format_container_creates_file(self):
        """Test format_container creates the container file"""
        self.assertFalse(os.path.exists(self.container_path))
        self.layout.format_container()
        self.assertTrue(os.path.exists(self.container_path))
        with open(self.container_path, "rb") as f:
            data = f.read()
            self.assertEqual(len(data), self.container_size)
            # Should be random, not all zeros
            self.assertNotEqual(data, b"\x00" * self.container_size)

    def test_silent_brick_overwrites_container(self):
        """Test silent_brick overwrites the entire container"""
        # Create container
        self.layout.format_container()
        with open(self.container_path, "rb") as f:
            original_data = f.read()

        # Brick it
        self.layout.silent_brick()
        with open(self.container_path, "rb") as f:
            bricked_data = f.read()

        self.assertEqual(len(bricked_data), self.container_size)
        self.assertNotEqual(original_data, bricked_data)

    def test_purge_mode_dummy(self):
        """Test purge_mode overwrites dummy mode"""
        self.layout.format_container()
        with open(self.container_path, "rb") as f:
            original_data = f.read()

        self.layout.purge_mode("dummy")
        with open(self.container_path, "rb") as f:
            purged_data = f.read()

        # First half should be changed
        self.assertNotEqual(
            original_data[: self.container_size // 2],
            purged_data[: self.container_size // 2],
        )
        # Second half should be unchanged
        self.assertEqual(
            original_data[self.container_size // 2 :],
            purged_data[self.container_size // 2 :],
        )

    def test_purge_mode_secret(self):
        """Test purge_mode overwrites secret mode"""
        self.layout.format_container()
        with open(self.container_path, "rb") as f:
            original_data = f.read()

        self.layout.purge_mode("secret")
        with open(self.container_path, "rb") as f:
            purged_data = f.read()

        # First half should be unchanged
        self.assertEqual(
            original_data[: self.container_size // 2],
            purged_data[: self.container_size // 2],
        )
        # Second half should be changed
        self.assertNotEqual(
            original_data[self.container_size // 2 :],
            purged_data[self.container_size // 2 :],
        )

    def test_purge_other_mode_from_dummy(self):
        """Test purge_other_mode purges secret when dummy was accessed"""
        self.layout.format_container()
        with open(self.container_path, "rb") as f:
            original_data = f.read()

        self.layout.purge_other_mode("dummy")
        with open(self.container_path, "rb") as f:
            purged_data = f.read()

        # Same as purging secret mode
        self.assertEqual(
            original_data[: self.container_size // 2],
            purged_data[: self.container_size // 2],
        )
        self.assertNotEqual(
            original_data[self.container_size // 2 :],
            purged_data[self.container_size // 2 :],
        )

    def test_purge_other_mode_from_secret(self):
        """Test purge_other_mode purges dummy when secret was accessed"""
        self.layout.format_container()
        with open(self.container_path, "rb") as f:
            original_data = f.read()

        self.layout.purge_other_mode("secret")
        with open(self.container_path, "rb") as f:
            purged_data = f.read()

        # Same as purging dummy mode
        self.assertNotEqual(
            original_data[: self.container_size // 2],
            purged_data[: self.container_size // 2],
        )
        self.assertEqual(
            original_data[self.container_size // 2 :],
            purged_data[self.container_size // 2 :],
        )

    def test_purge_other_mode_invalid(self):
        """Test purge_other_mode raises ValueError for invalid mode"""
        with self.assertRaises(ValueError):
            self.layout.purge_other_mode("invalid")

    def test_require_container_missing_file(self):
        """Test _require_container raises FileNotFoundError for missing file"""
        with self.assertRaises(FileNotFoundError):
            self.layout._require_container()


if __name__ == "__main__":
    unittest.main()
