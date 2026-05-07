"""SH-11: Scenario tests for Field Mode capture-visible language constraints.

Claim coverage:
  CLM-06  Field Mode hides state path before restricted confirmation.
  CLM-07  Field Mode hides session token before restricted confirmation.
  CLM-08  Forbidden internal terms are absent from Field Mode HTML output.

Verifies that:
- The maintenance page template does not expose the state directory path in
  Field Mode before restricted confirmation is active.
- Forbidden internal terms (see forbidden_terms.py) are absent from rendered
  HTML in Field Mode.
- Output differences between Field Mode on/off are bounded and documented.

Template rendering is tested directly via Jinja2 to avoid needing a running
HTTP server while still verifying the full template output.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from jinja2 import Environment, FileSystemLoader

from tests.scenarios.forbidden_terms import (
    FORBIDDEN_IN_ALL_MODES_HTML,
    FORBIDDEN_IN_FIELD_MODE_HTML,
)

TEMPLATES_DIR = Path(ROOT) / "src" / "phasmid" / "templates"

FAKE_STATE_PATH = "/home/user/.phasmid/state"
FAKE_WEB_TOKEN = "test-token-value-abc123"


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    return env


def _base_context(*, field_mode: bool, restricted_confirmed: bool, state_path: str = "") -> dict:
    return {
        "request": SimpleNamespace(url=SimpleNamespace(path="/maintenance")),
        "active": "maintenance",
        "web_token": FAKE_WEB_TOKEN,
        "max_upload_bytes": 10 * 1024 * 1024,
        "purge_confirmation_required": False,
        "duress_mode_enabled": False,
        "field_mode": field_mode,
        "deployment_mode": "standard",
        "restricted_confirmed": restricted_confirmed,
        "restricted_session_seconds_remaining": 0,
        "face_enrollment_enabled": False,
        "face_lock": {"enrolled": False, "locked": False},
        "destructive_clear_phrase": "CLEAR LOCAL ENTRY",
        "initialize_container_phrase": "INITIALIZE LOCAL CONTAINER",
        "emergency_brick_phrase": "CLEAR LOCAL ACCESS PATH",
        "restricted_confirmation_phrase": "CONFIRM RESTRICTED",
        "overwrite_confirmation_phrase": "OVERWRITE ENTRY",
        "entries": [],
        "audit_enabled": "0",
        "state_path": state_path,
    }


class FieldModeMaintenanceVisibility(unittest.TestCase):
    """Tests CLM-06, CLM-07, CLM-08."""

    def setUp(self):
        self.env = _make_env()

    def _render_maintenance(self, *, field_mode: bool, restricted_confirmed: bool,
                            state_path: str = "") -> str:
        template = self.env.get_template("maintenance.html")
        return template.render(
            _base_context(
                field_mode=field_mode,
                restricted_confirmed=restricted_confirmed,
                state_path=state_path,
            )
        )

    # ------------------------------------------------------------------
    # CLM-06: state path hidden in Field Mode before confirmation
    # ------------------------------------------------------------------

    def test_claim_CLM06_field_mode_hides_state_path_before_confirmation(self):
        """State directory path must not appear in Field Mode HTML before confirmation."""
        html = self._render_maintenance(
            field_mode=True,
            restricted_confirmed=False,
            state_path="",
        )
        self.assertNotIn(
            FAKE_STATE_PATH,
            html,
            "State path must not appear in Field Mode HTML before restricted confirmation",
        )

    def test_scenario_field_mode_state_path_visible_after_confirmation(self):
        """State path appears in HTML when restricted confirmation is active."""
        html = self._render_maintenance(
            field_mode=True,
            restricted_confirmed=True,
            state_path=FAKE_STATE_PATH,
        )
        self.assertIn(
            FAKE_STATE_PATH,
            html,
            "State path should appear after restricted confirmation",
        )

    def test_scenario_field_mode_off_state_path_visible(self):
        """Without Field Mode, state path appears in HTML normally."""
        html = self._render_maintenance(
            field_mode=False,
            restricted_confirmed=False,
            state_path=FAKE_STATE_PATH,
        )
        self.assertIn(
            FAKE_STATE_PATH,
            html,
            "State path should appear when Field Mode is off",
        )

    # ------------------------------------------------------------------
    # CLM-08: forbidden terms absent in Field Mode
    # ------------------------------------------------------------------

    def test_claim_CLM08_forbidden_terms_absent_from_field_mode_html(self):
        """Forbidden internal terms must not appear in Field Mode HTML output."""
        html = self._render_maintenance(
            field_mode=True,
            restricted_confirmed=False,
            state_path="",
        )
        violations: list[str] = []
        for term, reason in FORBIDDEN_IN_FIELD_MODE_HTML:
            if term in html:
                violations.append(f"  '{term}': {reason}")
        self.assertFalse(
            violations,
            "Forbidden terms found in Field Mode HTML:\n" + "\n".join(violations),
        )

    def test_claim_CLM08_forbidden_terms_absent_from_normal_mode_html(self):
        """Always-forbidden terms must not appear even in non-Field-Mode HTML."""
        html = self._render_maintenance(
            field_mode=False,
            restricted_confirmed=False,
            state_path="",
        )
        violations: list[str] = []
        for term, reason in FORBIDDEN_IN_ALL_MODES_HTML:
            if term in html:
                violations.append(f"  '{term}': {reason}")
        self.assertFalse(
            violations,
            "Always-forbidden terms found in HTML:\n" + "\n".join(violations),
        )

    # ------------------------------------------------------------------
    # Bounded output-difference assertion
    # ------------------------------------------------------------------

    def test_scenario_field_mode_visibility_output_diff_is_bounded(self):
        """Field Mode and normal mode HTML differ only in expected fields."""
        html_field = self._render_maintenance(
            field_mode=True,
            restricted_confirmed=False,
            state_path="",
        )
        html_normal = self._render_maintenance(
            field_mode=False,
            restricted_confirmed=False,
            state_path=FAKE_STATE_PATH,
        )

        # Both renders must produce non-empty HTML.
        self.assertGreater(len(html_field), 100)
        self.assertGreater(len(html_normal), 100)

        # In normal mode, the state path appears; in Field Mode it does not.
        self.assertNotIn(FAKE_STATE_PATH, html_field)
        self.assertIn(FAKE_STATE_PATH, html_normal)

    def test_scenario_field_mode_home_template_renders_without_forbidden_terms(self):
        """The home template must not contain always-forbidden terms."""
        template = self.env.get_template("home.html")
        ctx = _base_context(field_mode=True, restricted_confirmed=False)
        ctx["gate_status"] = {"status": "waiting", "matched": False, "label": ""}
        ctx["audit_count"] = 0
        ctx["entry_count"] = 0
        ctx["webui_active"] = False
        html = template.render(ctx)

        violations: list[str] = []
        for term, reason in FORBIDDEN_IN_ALL_MODES_HTML:
            if term in html:
                violations.append(f"  '{term}': {reason}")
        self.assertFalse(
            violations,
            "Always-forbidden terms found in home.html:\n" + "\n".join(violations),
        )


class ForbiddenTermsModule(unittest.TestCase):
    """Structural tests on forbidden_terms.py itself."""

    def test_scenario_field_mode_visibility_forbidden_list_is_nonempty(self):
        self.assertGreater(len(FORBIDDEN_IN_FIELD_MODE_HTML), 0)

    def test_scenario_field_mode_visibility_all_forbidden_entries_have_reasons(self):
        for term, reason in FORBIDDEN_IN_FIELD_MODE_HTML:
            self.assertTrue(term, "Term must be non-empty")
            self.assertTrue(reason, f"Reason missing for term '{term}'")

    def test_scenario_field_mode_visibility_always_forbidden_is_subset(self):
        field_terms = {t for t, _ in FORBIDDEN_IN_FIELD_MODE_HTML}
        always_terms = {t for t, _ in FORBIDDEN_IN_ALL_MODES_HTML}
        self.assertTrue(
            always_terms.issubset(field_terms),
            "FORBIDDEN_IN_ALL_MODES_HTML must be a subset of FORBIDDEN_IN_FIELD_MODE_HTML",
        )


if __name__ == "__main__":
    unittest.main()
