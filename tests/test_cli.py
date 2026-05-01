import contextlib
import io
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm import cli


class CLITests(unittest.TestCase):
    def test_local_state_confirmation_language_is_neutral(self):
        output = io.StringIO()
        with unittest.mock.patch.object(cli, "purge_confirmation_required", return_value=True), \
             unittest.mock.patch("builtins.input", return_value=""), \
             contextlib.redirect_stdout(output):
            self.assertFalse(cli._confirm_purge_other_mode(cli.gate.MODES[0]))
        self.assertNotRegex(output.getvalue(), re.compile(r"profile|dummy|secret|decoy|truth|fake|real", re.I))

    def test_face_reset_confirmation_requires_exact_phrase(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(cli._confirm_face_lock_reset(lambda _: cli.FACE_RESET_CONFIRMATION))
            self.assertFalse(cli._confirm_face_lock_reset(lambda _: "RESET"))

    def test_face_reset_arms_web_enrollment(self):
        class FakeVault:
            def __init__(self):
                self.rotate_access_key = None

            def format_container(self, rotate_access_key=False):
                self.rotate_access_key = rotate_access_key

        vault = FakeVault()
        with unittest.mock.patch.object(cli.gate, "clear_references", return_value=(True, "objects cleared")), \
             unittest.mock.patch.object(cli.face_lock, "reset", return_value=(True, "face cleared")), \
             unittest.mock.patch.object(cli.face_lock, "arm_enrollment", return_value=(True, "enrollment armed")) as arm:
            success, object_message, face_message, enroll_message = cli._reset_face_lock_and_container(vault)

        self.assertTrue(success)
        self.assertTrue(vault.rotate_access_key)
        self.assertEqual(object_message, "objects cleared")
        self.assertEqual(face_message, "face cleared")
        self.assertEqual(enroll_message, "enrollment armed")
        arm.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
