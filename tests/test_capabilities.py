import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.capabilities import Capability, active_policy, capability_enabled


class CapabilityPolicyTests(unittest.TestCase):
    def test_standard_mode_allows_existing_default_capabilities(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(active_policy().name, "standard")
            self.assertTrue(capability_enabled(Capability.METADATA_CHECK))
            self.assertTrue(capability_enabled(Capability.METADATA_REDUCE))
            self.assertTrue(capability_enabled(Capability.RESTRICTED_ACTION))
            self.assertTrue(capability_enabled(Capability.RAPID_LOCAL_CLEAR))

    def test_field_mode_reduces_high_risk_capabilities(self):
        with mock.patch.dict(os.environ, {"PHASMID_PROFILE": "field"}, clear=True):
            self.assertEqual(active_policy().name, "field")
            self.assertTrue(capability_enabled(Capability.METADATA_CHECK))
            self.assertTrue(capability_enabled(Capability.RESTRICTED_ACTION))
            self.assertFalse(capability_enabled(Capability.TOKEN_ROTATION))
            self.assertFalse(capability_enabled(Capability.SESSION_RESET))
            self.assertFalse(capability_enabled(Capability.RAPID_LOCAL_CLEAR))

    def test_maintenance_mode_rejects_storage_workflow_capabilities(self):
        with mock.patch.dict(
            os.environ, {"PHASMID_PROFILE": "maintenance"}, clear=True
        ):
            self.assertEqual(active_policy().name, "maintenance")
            self.assertFalse(capability_enabled(Capability.METADATA_CHECK))
            self.assertFalse(capability_enabled(Capability.METADATA_REDUCE))
            self.assertFalse(capability_enabled(Capability.RESTRICTED_ACTION))
            self.assertTrue(capability_enabled(Capability.TOKEN_ROTATION))

    def test_unknown_mode_falls_back_to_standard(self):
        with mock.patch.dict(os.environ, {"PHASMID_PROFILE": "unknown"}, clear=True):
            self.assertEqual(active_policy().name, "standard")


if __name__ == "__main__":
    unittest.main()
