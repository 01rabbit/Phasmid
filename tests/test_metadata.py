import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.metadata import metadata_risk_report, scrub_metadata


class MetadataTests(unittest.TestCase):
    def test_text_path_and_author_metadata_are_reported(self):
        data = b"author: Alice\nsource path: /Users/alice/interview.txt\n"
        report = metadata_risk_report("interview.txt", data)
        self.assertTrue(report["risk"])
        self.assertIn("local path leakage", report["findings"])
        self.assertIn("author or modification metadata", report["findings"])
        self.assertTrue(report["scrub_supported"])

    def test_metadata_scrub_returns_neutral_filename_without_overwriting_original(self):
        data = b"author: Alice\npath=/home/alice/source.txt\nbody\n"
        result = scrub_metadata("revealing-name.txt", data)
        self.assertTrue(result["success"])
        self.assertEqual(result["filename"], "metadata_reduced_payload.txt")
        self.assertNotEqual(result["data"], data)
        self.assertIn("best-effort", result["limitation"].lower())

    def test_unsupported_scrub_fails_safely(self):
        result = scrub_metadata("image.jpg", b"\xff\xd8Exif\x00\x00GPS")
        self.assertFalse(result["success"])
        self.assertEqual(result["data"], b"")
        self.assertIn("not supported", result["message"])


if __name__ == "__main__":
    unittest.main()
