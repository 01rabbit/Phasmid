import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phantasm.capabilities import Capability
from phantasm.restricted_actions import (
    RestrictedActionPolicy,
    RestrictedActionRejected,
    evaluate_restricted_action,
)


class RestrictedActionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = RestrictedActionPolicy(
            action_id="test_action",
            capability=Capability.RESTRICTED_ACTION,
            confirmation_phrase="CONFIRM",
        )

    def test_accepts_all_required_predicates(self):
        self.assertTrue(
            evaluate_restricted_action(
                self.policy,
                capability_allowed=True,
                restricted_confirmed=True,
                confirmation="CONFIRM",
            )
        )

    def test_rejects_disabled_capability(self):
        with self.assertRaises(RestrictedActionRejected) as ctx:
            evaluate_restricted_action(
                self.policy,
                capability_allowed=False,
                restricted_confirmed=True,
                confirmation="CONFIRM",
            )
        self.assertEqual(ctx.exception.message, "operation unavailable")

    def test_rejects_missing_restricted_confirmation(self):
        with self.assertRaises(RestrictedActionRejected) as ctx:
            evaluate_restricted_action(
                self.policy,
                capability_allowed=True,
                restricted_confirmed=False,
                confirmation="CONFIRM",
            )
        self.assertEqual(ctx.exception.message, "restricted confirmation required")

    def test_rejects_wrong_confirmation_phrase(self):
        with self.assertRaises(RestrictedActionRejected) as ctx:
            evaluate_restricted_action(
                self.policy,
                capability_allowed=True,
                restricted_confirmed=True,
                confirmation="WRONG",
            )
        self.assertEqual(ctx.exception.message, "confirmation rejected")

    def test_can_skip_restricted_confirmation_for_compatibility_action(self):
        policy = RestrictedActionPolicy(
            action_id="compat_action",
            capability=Capability.RAPID_LOCAL_CLEAR,
            confirmation_phrase="CONFIRM",
            require_restricted_confirmation=False,
        )
        self.assertTrue(
            evaluate_restricted_action(
                policy,
                capability_allowed=True,
                restricted_confirmed=False,
                confirmation="CONFIRM",
            )
        )


if __name__ == "__main__":
    unittest.main()
