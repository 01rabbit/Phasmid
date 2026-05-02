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
        self.assertIn("docs/REVIEW_VALIDATION_RECORD.md", readme)
        self.assertIn("docs/SOLUTION_READINESS_PLAN.md", readme)
        self.assertIn("docs/OPERATIONS.md", readme)
        self.assertIn("docs/RESTRICTED_ACTIONS.md", readme)
        self.assertIn("docs/STATE_RECOVERY.md", readme)
        self.assertIn("authoritative appliance deployment guide", readme)
        self.assertIn("metadata risk check", readme)

    def test_readme_addresses_reviewer_and_use_boundaries(self):
        readme = read_text("README.md")
        self.assertIn("Reviewer Notes and Known Limits", readme)
        self.assertIn("Safe Use Boundary", readme)
        self.assertIn("Government and Organizational Use Boundary", readme)
        self.assertIn("When to Use Phantasm", readme)
        self.assertIn("Test Command", readme)
        self.assertIn("not approved classified-data handling infrastructure", readme)
        self.assertIn("Field Mode is not a security boundary", readme)
        self.assertIn("Metadata detection and reduction are best-effort", readme)
        self.assertIn("field-evaluation prototype", readme)
        self.assertIn("From Prototype to Solution", readme)
        self.assertIn("record validation results for each release", readme)

    def test_specification_defines_field_mode_and_metadata_routes(self):
        spec = read_text("docs/SPECIFICATION.md")
        self.assertIn("PHANTASM_FIELD_MODE=1", spec)
        self.assertIn("/metadata/check", spec)
        self.assertIn("/metadata/scrub", spec)
        self.assertIn("no disk", spec.lower())
        self.assertIn("neutral filename", spec.lower())
        self.assertIn("Capture-Visible Surface Rule", spec)
        self.assertIn("Stress-Use UX Principle", spec)
        self.assertIn("Field Mode is not a security boundary", spec)

    def test_threat_model_names_leakage_surfaces(self):
        threat = read_text("docs/THREAT_MODEL.md")
        self.assertIn("metadata", threat.lower())
        self.assertIn("Maintenance diagnostics", threat)
        self.assertIn("camera overlay", threat)
        self.assertIn("CLI output", threat)
        self.assertIn("systemd logs", threat)
        self.assertIn("Capture-visible surfaces include", threat)
        self.assertIn("Hidden routes are not access control", threat)

    def test_source_safe_workflow_addresses_mixing_and_labels(self):
        doc = read_text("docs/SOURCE_SAFE_WORKFLOW.md")
        self.assertIn("Do not store source identity", doc)
        self.assertIn("Avoid local labels that reveal", doc)
        self.assertIn("Before travel", doc)

    def test_field_test_procedure_addresses_field_use_limits(self):
        doc = read_text("docs/FIELD_TEST_PROCEDURE.md")
        self.assertIn("Physical shock resistance and tamper-resistant casing are out of scope", doc)
        self.assertIn("Test sudden power loss during Retrieve", doc)
        self.assertIn("Review the systemd journal after each power-loss case", doc)

    def test_review_validation_record_exists(self):
        record = read_text("docs/REVIEW_VALIDATION_RECORD.md")
        self.assertIn("Review Validation Record", record)
        self.assertRegex(record, r"\d+ tests passed")
        self.assertIn("tests/scenarios/restricted_flows.json", record)
        self.assertIn("Target-hardware validation result", record)
        self.assertIn("Not field-proven", record)
        self.assertIn("Solution Readiness", record)

    def test_solution_readiness_plan_bounds_solution_claims(self):
        plan = read_text("docs/SOLUTION_READINESS_PLAN.md")
        self.assertIn("Solution Readiness Plan", plan)
        self.assertIn("readiness gates", plan)
        self.assertIn("target-hardware validation", plan)
        self.assertIn("README claims match the validation record", plan)

    def test_rpi_appliance_doc_is_authoritative(self):
        summary = read_text("docs/RPI_ZERO_DEPLOYMENT.md")
        appliance = read_text("docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md")
        self.assertIn("authoritative appliance deployment guide", summary)
        self.assertIn("authoritative Raspberry Pi Zero 2 W appliance deployment guide", appliance)
        self.assertIn("optional LUKS2 storage-layer procedure", summary)
        self.assertIn("Optional LUKS Storage Layer", appliance)


if __name__ == "__main__":
    unittest.main()
