import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

from phasmid.context_profile import (
    BUILT_IN_PROFILES,
    ContextProfile,
    ProfileValidationResult,
    get_profile,
    list_profiles,
    validate_against_profile,
)


class TestBuiltInProfiles(unittest.TestCase):
    def test_all_required_profiles_exist(self):
        for name in ("travel", "field_engineer", "researcher", "maintenance", "archive"):
            self.assertIn(name, BUILT_IN_PROFILES, f"Missing built-in profile: {name}")

    def test_list_profiles_returns_sorted_names(self):
        names = list_profiles()
        self.assertEqual(names, sorted(names))
        for name in ("travel", "field_engineer", "researcher", "maintenance", "archive"):
            self.assertIn(name, names)

    def test_get_profile_returns_correct_object(self):
        p = get_profile("travel")
        self.assertIsNotNone(p)
        self.assertEqual(p.profile_name, "travel")

    def test_get_profile_returns_none_for_unknown(self):
        self.assertIsNone(get_profile("nonexistent_profile_xyz"))

    def test_get_profile_case_insensitive(self):
        p = get_profile("TRAVEL")
        self.assertIsNotNone(p)
        self.assertEqual(p.profile_name, "travel")

    def test_all_profiles_have_dummy_content_types(self):
        for name, profile in BUILT_IN_PROFILES.items():
            self.assertTrue(
                len(profile.dummy_content_types) > 0,
                f"Profile '{name}' has no dummy_content_types",
            )

    def test_all_profiles_have_typical_directories(self):
        for name, profile in BUILT_IN_PROFILES.items():
            self.assertTrue(
                len(profile.typical_directories) > 0,
                f"Profile '{name}' has no typical_directories",
            )

    def test_all_profiles_have_valid_size_range(self):
        for name, profile in BUILT_IN_PROFILES.items():
            min_b, max_b = profile.expected_size_range
            self.assertGreater(max_b, min_b, f"Profile '{name}' has invalid size range")

    def test_all_profiles_have_positive_min_file_count(self):
        for name, profile in BUILT_IN_PROFILES.items():
            self.assertGreater(
                profile.min_file_count, 0, f"Profile '{name}' min_file_count must be > 0"
            )

    def test_all_profiles_validate_without_warnings(self):
        for name, profile in BUILT_IN_PROFILES.items():
            warnings = profile.validate()
            self.assertEqual(
                warnings, [], f"Profile '{name}' has unexpected validation warnings: {warnings}"
            )

    def test_profile_description_is_non_empty(self):
        for name, profile in BUILT_IN_PROFILES.items():
            self.assertTrue(
                len(profile.description) > 0, f"Profile '{name}' has empty description"
            )


class TestContextProfileValidation(unittest.TestCase):
    def _make_profile(self, **overrides) -> ContextProfile:
        defaults = dict(
            profile_name="test",
            container_name="test.vessel",
            expected_size_range=(10 * 1024 * 1024, 500 * 1024 * 1024),
            dummy_content_types=("txt", "pdf"),
            description="test profile",
            typical_directories=("docs",),
            min_file_count=5,
            occupancy_ratio_warn=0.10,
        )
        defaults.update(overrides)
        return ContextProfile(**defaults)

    def test_validate_returns_no_warnings_for_valid_profile(self):
        profile = self._make_profile()
        warnings = profile.validate()
        self.assertEqual(warnings, [])

    def test_validate_warns_on_negative_min(self):
        profile = self._make_profile(expected_size_range=(-1, 500 * 1024 * 1024))
        warnings = profile.validate()
        self.assertTrue(any("negative" in w for w in warnings))

    def test_validate_warns_when_max_less_than_min(self):
        profile = self._make_profile(expected_size_range=(1000, 500))
        warnings = profile.validate()
        self.assertTrue(any("less than minimum" in w for w in warnings))

    def test_validate_warns_on_zero_min_file_count(self):
        profile = self._make_profile(min_file_count=0)
        warnings = profile.validate()
        self.assertTrue(any("empty" in w for w in warnings))

    def test_validate_warns_on_low_occupancy_ratio(self):
        profile = self._make_profile(occupancy_ratio_warn=0.001)
        warnings = profile.validate()
        self.assertTrue(any("suspicious" in w or "below 5%" in w for w in warnings))

    def test_validate_warns_on_no_content_types(self):
        profile = self._make_profile(dummy_content_types=())
        warnings = profile.validate()
        self.assertTrue(any("content_types" in w for w in warnings))


class TestValidateAgainstProfile(unittest.TestCase):
    def setUp(self):
        self.profile = get_profile("travel")

    def test_no_warnings_for_plausible_config(self):
        result = validate_against_profile(
            profile=self.profile,
            container_size_bytes=200 * 1024 * 1024,
            dummy_size_bytes=50 * 1024 * 1024,
            file_count=50,
            extension_distribution={"jpg": 30, "txt": 10, "pdf": 10},
        )
        self.assertIsInstance(result, ProfileValidationResult)
        self.assertEqual(result.warnings, [])
        self.assertTrue(result.is_plausible)

    def test_warns_when_dummy_is_empty(self):
        result = validate_against_profile(
            profile=self.profile,
            container_size_bytes=200 * 1024 * 1024,
            dummy_size_bytes=0,
            file_count=0,
            extension_distribution={},
        )
        self.assertTrue(len(result.warnings) > 0)
        self.assertFalse(result.is_plausible)

    def test_warns_when_file_count_below_minimum(self):
        result = validate_against_profile(
            profile=self.profile,
            container_size_bytes=200 * 1024 * 1024,
            dummy_size_bytes=30 * 1024 * 1024,
            file_count=2,
            extension_distribution={"txt": 2},
        )
        self.assertTrue(any("file count" in w for w in result.warnings))

    def test_warns_when_occupancy_too_low(self):
        result = validate_against_profile(
            profile=self.profile,
            container_size_bytes=500 * 1024 * 1024,
            dummy_size_bytes=1 * 1024,
            file_count=30,
            extension_distribution={"txt": 30},
        )
        self.assertTrue(any("occupancy" in w for w in result.warnings))

    def test_occupancy_ratio_calculated_correctly(self):
        result = validate_against_profile(
            profile=self.profile,
            container_size_bytes=100 * 1024 * 1024,
            dummy_size_bytes=20 * 1024 * 1024,
            file_count=30,
            extension_distribution={"jpg": 30},
        )
        self.assertAlmostEqual(result.occupancy_ratio, 0.20, places=2)

    def test_zero_container_size_no_occupancy_warning(self):
        result = validate_against_profile(
            profile=self.profile,
            container_size_bytes=0,
            dummy_size_bytes=10 * 1024 * 1024,
            file_count=20,
            extension_distribution={"jpg": 20},
        )
        self.assertEqual(result.occupancy_ratio, 0.0)
        self.assertFalse(any("occupancy" in w for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
