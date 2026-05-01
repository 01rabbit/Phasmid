import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))


USER_FACING_FILES = [
    "README.md",
    "docs/SPECIFICATION.md",
    "docs/THREAT_MODEL.md",
]

TEMPLATE_DIR = os.path.join(ROOT, "src", "phantasm", "templates")

FORBIDDEN_PATTERNS = [
    r"\bProfile A\b",
    r"\bProfile B\b",
    r"\bdummy\b",
    r"\bsecret\b",
    r"\bdecoy\b",
    r"\btruth\b",
    r"\bfake\b",
    r"\breal\b",
    r"\balternate profile\b",
    r"\bhidden profile\b",
    r"\bsecond profile\b",
    r"\bpurge other profile\b",
    r"\bself-destruct\b",
    r"\bkill profile\b",
    r"\berase truth\b",
]


class TerminologyAuditTests(unittest.TestCase):
    def test_user_facing_files_do_not_expose_forbidden_terms(self):
        paths = [os.path.join(ROOT, path) for path in USER_FACING_FILES]
        paths.extend(
            os.path.join(TEMPLATE_DIR, name)
            for name in os.listdir(TEMPLATE_DIR)
            if name.endswith(".html")
        )

        violations = []
        for path in paths:
            with open(path, "r", encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, start=1):
                    if _line_is_allowed(line):
                        continue
                    for pattern in FORBIDDEN_PATTERNS:
                        if re.search(pattern, line, flags=re.IGNORECASE):
                            rel = os.path.relpath(path, ROOT)
                            violations.append(f"{rel}:{lineno}: {line.strip()}")

        self.assertEqual([], violations)

    def test_normal_navigation_does_not_link_restricted_route(self):
        with open(os.path.join(TEMPLATE_DIR, "base.html"), "r", encoding="utf-8") as handle:
            base = handle.read()
        nav_match = re.search(r"<nav.*?</nav>", base, flags=re.DOTALL)
        self.assertIsNotNone(nav_match)
        self.assertNotIn("/emergency", nav_match.group(0))


def _line_is_allowed(line):
    return bool(re.search(r"PHANTASM_[A-Z_]*SECRET", line))


if __name__ == "__main__":
    unittest.main()
