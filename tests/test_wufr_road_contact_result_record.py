from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from scripts.run_wufr_road_contact_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]


class WUFRRoadContactResultRecordTests(unittest.TestCase):
    def test_frozen_result_matches_live_benchmark(self) -> None:
        with (ROOT / "benchmarks/vehicle/wufr_road_contact_result_v0.1.0.toml").open("rb") as stream:
            frozen = tomllib.load(stream)
        live = build_report()
        live9 = live["BENCH-VEH-0009"]
        live10 = live["BENCH-VEH-0010"]
        expected9 = frozen["BENCH-VEH-0009"]
        expected10 = frozen["BENCH-VEH-0010"]

        self.assertTrue(live9["pass"])
        self.assertTrue(live10["pass"])
        self.assertAlmostEqual(live10["radius_m"], expected10["radius_m"], places=12)
        self.assertEqual(live10["radius_source"], expected10["radius_source"])
        self.assertLessEqual(live10["maximum_radius_error_m"], 1.0e-12)
        self.assertLessEqual(live10["maximum_wheel_plane_membership_residual_m"], 1.0e-12)
        for corner, key in (
            ("front_left", "front_left_contact_point_m"),
            ("front_right", "front_right_contact_point_m"),
            ("rear_left", "rear_left_contact_point_m"),
            ("rear_right", "rear_right_contact_point_m"),
        ):
            actual = live10["nominal_circle"][corner]["contact_point_m"]
            for value, target in zip(actual, expected10[key]):
                self.assertAlmostEqual(value, target, places=12)

        self.assertEqual(live9["coordinate_order"], expected9["coordinate_order"])
        self.assertEqual(live9["body_coordinate_order"], expected9["body_coordinate_order"])
        for value, target in zip(live9["nominal_wheel_coordinates_m"], expected9["nominal_wheel_coordinates_m"]):
            self.assertAlmostEqual(value, target, places=12)
        self.assertLessEqual(live9["maximum_nominal_road_gap_m"], 2.0e-9)
        for actual_row, expected_row in zip(live9["J_wb"], expected9["J_wb"]):
            for value, target in zip(actual_row, expected_row):
                self.assertAlmostEqual(value, target, places=9)
        self.assertAlmostEqual(live9["J_wb_two_step_error"], expected9["J_wb_two_step_error"], places=12)
        for value, target in zip(live9["pure_heave_0p004_wheel_coordinates_m"], expected9["pure_heave_0p004_wheel_coordinates_m"]):
            self.assertAlmostEqual(value, target, places=9)
        for value, target in zip(live9["combined_wheel_coordinates_m"], expected9["combined_wheel_coordinates_m"]):
            self.assertAlmostEqual(value, target, places=9)

        for corner, expected_c, expected_q in zip(
            expected9["coordinate_order"],
            expected9["contact_coefficients"],
            expected9["unsprung_gravity_generalized_force_N"],
        ):
            actual = live9["nominal"][corner]
            self.assertAlmostEqual(actual["contact_coefficient"], expected_c, places=8)
            self.assertAlmostEqual(actual["unsprung_gravity_generalized_force_N"], expected_q, places=6)
            self.assertLessEqual(actual["unsprung_gravity_two_step_error_N"], 1.0e-6)

        self.assertEqual(live9["unsprung_corner_mass_kg"], expected9["unsprung_corner_mass_kg"])
        self.assertFalse(live9["road_reactions_available"])
        self.assertFalse(live10["loaded_radius_used"])
        self.assertFalse(live10["tire_vertical_compliance_used"])
        self.assertFalse(live10["historical_contact_patch_fitted"])


if __name__ == "__main__":
    unittest.main()
