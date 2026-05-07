import contextlib
import io
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import cli


class CLITests(unittest.TestCase):
    def test_entry_labels_are_neutral(self):
        self.assertEqual(
            cli.display_mode_label(cli.gate.MODES[0]), "selected local entry"
        )
        self.assertEqual(
            cli.display_mode_label(cli.gate.MODES[1]), "selected local entry"
        )
        self.assertEqual(cli.display_mode_label("invalid"), "local entry")

    def test_resolve_mode(self):
        self.assertEqual(cli.resolve_mode("a"), cli.gate.MODES[0])
        self.assertEqual(cli.resolve_mode("b"), cli.gate.MODES[1])
        with self.assertRaises(ValueError):
            cli.resolve_mode("c")

    def test_show_loading(self):
        with unittest.mock.patch("time.sleep"):
            cli.show_loading("test", duration=0.1)

    def test_wait_for_camera_frame(self):
        with unittest.mock.patch("time.sleep"):
            # Case 1: Frame already exists
            with unittest.mock.patch.object(cli.gate, "lock"):
                cli.gate.latest_frame = object()
                self.assertTrue(cli._wait_for_camera_frame(timeout=0.1))

            # Case 2: Timeout
            cli.gate.latest_frame = None
            self.assertFalse(cli._wait_for_camera_frame(timeout=0.1))

    def test_wait_for_reference_match(self):
        with unittest.mock.patch("time.sleep"):
            # Case 1: Match already exists
            cli.gate.last_match_mode = "dummy"
            self.assertTrue(cli._wait_for_reference_match(timeout=0.1))
            self.assertTrue(
                cli._wait_for_reference_match(timeout=0.1, expected_mode="dummy")
            )
            self.assertFalse(
                cli._wait_for_reference_match(timeout=0.1, expected_mode="secret")
            )

            # Case 2: Timeout
            cli.gate.last_match_mode = "none"
            self.assertFalse(cli._wait_for_reference_match(timeout=0.1))

    def test_local_state_confirmation_language_is_neutral(self):
        output = io.StringIO()
        with (
            unittest.mock.patch.object(
                cli, "purge_confirmation_required", return_value=True
            ),
            unittest.mock.patch("builtins.input", return_value=""),
            contextlib.redirect_stdout(output),
        ):
            self.assertFalse(cli._confirm_purge_other_mode(cli.gate.MODES[0]))
        self.assertNotRegex(
            output.getvalue(),
            re.compile(r"profile|dummy|secret|decoy|truth|fake|real", re.I),
        )

    def test_object_registration_output_is_neutral(self):
        output = io.StringIO()
        with (
            unittest.mock.patch("builtins.input", return_value=""),
            unittest.mock.patch.object(
                cli.gate, "capture_reference", return_value=(True, "ok")
            ),
            unittest.mock.patch.object(
                cli, "_wait_for_reference_match", return_value=True
            ),
            contextlib.redirect_stdout(output),
        ):
            success, message = cli._register_reference_key(cli.gate.MODES[0])

        self.assertTrue(success)
        self.assertEqual(message, "Object access cue registered.")
        self.assertNotRegex(
            output.getvalue(),
            re.compile(
                r"profile|Entry A|Entry B|image key|registered image keys|Physical key|"
                r"other profile|other mode|DELETE Entry|TACTICAL|ARMED|Master Key|Biometric",
                re.I,
            ),
        )

    def test_cli_source_does_not_include_retired_user_visible_phrases(self):
        with open(cli.__file__, "r", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("Entry A", source)
        self.assertNotIn("Entry B", source)
        self.assertNotIn("AMBIGUOUS KEY", source)
        self.assertNotIn("KEY NOT FOUND", source)
        self.assertNotIn("Performing Argon2id-based key derivation", source)

    def test_store_password_prompt_rejects_short_values(self):
        prompts = iter(["short", "another-short"])

        with unittest.mock.patch(
            "getpass.getpass", side_effect=lambda _: next(prompts)
        ):
            with self.assertRaises(ValueError) as ctx:
                cli._prompt_store_passwords()

        self.assertIn("at least", str(ctx.exception))

    def test_cli_retrieve_respects_attempt_lockout(self):
        output = io.StringIO()

        class LockedLimiter:
            def check(self, _scope):
                return type("Decision", (), {"allowed": False})()

        with (
            unittest.mock.patch.object(sys, "argv", ["phasmid", "retrieve"]),
            unittest.mock.patch.object(
                cli, "_wait_for_camera_frame", return_value=True
            ),
            unittest.mock.patch.object(cli.gate, "start"),
            unittest.mock.patch.object(cli.gate, "close"),
            unittest.mock.patch.object(cli.EmergencyDaemon, "start"),
            unittest.mock.patch.object(cli.EmergencyDaemon, "stop"),
            unittest.mock.patch.object(
                cli, "FileAttemptLimiter", return_value=LockedLimiter()
            ),
            contextlib.redirect_stdout(output),
        ):
            cli.main()

        self.assertIn("Access temporarily unavailable", output.getvalue())

    def test_startup_check_failure_is_neutral(self):
        output = io.StringIO()

        with unittest.mock.patch.object(
            cli, "ensure_crypto_self_tests", side_effect=cli.CryptoSelfTestError
        ):
            with contextlib.redirect_stdout(output):
                self.assertFalse(cli._run_startup_checks())

        self.assertIn("Startup check failed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
