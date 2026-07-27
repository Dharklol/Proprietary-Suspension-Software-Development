from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _midpoint(a: list[float], b: list[float]) -> list[float]:
    return [(x + y) * 0.5 for x, y in zip(a, b)]


class SuspensionWufrZBarMapAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0006_remains_the_fixture_only_stage(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0006.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0006")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0005"])
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-SUSP-0013", "BENCH-SUSP-0014"])
        self.assertTrue(auth["scope"]["mechanism_point_fixture_authorized"])
        self.assertTrue(auth["scope"]["rocker_pickup_transport_authorized"])
        self.assertTrue(auth["scope"]["rigid_link_nominal_geometry_authorized"])
        self.assertFalse(auth["scope"]["scalar_delta_b_map_authorized"])
        self.assertFalse(auth["scope"]["jacobian_authorized"])
        self.assertFalse(auth["scope"]["vehicle_coordinate_generalized_force_authorized"])
        self.assertFalse(auth["scope"]["implementation_authorized"])
        self.assertFalse(auth["numerics"]["body_roll_substitution_allowed"])
        self.assertFalse(auth["numerics"]["track_width_approximation_allowed"])
        self.assertFalse(auth["numerics"]["wheel_travel_shortcut_allowed"])
        self.assertFalse(auth["numerics"]["historical_motion_ratio_allowed"])
        self.assertFalse(auth["numerics"]["sketch_row_connectivity_allowed"])
        self.assertFalse(auth["numerics"]["two_arm_stiffness_rescaling_allowed"])

        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("body roll", prohibited)
        self.assertIn("track width", prohibited)
        self.assertIn("wheel-travel", prohibited)
        self.assertIn("motion ratios", prohibited)
        self.assertIn("sketch row", prohibited)
        self.assertIn("doubling", prohibited)
        self.assertIn("vehicle-coordinate q_arb", prohibited)

    def test_source_record_preserves_preimplementation_recovery_finding(self) -> None:
        source = _load("data_catalog/wufr27_zbar_mapping_source_v0.toml")
        self.assertEqual(source["record_id"], "WUFR27_ZBAR_MAPPING_SOURCE_V0")
        self.assertTrue(source["mechanism_point_fixture_authorized"])
        self.assertTrue(source["rocker_pickup_transport_authorized"])
        self.assertTrue(source["rigid_link_nominal_geometry_authorized"])
        self.assertFalse(source["map_authorized"])
        self.assertFalse(source["jacobian_authorized"])
        self.assertFalse(source["vehicle_coordinate_generalized_force_authorized"])
        self.assertEqual(
            source["governing_constitutive_context"]["blade_settings_N_per_m"],
            [280000.0, 300000.0, 400000.0, 700000.0, 2300000.0],
        )
        self.assertIn("do not double", source["governing_constitutive_context"]["coordinate_scaling_boundary"].lower())
        recovered = source["recovered_sources"]
        self.assertEqual(recovered["inboard_calculator"]["box_file_id"], "2026725896730")
        self.assertEqual(recovered["simscape"]["rear_arb_model_box_file_id"], "2027153797982")
        self.assertEqual(recovered["simscape"]["rear_arb_figure_box_file_id"], "2027140002033")
        self.assertEqual(
            recovered["structural_design_binder"]["google_presentation_id"],
            "1aGXggyvdOBSUNVWx82j0Amqns8nsUUToDJGSnpHlb74",
        )
        shortcuts = source["blocked_shortcuts"]
        self.assertTrue(shortcuts["body_roll_equals_blade_deflection"])
        self.assertTrue(shortcuts["track_width_lever_approximation"])
        self.assertTrue(shortcuts["wheel_travel_difference_as_blade_deflection"])
        self.assertTrue(shortcuts["historical_scalar_motion_ratio"])
        self.assertTrue(shortcuts["reduced_axle_roll_stiffness_back_conversion"])
        self.assertTrue(shortcuts["two_arm_stiffness_rescaling_without_authority"])

    def test_nominal_front_fixture_identity(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml")
        front = fixture["front"]
        midpoint = _midpoint(front["blade_link_joint_left_m"], front["blade_link_joint_right_m"])
        for actual, expected in zip(midpoint, front["blade_housing_pivot_m"]):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertEqual(front["blade_housing_axis_unit"], [0.0, 0.0, 1.0])
        self.assertEqual(front["rocker_axis_unit"], [1.0, 0.0, 0.0])
        self.assertAlmostEqual(
            math.dist(front["blade_housing_pivot_m"], front["blade_link_joint_left_m"]),
            0.07254240001930749,
            places=14,
        )
        self.assertAlmostEqual(
            math.dist(front["blade_link_joint_left_m"], front["rocker_arb_pickup_left_m"]),
            front["link_joint_center_length_left_m"],
            places=14,
        )
        self.assertAlmostEqual(front["nominal_blade_arm_to_link_angle_deg"], 88.87404422054695, places=12)
        self.assertEqual(front["linkage_tube_nominal_length_in"], 7.22)

    def test_nominal_rear_fixture_identity_and_registration_boundary(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml")
        rear = fixture["rear"]
        midpoint = _midpoint(rear["blade_link_joint_left_m"], rear["blade_link_joint_right_m"])
        for actual, expected in zip(midpoint, rear["blade_housing_pivot_m"]):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertEqual(rear["raw_source_frame_registration_translation_m"], [1.5604, 0.0, 0.0])
        self.assertAlmostEqual(rear["blade_housing_pivot_m"][0], -0.022225, places=12)
        self.assertIn("not wufr-27 wheelbase authority", rear["registration_semantics"].lower())
        self.assertIn("1.5624", rear["registration_semantics"])
        self.assertAlmostEqual(
            math.dist(rear["blade_housing_pivot_m"], rear["blade_link_joint_left_m"]),
            0.07254239962933001,
            places=14,
        )
        self.assertAlmostEqual(rear["nominal_blade_arm_to_link_angle_deg"], 86.7741933427058, places=12)
        self.assertEqual(rear["linkage_tube_nominal_length_in"], 6.22)

    def test_fixture_records_rocker_stage_and_package_records_later_wheel_stage(self) -> None:
        fixture = _load("benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml")
        boundary = fixture["current_boundary"]
        self.assertTrue(boundary["two_arm_elastic_coordinate_authorized"])
        self.assertTrue(boundary["rocker_coordinate_jacobian_authorized"])
        self.assertTrue(boundary["rocker_coordinate_generalized_force_authorized"])

        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        current = package["authority_boundaries"]
        self.assertTrue(current["z_bar_geometry_map_authorized"])
        self.assertTrue(current["rocker_coordinate_generalized_force_authorized"])
        self.assertTrue(current["wheel_coordinate_generalized_force_authorized"])
        self.assertFalse(current["vehicle_equilibrium_authorized"])

    def test_benchmarks_preserve_source_and_fixture_gates(self) -> None:
        source_gate = _load("registry/records/benchmarks/BENCH-SUSP-0013.toml")["record"]
        fixture_gate = _load("registry/records/benchmarks/BENCH-SUSP-0014.toml")["record"]
        self.assertEqual(source_gate["verification_level"], "B")
        self.assertEqual(fixture_gate["verification_level"], "B")
        source_criteria = "\n".join(source_gate["acceptance_criteria"]).lower()
        fixture_criteria = "\n".join(fixture_gate["acceptance_criteria"]).lower()
        self.assertIn("two blade arms", source_criteria)
        self.assertIn("2.856", fixture_criteria)
        self.assertIn("88.874", fixture_criteria)
        self.assertIn("86.774", fixture_criteria)
        self.assertIn("1.5604", fixture_criteria)
        self.assertIn("1.5624", fixture_criteria)


if __name__ == "__main__":
    unittest.main()
