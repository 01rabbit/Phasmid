import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm import cli
from phantasm.config import AUDIT_LOG_NAME, STATE_BLOB_NAME, STATE_KEY_NAME, VAULT_KEY_NAME
from phantasm.operations import (
    export_redacted_log,
    verify_audit_log,
    verify_state,
)


class LocalOperationTests(unittest.TestCase):
    def test_verify_state_reports_missing_state_without_paths(self):
        missing = os.path.join(tempfile.mkdtemp(), "missing")
        report = verify_state(
            base_dir=missing,
            vault_path=os.path.join(missing, "vault.bin"),
        )

        self.assertEqual(report["status"], "attention")
        rendered = json.dumps(report)
        self.assertNotIn(missing, rendered)
        self.assertIn("local state is not initialized", rendered)

    def test_verify_state_reports_ready_state(self):
        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, ".state")
        os.mkdir(state_path, 0o700)
        for name in (STATE_BLOB_NAME, STATE_KEY_NAME, VAULT_KEY_NAME):
            path = os.path.join(state_path, name)
            with open(path, "wb") as handle:
                handle.write(b"x")
            os.chmod(path, 0o600)
        vault_path = os.path.join(tmpdir, "vault.bin")
        with open(vault_path, "wb") as handle:
            handle.write(b"vault")

        report = verify_state(base_dir=state_path, vault_path=vault_path)

        self.assertEqual(report["status"], "ready")

    def test_verify_audit_log_accepts_minimal_schema(self):
        tmpdir = tempfile.mkdtemp()
        audit_path = os.path.join(tmpdir, AUDIT_LOG_NAME)
        with open(audit_path, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps({"ts": 1, "event": "startup", "source": "test"})
                + "\n"
            )

        report = verify_audit_log(audit_path)

        self.assertEqual(report["status"], "ready")
        rendered = json.dumps(report)
        self.assertIn("audit records parse as JSON lines", rendered)
        self.assertIn("audit chain data is not recorded", rendered)

    def test_verify_audit_log_reports_parse_error(self):
        tmpdir = tempfile.mkdtemp()
        audit_path = os.path.join(tmpdir, AUDIT_LOG_NAME)
        with open(audit_path, "w", encoding="utf-8") as handle:
            handle.write("{broken\n")

        report = verify_audit_log(audit_path)

        self.assertEqual(report["status"], "attention")

    def test_redacted_log_export_omits_unapproved_fields(self):
        tmpdir = tempfile.mkdtemp()
        audit_path = os.path.join(tmpdir, AUDIT_LOG_NAME)
        output_path = os.path.join(tmpdir, "review.jsonl")
        with open(audit_path, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "ts": 1,
                        "event": "payload_stored",
                        "filename_hash": "abc123",
                        "source": "test",
                    }
                )
                + "\n"
            )

        report = export_redacted_log(output_path, input_path=audit_path)

        self.assertEqual(report["status"], "ready")
        with open(output_path, "r", encoding="utf-8") as handle:
            exported = json.loads(handle.readline())
        self.assertNotIn("filename_hash", exported)
        self.assertTrue(exported["details_redacted"])

    def test_cli_operation_report_is_neutral_and_pathless(self):
        report = {
            "name": "doctor",
            "status": "ready",
            "checks": [
                {
                    "name": "state",
                    "status": "ready",
                    "message": "local state check completed",
                }
            ],
        }
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            cli._print_operation_report(report)

        rendered = output.getvalue()
        self.assertIn("doctor: ready", rendered)
        self.assertNotRegex(rendered, r"dummy|secret|profile|decoy|truth|fake|real")

    def test_cli_verify_state_command_runs_without_starting_panic_monitor(self):
        tmpdir = tempfile.mkdtemp()
        output = io.StringIO()

        with mock.patch.object(sys, "argv", ["phantasm", "verify-state"]), \
             mock.patch.dict(os.environ, {"PHANTASM_STATE_DIR": tmpdir}), \
             mock.patch.object(cli.EmergencyDaemon, "start") as start, \
             contextlib.redirect_stdout(output):
            cli.main()

        start.assert_not_called()
        self.assertIn("verify-state:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
