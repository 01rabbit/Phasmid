import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import audit
from phasmid.config import AUDIT_LOG_NAME


class AuditTests(unittest.TestCase):
    def test_audit_hashes_filename_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ,
                {
                    "PHASMID_STATE_DIR": tmp,
                    "PHASMID_AUDIT": "1",
                    "PHASMID_AUDIT_FILENAMES": "hash",
                },
            ):
                audit.audit_event(
                    "payload_stored",
                    filename="../classified-plan.txt",
                    bytes=10,
                    profile="Profile A",
                )

            with open(
                os.path.join(tmp, AUDIT_LOG_NAME), "r", encoding="utf-8"
            ) as handle:
                record = json.loads(handle.readline())

            self.assertEqual(record["event"], "payload_stored")
            self.assertEqual(record["version"], "2.0")
            self.assertEqual(record["sequence"], 1)
            self.assertIn("previous_hash", record)
            self.assertIn("entry_hash", record)
            self.assertIn("hmac_sha256", record)
            self.assertEqual(record["bytes"], 10)
            self.assertEqual(record["entry"], "local_entry")
            self.assertNotIn("profile", record)
            self.assertTrue(record["filename_present"])
            self.assertIn("filename_hash", record)
            self.assertNotIn("filename", record)
            self.assertNotIn("classified-plan.txt", json.dumps(record))

    def test_audit_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"PHASMID_STATE_DIR": tmp}, clear=True):
                audit.audit_event("payload_stored", filename="payload-name.txt")

            self.assertFalse(os.path.exists(os.path.join(tmp, AUDIT_LOG_NAME)))

    def test_audit_omits_filename_hash_by_default_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ, {"PHASMID_STATE_DIR": tmp, "PHASMID_AUDIT": "1"}
            ):
                audit.audit_event("payload_stored", filename="payload-name.txt")

            with open(
                os.path.join(tmp, AUDIT_LOG_NAME), "r", encoding="utf-8"
            ) as handle:
                record = json.loads(handle.readline())

            self.assertTrue(record["filename_present"])
            self.assertNotIn("filename_hash", record)
            self.assertNotIn("payload-name.txt", json.dumps(record))

    def test_audit_integrity_detects_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ, {"PHASMID_STATE_DIR": tmp, "PHASMID_AUDIT": "1"}
            ):
                audit.audit_event("payload_stored", bytes=10)
                audit.audit_event("payload_retrieved", bytes=10)
                ok, errors = audit.verify_log_integrity()
                self.assertTrue(ok, errors)

                path = os.path.join(tmp, AUDIT_LOG_NAME)
                with open(path, "r", encoding="utf-8") as handle:
                    records = [json.loads(line) for line in handle]
                records[0]["event"] = "modified"
                with open(path, "w", encoding="utf-8") as handle:
                    for record in records:
                        handle.write(json.dumps(record) + "\n")

                ok, errors = audit.verify_log_integrity()
                self.assertFalse(ok)
                self.assertTrue(any("event hash rejected" in item for item in errors))

    def test_audit_integrity_detects_deleted_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ, {"PHASMID_STATE_DIR": tmp, "PHASMID_AUDIT": "1"}
            ):
                audit.audit_event("payload_stored", bytes=10)
                audit.audit_event("payload_retrieved", bytes=10)

                path = os.path.join(tmp, AUDIT_LOG_NAME)
                with open(path, "r", encoding="utf-8") as handle:
                    records = handle.readlines()
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(records[1])

                ok, errors = audit.verify_log_integrity()
                self.assertFalse(ok)
                self.assertTrue(any("sequence rejected" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
