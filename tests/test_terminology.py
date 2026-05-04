import glob
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
    "docs/RPI_ZERO_DEPLOYMENT.md",
    "docs/RPI_ZERO_APPLIANCE_DEPLOYMENT.md",
    "docs/SOURCE_SAFE_WORKFLOW.md",
    "docs/SEIZURE_REVIEW_CHECKLIST.md",
    "docs/FIELD_TEST_PROCEDURE.md",
    "docs/REVIEW_VALIDATION_RECORD.md",
    "docs/SOLUTION_READINESS_PLAN.md",
    "docs/OPERATIONS.md",
    "docs/RESTRICTED_ACTIONS.md",
    "docs/STATE_RECOVERY.md",
    "contrib/systemd/phantasm.service",
]

TEMPLATE_DIR = os.path.join(ROOT, "src", "phantasm", "templates")
PYTHON_BOUNDARY_FILES = [
    "src/phantasm/web_server.py",
    "src/phantasm/cli.py",
    "src/phantasm/audit.py",
    "src/phantasm/capabilities.py",
    "src/phantasm/emergency_daemon.py",
    "src/phantasm/config.py",
    "src/phantasm/metadata.py",
    "src/phantasm/bridge_ui.py",
    "src/phantasm/face_lock.py",
    "src/phantasm/restricted_actions.py",
    "src/phantasm/strings.py",
    "src/phantasm/operations.py",
    "src/phantasm/state_store.py",
    "src/phantasm/passphrase_policy.py",
    "src/phantasm/attempt_limiter.py",
    "src/phantasm/crypto_boundary.py",
]

FORBIDDEN_PATTERNS = [
    r"\bProfile A\b",
    r"\bProfile B\b",
    r"\bprofile\b",
    r"\bprofiles\b",
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
    r"\bother mode\b",
    r"\bother profile\b",
    r"\bIMAGE KEY\b",
    r"\bRegistered keys\b",
    r"\bself-destruct\b",
    r"\bkill profile\b",
    r"\bkill secret\b",
    r"\berase truth\b",
    r"\bclean metadata\b",
    r"\bfully scrubbed\b",
    r"\bmetadata-free\b",
    r"\bfield-proof\b",
    r"\bforensic-proof\b",
    r"\bpurge_password\b",
    r"\bX-Local-State-Updated\b",
    r"\bX-Purge-Applied\b",
    r"\bX-Filename\b",
    r"\bLocal state updated\b",
    r"\balternate_entry_cleared\b",
    r"\bprofile_purged\b",
    r"\bsecret_removed\b",
    r"\bdecoy_opened\b",
    r"\bdestructive password\b",
    r"\bemergency brick\b",
]


class TerminologyAuditTests(unittest.TestCase):
    def test_all_python_modules_are_classified_for_terminology_audit(self):
        all_modules = {
            os.path.relpath(path, ROOT)
            for path in glob.glob(os.path.join(ROOT, "src", "phantasm", "*.py"))
        }
        scanned = set(PYTHON_BOUNDARY_FILES)
        internal_allowlist = {
            "src/phantasm/__init__.py",
            "src/phantasm/ai_gate.py",
            "src/phantasm/gv_core.py",
            "src/phantasm/kdf_engine.py",
        }
        self.assertEqual(all_modules, scanned | internal_allowlist)

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

    def test_python_boundary_strings_do_not_expose_forbidden_terms(self):
        paths = [os.path.join(ROOT, path) for path in PYTHON_BOUNDARY_FILES]
        violations = _scan_paths(paths)
        self.assertEqual([], violations)

    def test_normal_navigation_does_not_link_restricted_route(self):
        with open(
            os.path.join(TEMPLATE_DIR, "base.html"), "r", encoding="utf-8"
        ) as handle:
            base = handle.read()
        nav_match = re.search(r"<nav.*?</nav>", base, flags=re.DOTALL)
        self.assertIsNotNone(nav_match)
        self.assertNotIn("/emergency", nav_match.group(0))


def _scan_paths(paths):
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
    return violations


def _line_is_allowed(line):
    return bool(
        re.search(r"PHANTASM_[A-Z_]*SECRET", line)
        or re.search(r"import secrets|secrets\.", line)
        or re.search(r"argparse\.SUPPRESS", line)
        or re.search(r"no lies, no unnecessary truth", line, flags=re.IGNORECASE)
        or re.search(r"PHANTASM_HARDWARE_SECRET", line)
        or re.search(r"PHANTASM_STATE_SECRET", line)
    )


if __name__ == "__main__":
    unittest.main()
