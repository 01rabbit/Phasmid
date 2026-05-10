from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.services.doctor_service import run_doctor_checks


class DoctorM4Checks(unittest.TestCase):
    def test_doctor_includes_sh14_and_sh15_checks(self):
        result = run_doctor_checks()
        names = {check.name for check in result.checks}
        expected = {
            "Recent File Activity",
            "Vault Size Record",
            "Recent Documents Cache",
            "Thumbnail Cache",
            "System Journal",
            "Core Dumps",
            "Compressed Swap",
            "Shell History",
            "LUKS Mode",
            "LUKS cryptsetup",
            "Local container path",
            "Local container mount state",
            "LUKS key-store tmpfs",
            "Dummy Profile Size",
            "Dummy Profile File Count",
            "Dummy Profile Occupancy Ratio",
            "Dummy Profile Size Distribution",
            "Dummy Profile Plausibility",
        }
        self.assertTrue(expected.issubset(names))

    def test_dummy_profile_plausibility_warns_for_small_ratio(self):
        with tempfile.TemporaryDirectory() as td:
            dummy_dir = os.path.join(td, "dummy")
            os.makedirs(dummy_dir, exist_ok=True)
            with open(os.path.join(dummy_dir, "a.bin"), "wb") as handle:
                handle.write(b"a" * 64)
            container = os.path.join(td, "vault.bin")
            with open(container, "wb") as handle:
                handle.write(b"b" * (10 * 1024 * 1024))
            with mock.patch.dict(
                os.environ,
                {
                    "PHASMID_DUMMY_PROFILE_DIR": dummy_dir,
                    "PHASMID_DUMMY_CONTAINER_PATH": container,
                    "PHASMID_DUMMY_MIN_SIZE_MB": "1",
                    "PHASMID_DUMMY_MIN_FILE_COUNT": "2",
                    "PHASMID_DUMMY_OCCUPANCY_WARN": "0.10",
                },
                clear=False,
            ):
                result = run_doctor_checks()

        check = next(c for c in result.checks if c.name == "Dummy Profile Plausibility")
        self.assertEqual("WARN", check.level.value)

    def test_luks_checks_show_disabled_state(self):
        with mock.patch.dict(
            os.environ, {"PHASMID_LUKS_MODE": "disabled"}, clear=False
        ):
            result = run_doctor_checks()
        checks = {c.name: c for c in result.checks}
        self.assertIn("[DISABLED]", checks["LUKS Mode"].message)
        self.assertIn("[DISABLED]", checks["LUKS cryptsetup"].message)
        self.assertIn("[DISABLED]", checks["Local container path"].message)
        self.assertIn("[DISABLED]", checks["Local container mount state"].message)
        self.assertIn("[DISABLED]", checks["LUKS key-store tmpfs"].message)

    def test_shell_history_warns_when_histfile_contains_phasmid_usage(self):
        with mock.patch.dict(
            os.environ,
            {
                "SHELL": "/bin/bash",
                "HISTFILE": "/tmp/fake_hist",
            },
            clear=False,
        ):
            fake_history = "python -m phasmid doctor --no-tui\n"
            with (
                mock.patch("pathlib.Path.exists", return_value=True),
                mock.patch("pathlib.Path.read_text", return_value=fake_history),
            ):
                result = run_doctor_checks()
        shell_check = next(
            check for check in result.checks if check.name == "Shell History"
        )
        self.assertIn("contains recent Phasmid-related commands", shell_check.message)


if __name__ == "__main__":
    unittest.main()
