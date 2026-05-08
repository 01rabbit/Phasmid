from __future__ import annotations

import unittest

from phasmid.dummy_profile_eval import evaluate_dummy_profile


class DummyProfileEvalTests(unittest.TestCase):
    def test_warns_on_small_footprint(self):
        with self.subTest("small footprint"):
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as td:
                base = Path(td)
                dummy_dir = base / "dummy"
                dummy_dir.mkdir()
                (dummy_dir / "a.txt").write_bytes(b"a" * 128)

                container = base / "vault.bin"
                container.write_bytes(b"x" * (10 * 1024 * 1024))

                result = evaluate_dummy_profile(
                    dummy_profile_dir=dummy_dir,
                    container_path=container,
                    min_size_mb=1,
                    min_file_count=3,
                    occupancy_warn_threshold=0.10,
                )

                self.assertEqual(result.file_count, 1)
                self.assertEqual(result.container_size_bytes, 10 * 1024 * 1024)
                self.assertLess(result.occupancy_ratio, 0.10)
                self.assertTrue(result.warnings)

    def test_ok_when_thresholds_met(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dummy_dir = base / "dummy"
            dummy_dir.mkdir()
            for i in range(4):
                (dummy_dir / f"f{i}.bin").write_bytes(b"a" * (300 * 1024))

            container = base / "vault.bin"
            container.write_bytes(b"x" * (8 * 1024 * 1024))

            result = evaluate_dummy_profile(
                dummy_profile_dir=dummy_dir,
                container_path=container,
                min_size_mb=1,
                min_file_count=4,
                occupancy_warn_threshold=0.10,
            )

            self.assertEqual(result.file_count, 4)
            self.assertGreaterEqual(result.dummy_size_bytes, 1024 * 1024)
            self.assertGreaterEqual(result.occupancy_ratio, 0.10)
            self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
