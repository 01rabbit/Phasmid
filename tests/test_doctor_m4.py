from __future__ import annotations

import os
import sys
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
        }
        self.assertTrue(expected.issubset(names))

    def test_luks_checks_show_disabled_state(self):
        with mock.patch.dict(os.environ, {"PHASMID_LUKS_MODE": "disabled"}, clear=False):
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
