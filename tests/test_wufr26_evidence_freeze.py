from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WUFR26EvidenceFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        with (
            ROOT
            / "configurations"
            / "steering"
            / "WUFR26_DESIGN_NOMINAL_V0.toml"
        ).open("rb") as stream:
            self.configuration = tomllib.load(stream)
        with (
            ROOT
            / "benchmarks"
            / "steering"
            / "wufr26_level_e_test3_result.toml"
        ).open("rb") as stream:
            self.result = tomllib.load(stream)

    def test_team_supplied_rack_center_confirms_canonical_mapping(self) -> None:
        rack = self.configuration["rack"]
        lateral_mm, vertical_mm, longitudinal_mm = rack["solidworks_native_center_mm"]
        mapped = (
            longitudinal_mm * 0.001,
            lateral_mm * 0.001,
            vertical_mm * 0.001,
        )
        for actual, expected in zip(rack["axis_origin"], mapped):
            self.assertAlmostEqual(actual, expected, places=12)
        for actual, expected in zip(mapped, (-0.079298, 0.0, 0.162865)):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_nominal_right_geometry_is_exact_y_reflection(self) -> None:
        left = self.configuration["left"]
        right = self.configuration["right"]
        point_keys = (
            "steering_axis_lower_point",
            "steering_axis_upper_point",
            "steering_axis_ground_intersection",
            "outer_tie_rod_joint_at_center",
        )
        for key in point_keys:
            left_point = left[key]
            right_point = right[key]
            self.assertEqual(right_point[0], left_point[0], key)
            self.assertEqual(right_point[1], -left_point[1], key)
            self.assertEqual(right_point[2], left_point[2], key)

        rack = self.configuration["rack"]
        left_inner = rack["left_inner_joint_at_center"]
        right_inner = rack["right_inner_joint_at_center"]
        self.assertEqual(right_inner[0], left_inner[0])
        self.assertEqual(right_inner[1], -left_inner[1])
        self.assertEqual(right_inner[2], left_inner[2])
        self.assertEqual(right["static_toe"], left["static_toe"])
        self.assertEqual(right["static_camber"], left["static_camber"])

    def test_level_e_result_and_fdr_endpoint_cross_check_are_frozen(self) -> None:
        self.assertEqual(
            self.result["status"],
            "frozen_descriptive_cross_tool_consistency",
        )
        cross_check = self.result["fdr_endpoint_cross_check"]
        less_error = (
            cross_check["less_steered_candidate_deg"]
            - cross_check["less_steered_fdr_deg"]
        )
        more_error = (
            cross_check["more_steered_candidate_deg"]
            - cross_check["more_steered_fdr_deg"]
        )
        self.assertAlmostEqual(
            less_error,
            cross_check["less_steered_candidate_minus_fdr_deg"],
            places=12,
        )
        self.assertAlmostEqual(
            more_error,
            cross_check["more_steered_candidate_minus_fdr_deg"],
            places=12,
        )
        self.assertEqual(
            self.result["review"]["acceptance_disposition"],
            "frozen_descriptive_only_no_pass_fail_tolerance",
        )


if __name__ == "__main__":
    unittest.main()
