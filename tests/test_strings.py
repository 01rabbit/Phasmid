import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid import strings


class UserVisibleStringTests(unittest.TestCase):
    def test_restricted_action_messages_match_policy_contract(self):
        self.assertEqual(strings.OPERATION_UNAVAILABLE, "operation unavailable")
        self.assertEqual(
            strings.RESTRICTED_CONFIRMATION_REQUIRED, "restricted confirmation required"
        )
        self.assertEqual(strings.CONFIRMATION_REJECTED, "confirmation rejected")
        self.assertEqual(strings.OPERATION_REJECTED, "operation rejected")

    def test_shared_strings_avoid_reviewer_sensitive_terms(self):
        forbidden = [
            r"\bProfile A\b",
            r"\bProfile B\b",
            r"\bprofile\b",
            r"\bdummy\b",
            r"\bsecret\b",
            r"\bdecoy\b",
            r"\btruth\b",
            r"\bfake\b",
            r"\bother mode\b",
            r"\bother profile\b",
            r"\bIMAGE KEY\b",
            r"\bregistered keys\b",
            r"\bself-destruct\b",
            r"\bkill secret\b",
            r"\berase truth\b",
            r"\bclean metadata\b",
            r"\bfully scrubbed\b",
            r"\bmetadata-free\b",
            r"\bfield-proof\b",
            r"\bforensic-proof\b",
        ]
        values = [
            value
            for name, value in vars(strings).items()
            if name.isupper() and isinstance(value, str)
        ]

        violations = []
        for value in values:
            for pattern in forbidden:
                if re.search(pattern, value, flags=re.IGNORECASE):
                    violations.append(value)

        self.assertEqual([], violations)


if __name__ == "__main__":
    unittest.main()
