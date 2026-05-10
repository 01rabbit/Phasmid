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

    def test_luks_probe_script_exists_and_has_required_checks(self):
        script = ROOT / "scripts" / "pi_zero2w" / "run_luks_probe.sh"
        self.assertTrue(script.exists())
        text = script.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("cryptsetup benchmark", text)
        self.assertIn("luksFormat", text)
        self.assertIn("luksOpen", text)
        self.assertIn("luks_field_test.json", text)
        self.assertIn("PHASMID_LUKS_CALIBRATION_SET", text)

    def test_remote_perf_invokes_luks_probe_phase(self):
        script = ROOT / "scripts" / "pi_zero2w" / "run_remote_perf.sh"
        text = script.read_text(encoding="utf-8")
        self.assertIn("Phase J: LUKS calibration probe", text)
        self.assertIn("run_luks_probe.sh", text)
        self.assertIn("phase_ok \"luks\"", text)

    def test_luks_eval_module_and_profile_exist(self):
        eval_script = ROOT / "scripts" / "pi_zero2w" / "luks_eval.py"
        profile = ROOT / "profiles" / "pi-zero2w.json"
        self.assertTrue(eval_script.exists())
        self.assertTrue(profile.exists())
        eval_text = eval_script.read_text(encoding="utf-8")
        self.assertIn("PASS_WITH_CONSTRAINTS", eval_text)
        self.assertIn("aes_acceleration_status", eval_text)

    def test_pi_detection_logic_is_present_in_bootstrap(self):
        text = (ROOT / "scripts" / "bootstrap_pi.sh").read_text(encoding="utf-8")
        self.assertIn("is_raspberry_pi()", text)
        self.assertIn("PHASMID_ALLOW_NON_PI", text)


if __name__ == "__main__":
    unittest.main()
