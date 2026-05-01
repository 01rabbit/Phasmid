import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.emergency_daemon import EmergencyDaemon


class EmergencyDaemonTests(unittest.TestCase):
    def test_panic_trigger_requires_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            daemon = EmergencyDaemon(
                vault_path=os.path.join(tmp, "vault.bin"),
                state_dir=os.path.join(tmp, "state"),
            )

            with open(daemon.trigger_file, "w", encoding="utf-8") as handle:
                handle.write("wrong-token")
            self.assertFalse(daemon._authorized_trigger_present())
            self.assertFalse(os.path.exists(daemon.trigger_file))

            with open(daemon.trigger_file, "w", encoding="utf-8") as handle:
                handle.write(daemon.panic_token)
            self.assertTrue(daemon._authorized_trigger_present())


if __name__ == "__main__":
    unittest.main()
