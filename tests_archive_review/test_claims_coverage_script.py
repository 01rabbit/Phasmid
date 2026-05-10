from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_claims_coverage.py"


class ClaimsCoverageScriptTests(unittest.TestCase):
    def test_script_writes_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "claims_coverage.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--claims-file",
                    str(ROOT / "docs" / "CLAIMS.md"),
                    "--tests-dir",
                    str(ROOT / "tests"),
                    "--output",
                    str(output_path),
                    "--max-unverified",
                    "99",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr + proc.stdout)
            self.assertTrue(output_path.exists())
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("claims_total", data)
            self.assertIn("claims_unverified", data)

    def test_script_fails_when_threshold_is_too_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "claims_coverage.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--claims-file",
                    str(ROOT / "docs" / "CLAIMS.md"),
                    "--tests-dir",
                    str(ROOT / "tests"),
                    "--output",
                    str(output_path),
                    "--max-unverified",
                    "-1",
                ],
                check=False,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
            )
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
