import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))


def read_text(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as handle:
        return handle.read()


class DocsAndTemplateTests(unittest.TestCase):
    def test_store_template_exposes_metadata_workflow_without_overclaiming(self):
        store = read_text("src/phantasm/templates/store.html")
        self.assertIn("Data minimization", store)
        self.assertIn("Metadata Risk", store)
        self.assertIn("Check metadata risk", store)
        self.assertIn("Download metadata-reduced copy", store)
        self.assertIn("Metadata detection and reduction are best-effort.", store)
        self.assertNotIn("complete metadata removal", store.lower())

    def test_readme_links_field_operational_docs(self):
        readme = read_text("README.md")
        self.assertIn("PHANTASM_FIELD_MODE=1", readme)
        self.assertIn("docs/SOURCE_SAFE_WORKFLOW.md", readme)
        self.assertIn("docs/SEIZURE_REVIEW_CHECKLIST.md", readme)
        self.assertIn("docs/FIELD_TEST_PROCEDURE.md", readme)
        self.assertIn("metadata risk check", readme)

    def test_specification_defines_field_mode_and_metadata_routes(self):
        spec = read_text("docs/SPECIFICATION.md")
        self.assertIn("PHANTASM_FIELD_MODE=1", spec)
        self.assertIn("/metadata/check", spec)
        self.assertIn("/metadata/scrub", spec)
        self.assertIn("no disk", spec.lower())
        self.assertIn("neutral filename", spec.lower())

    def test_threat_model_names_leakage_surfaces(self):
        threat = read_text("docs/THREAT_MODEL.md")
        self.assertIn("metadata", threat.lower())
        self.assertIn("Maintenance diagnostics", threat)
        self.assertIn("camera overlay", threat)
        self.assertIn("CLI output", threat)
        self.assertIn("systemd logs", threat)


if __name__ == "__main__":
    unittest.main()
