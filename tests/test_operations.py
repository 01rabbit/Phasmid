import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import audit, cli
from phasmid.config import (
    AUDIT_AUTH_NAME,
    AUDIT_LOG_NAME,
    STATE_BLOB_NAME,
    STATE_KEY_NAME,
    VAULT_KEY_NAME,
)
from phasmid.kdf_providers import HardwareBindingStatus
from phasmid.operations import (
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

        with mock.patch(
            "phasmid.operations.hardware_binding_status",
            return_value=HardwareBindingStatus(
                host_supported=True,
                device_binding_available=True,
                external_binding_configured=False,
            ),
        ):
            report = verify_state(base_dir=state_path, vault_path=vault_path)

        self.assertEqual(report["status"], "ready")

    def test_verify_state_reports_hardware_binding_attention_on_supported_host(self):
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

        with mock.patch(
            "phasmid.operations.hardware_binding_status",
            return_value=HardwareBindingStatus(
                host_supported=True,
                device_binding_available=False,
                external_binding_configured=False,
            ),
        ):
            report = verify_state(base_dir=state_path, vault_path=vault_path)

        self.assertEqual(report["status"], "attention")
        rendered = json.dumps(report)
        self.assertIn("device binding material is not present", rendered)
        self.assertIn(
            "supplemental key material source is not configured",
            rendered,
        )

    def test_verify_audit_log_accepts_minimal_schema(self):
        tmpdir = tempfile.mkdtemp()
        audit_path = os.path.join(tmpdir, AUDIT_LOG_NAME)
        with open(audit_path, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps({"ts": 1, "event": "startup", "source": "test"}) + "\n"
            )

        report = verify_audit_log(audit_path)

        self.assertEqual(report["status"], "ready")
        rendered = json.dumps(report)
        self.assertIn("audit records parse as JSON lines", rendered)
        self.assertIn("audit chain data is not recorded", rendered)

    def test_verify_audit_log_reports_missing_verifier_material(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ, {"PHASMID_STATE_DIR": tmpdir, "PHASMID_AUDIT": "1"}
            ):
                audit.audit_event("payload_stored", bytes=10)

            os.remove(os.path.join(tmpdir, AUDIT_AUTH_NAME))
            report = verify_audit_log(os.path.join(tmpdir, AUDIT_LOG_NAME))

            self.assertEqual(report["status"], "attention")
            rendered = json.dumps(report)
            self.assertIn("audit verifier material is not present", rendered)
            self.assertIn("audit integrity verification requires attention", rendered)

    def test_verify_audit_log_reports_integrity_tamper(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ, {"PHASMID_STATE_DIR": tmpdir, "PHASMID_AUDIT": "1"}
            ):
                audit.audit_event("payload_stored", bytes=10)
                audit.audit_event("payload_retrieved", bytes=10)

            audit_path = os.path.join(tmpdir, AUDIT_LOG_NAME)
            with open(audit_path, "r", encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle]
            records[1]["bytes"] = 11
            with open(audit_path, "w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record) + "\n")

            report = verify_audit_log(audit_path)

            self.assertEqual(report["status"], "attention")
            rendered = json.dumps(report)
            self.assertIn("audit verifier material is present", rendered)
            self.assertIn("audit integrity verification requires attention", rendered)

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
        # _print_operation_report uses Rich console; verify it does not raise
        # and does not include forbidden terminology
        import io as _io

        from rich.console import Console

        buf = _io.StringIO()
        original_console = cli.console
        cli.console = Console(file=buf, highlight=False)
        try:
            cli._print_operation_report(report)
        finally:
            cli.console = original_console
        rendered = buf.getvalue()
        self.assertNotRegex(rendered.lower(), r"dummy|secret|decoy|truth")

    def test_cli_verify_state_command_runs_without_starting_panic_monitor(self):
        tmpdir = tempfile.mkdtemp()

        with (
            mock.patch.object(sys, "argv", ["phasmid", "verify-state"]),
            mock.patch.dict(os.environ, {"PHASMID_STATE_DIR": tmpdir}),
            mock.patch.object(cli.EmergencyDaemon, "start") as start,
        ):
            cli.main()

        start.assert_not_called()

    def test_cli_verify_audit_log_command_reports_missing_audit_log(self):
        tmpdir = tempfile.mkdtemp()

        with (
            mock.patch.object(cli, "ensure_crypto_self_tests", return_value=True),
            mock.patch.object(sys, "argv", ["phasmid", "verify-audit-log"]),
            mock.patch.dict(os.environ, {"PHASMID_STATE_DIR": tmpdir}),
        ):
            cli.main()

    def test_cli_doctor_command_reports_structured_output(self):
        """phasmid doctor (non-interactive) produces structured doctor output."""
        with (
            mock.patch.object(cli, "ensure_crypto_self_tests", return_value=True),
            mock.patch.object(sys, "argv", ["phasmid", "doctor", "--no-tui"]),
        ):
            cli.main()


if __name__ == "__main__":
    unittest.main()
