import contextlib
import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm import cli


class CLITests(unittest.TestCase):
    def test_face_reset_confirmation_requires_exact_phrase(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(cli._confirm_face_lock_reset(lambda _: cli.FACE_RESET_CONFIRMATION))
            self.assertFalse(cli._confirm_face_lock_reset(lambda _: "RESET"))


if __name__ == "__main__":
    unittest.main()
