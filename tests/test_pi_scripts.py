import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class PiScriptTests(unittest.TestCase):
    def test_bootstrap_script_exists_and_has_required_flags(self):
        script = ROOT / "scripts" / "bootstrap_pi.sh"
        self.assertTrue(script.exists())
        text = script.read_text(encoding="utf-8")
        self.assertIn("#!/usr/bin/env bash", text)
        self.assertIn("set -euo pipefail", text)
        self.assertIn("--system-site-packages", text)
        self.assertIn("python3-picamera2", text)
        self.assertIn("python3-libcamera", text)
        self.assertIn("python -m pip install -e .", text)

    def test_validation_script_exists_and_checks_required_stages(self):
        script = ROOT / "scripts" / "validate_pi_environment.sh"
        self.assertTrue(script.exists())
        text = script.read_text(encoding="utf-8")
        self.assertIn("#!/usr/bin/env bash", text)
        self.assertIn("set -euo pipefail", text)
        self.assertIn("Stage A: Python imports", text)
        self.assertIn("Stage B: Picamera2 frame capture", text)
        self.assertIn("Stage C: WebUI startup", text)
        self.assertIn("Stage D: /status validation", text)
        self.assertIn("Stage E: MJPEG validation", text)
        self.assertIn("Stage F: cleanup and camera release", text)
        self.assertIn("python -m uvicorn phasmid.web_server:app", text)
        self.assertIn("curl -fsS \"$FEED_URL\" --max-time 5", text)

    def test_pi_detection_logic_is_present_in_bootstrap(self):
        text = (ROOT / "scripts" / "bootstrap_pi.sh").read_text(encoding="utf-8")
        self.assertIn("is_raspberry_pi()", text)
        self.assertIn("PHASMID_ALLOW_NON_PI", text)


if __name__ == "__main__":
    unittest.main()
