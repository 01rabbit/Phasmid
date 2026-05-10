import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pi_zero2w" / "luks_eval.py"
PROFILE = ROOT / "profiles" / "pi-zero2w.json"

spec = importlib.util.spec_from_file_location("luks_eval", SCRIPT)
assert spec is not None and spec.loader is not None
luks_eval = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = luks_eval
spec.loader.exec_module(luks_eval)


class LuksEvalTests(unittest.TestCase):
    def test_profile_loading(self):
        p = luks_eval.load_device_profile(PROFILE)
        self.assertEqual(p["device_tier"], "Tier-C")
        self.assertEqual(p["recommended_iter_time_ms"], 400)
        self.assertEqual(p["acceptance_luks_format_ms_max"], 4300)

    def test_tier_classification(self):
        self.assertEqual(
            luks_eval.classify_device_tier("Raspberry Pi Zero 2 W Rev 1.0", "aarch64"),
            "Tier-C",
        )
        self.assertEqual(
            luks_eval.classify_device_tier("x86 workstation", "x86_64"), "Tier-A"
        )

    def test_aes_capability_classification_inferred(self):
        status = luks_eval.classify_aes_acceleration(False, True, 29.0, 29.0)
        self.assertEqual(status, "inferred")

    def test_plateau_detection(self):
        data = [
            {"iter_time_ms": 500, "luks_format_ms": 4236, "luks_open_ms": 1158},
            {"iter_time_ms": 400, "luks_format_ms": 4203, "luks_open_ms": 1142},
            {"iter_time_ms": 300, "luks_format_ms": 4227, "luks_open_ms": 1132},
            {"iter_time_ms": 250, "luks_format_ms": 4205, "luks_open_ms": 1142},
        ]
        plateau, fmt_ratio, open_ratio = luks_eval.compute_plateau(data)
        self.assertTrue(plateau)
        self.assertGreaterEqual(fmt_ratio, 0.0)
        self.assertGreaterEqual(open_ratio, 0.0)

    def test_recommendation_prefers_highest_iter_with_new_threshold(self):
        profile = luks_eval.load_device_profile(PROFILE)
        ms = [
            {
                "iter_time_ms": 2000,
                "luks_format_ms": 7690,
                "luks_open_ms": 2675,
                "luks_format_ok": True,
                "luks_open_ok": True,
                "luks_format_in_range": False,
                "luks_open_in_range": True,
                "acceptable": False,
            },
            {
                "iter_time_ms": 500,
                "luks_format_ms": 4198,
                "luks_open_ms": 1151,
                "luks_format_ok": True,
                "luks_open_ok": True,
                "luks_format_in_range": True,
                "luks_open_in_range": True,
                "acceptable": True,
            },
        ]
        recommended, basis = luks_eval.recommend_iter(ms, profile, "Tier-C")
        self.assertEqual(recommended, 500)
        self.assertIn("highest iter-time", basis)

    def test_pass_with_constraints_evaluation(self):
        selected = {
            "luks_open_ok": True,
            "luks_open_in_range": True,
            "luks_format_in_range": False,
        }
        status = luks_eval.evaluate_status(
            tier="Tier-C",
            aes_status="inferred",
            dm_crypt_loadable=True,
            cryptsetup_available=True,
            selected=selected,
            recommended_iter=400,
        )
        self.assertEqual(status, "PASS_WITH_CONSTRAINTS")

    def test_pass_evaluation_with_new_format_threshold(self):
        selected = {
            "luks_open_ok": True,
            "luks_open_in_range": True,
            "luks_format_in_range": True,
        }
        status = luks_eval.evaluate_status(
            tier="Tier-C",
            aes_status="inferred",
            dm_crypt_loadable=True,
            cryptsetup_available=True,
            selected=selected,
            recommended_iter=500,
        )
        self.assertEqual(status, "PASS")


if __name__ == "__main__":
    unittest.main()
