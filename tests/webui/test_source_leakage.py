from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from tests.scenarios.forbidden_terms import (
    FORBIDDEN_IN_ALL_MODES_HTML,
    FORBIDDEN_IN_FIELD_MODE_HTML,
)

TEMPLATES_DIR = Path(ROOT) / "src" / "phasmid" / "templates"


class WebUISourceLeakageTests(unittest.TestCase):
    def test_templates_do_not_include_forbidden_internal_terms(self):
        terms = sorted(
            {
                term
                for term, _reason in (
                    FORBIDDEN_IN_ALL_MODES_HTML + FORBIDDEN_IN_FIELD_MODE_HTML
                )
            }
        )
        offenders: list[str] = []
        for template in TEMPLATES_DIR.glob("*.html"):
            content = template.read_text(encoding="utf-8")
            for term in terms:
                if term in content:
                    offenders.append(f"{template.name}: {term}")
        self.assertFalse(
            offenders,
            "Forbidden internal terms found in template sources:\n"
            + "\n".join(offenders),
        )

    def test_templates_do_not_include_html_comments(self):
        offenders: list[str] = []
        for template in TEMPLATES_DIR.glob("*.html"):
            content = template.read_text(encoding="utf-8")
            if "<!--" in content or "-->" in content:
                offenders.append(template.name)
        self.assertFalse(
            offenders,
            "HTML comments should not remain in production templates:\n"
            + "\n".join(offenders),
        )

    def test_no_i18n_keys_use_forbidden_terms(self):
        # i18n key transport is attribute-based in templates if used at all.
        terms = sorted(
            {
                term
                for term, _reason in (
                    FORBIDDEN_IN_ALL_MODES_HTML + FORBIDDEN_IN_FIELD_MODE_HTML
                )
            }
        )
        offenders: list[str] = []
        for template in TEMPLATES_DIR.glob("*.html"):
            content = template.read_text(encoding="utf-8")
            if "data-i18n" not in content:
                continue
            for term in terms:
                if term in content:
                    offenders.append(f"{template.name}: {term}")
        self.assertFalse(
            offenders,
            "Forbidden terms found in i18n key-bearing template source:\n"
            + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
