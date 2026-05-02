import json
import os
import stat
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
import sys

sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.state_store import (
    STATE_INDEX_NAME,
    LocalStateStore,
    StatePhase,
    StateRecord,
    StateStoreError,
)


class LocalStateStoreTests(unittest.TestCase):
    def test_missing_record_returns_uninitialized(self):
        store = LocalStateStore(tempfile.mkdtemp())

        record = store.read_record()

        self.assertEqual(record.phase, StatePhase.UNINITIALIZED)
        self.assertEqual(record.category, "local_state")

    def test_malformed_record_returns_corrupt(self):
        tmpdir = tempfile.mkdtemp()
        with open(os.path.join(tmpdir, STATE_INDEX_NAME), "w", encoding="utf-8") as handle:
            handle.write("{broken\n")
        store = LocalStateStore(tmpdir)

        record = store.read_record()

        self.assertEqual(record.phase, StatePhase.CORRUPT)

    def test_write_record_is_atomic_and_restricts_permissions(self):
        tmpdir = tempfile.mkdtemp()
        store = LocalStateStore(tmpdir)

        store.write_record(
            StateRecord(
                category="local_state",
                phase=StatePhase.INITIALIZED,
                attributes={"source": "test"},
            )
        )

        path = os.path.join(tmpdir, STATE_INDEX_NAME)
        mode = stat.S_IMODE(os.stat(path).st_mode)
        self.assertEqual(mode, 0o600)
        self.assertEqual(store.read_record().phase, StatePhase.INITIALIZED)

    def test_rejects_invalid_transition(self):
        tmpdir = tempfile.mkdtemp()
        store = LocalStateStore(tmpdir)
        store.write_record(
            StateRecord(category="local_state", phase=StatePhase.INITIALIZED)
        )
        store.write_record(StateRecord(category="local_state", phase=StatePhase.READY))

        with self.assertRaises(StateStoreError):
            store.write_record(
                StateRecord(category="local_state", phase=StatePhase.ENROLLED)
            )

    def test_rejects_path_traversal_names(self):
        store = LocalStateStore(tempfile.mkdtemp())

        with self.assertRaises(StateStoreError):
            store.write_json_atomic("../outside.json", {"ok": True})

    def test_inspect_layout_reports_insecure_state_file(self):
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "access.bin")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"ok": True}, handle)
        os.chmod(path, 0o644)
        store = LocalStateStore(tmpdir)

        layout = store.inspect_layout(("access.bin",))

        self.assertTrue(layout["root_present"])
        self.assertFalse(layout["files_secure"])


if __name__ == "__main__":
    unittest.main()
