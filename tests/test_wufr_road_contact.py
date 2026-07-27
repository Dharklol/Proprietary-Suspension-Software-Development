from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import tomllib
import unittest

from pssd_vehicle import load_wufr_static_gravity_allocation
from pssd_vehicle.wufr_road_contact import (
    WUFRRoadContactFailureCode,
    evaluate_corner_road_state,
    evaluate_wufr_road_contact,
    load_wufr_road_contact_provider,
    reconstruct_historical_front_contact_reference,
    solve_road_compatibility,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml"
SUSPENSION = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
STEERING = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
WHOLE_VEHICLE = ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml"
GRAVITY = ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml"
FRONT_LEFT_SOURCE = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_LEFT_WHEEL_REFERENCE_SOURCE_V0.toml"


def _load(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


class WUFRRoadContactImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = load_wufr_road_contact_provider(
            source_path=SOURCE,
            suspension_geometry_path=SUSPENSION,
            wheel_profile_path=WHEEL_PROFILE,
            steering_geometry_path=STEERING,
            whole_vehicle_path=WHOLE_VEHICLE,
        )
        cls.gravity = load_wufr_static_gravity_allocation(GRAVITY)
        cls.nominal_pose = cls.provider.nominal_body_pose()
        cls.nominal = evaluate_wufr_road_contact(cls.provider, cls.nominal_pose, cls.gravity)

    def test_bench_veh_0008_historical_front_contact_reconstruction_uses_3d_twist(self) -> None:
        source = _load(SOURCE)
        fixture = _load(FRONT_LEFT_SOURCE)
        nominal = fixture["nominal"]
        states = {round(float(row["heave_mm"]), 6): row for row in fixture["states"]}
        checks = [row for row in source["historical_heave_checks"] if row["corner"] == "front_left"]
        max_point_error = 0.0
        max_twist_error = 0.0
        nominal_contact = tuple(source["contact_reference"]["front_left_source_m"])
        for check in checks:
            state = states[round(float(check["heave_mm"]), 6)]
            reconstructed, twist = reconstruct_historical_front_contact_reference(
                nominal_contact_m=nominal_contact,
                nominal_lower_m=tuple(nominal["lower_m"]),
                nominal_upper_m=tuple(nominal["upper_m"]),
                nominal_tie_m=tuple(nominal["tie_m"]),
                current_lower_m=tuple(state["lower_m"]),
                current_upper_m=tuple(state["upper_m"]),
                current_tie_m=tuple(state["tie_m"]),
            )
            expected = tuple(check["contact_reference_body_m"])
            max_point_error = max(max_point_error, math.dist(reconstructed, expected))
            max_twist_error = max(max_twist_error, abs(math.degrees(twist) - float(check["source_reconstructed_twist_deg"])))
            self.assertGreater(abs(float(state["scalar_steer_angle_deg"]) - math.degrees(twist)), 7.0e-4)
        self.assertLessEqual(max_point_error, 5.0e-6)
        self.assertLessEqual(max_twist_error, 2.0e-8)

    def test_bench_veh_0009_nominal_roots_contact_coefficients_and_gravity(self) -> None:
        result = self.nominal
        self.assertTrue(result.ok, result.message)
        assert result.compatibility.wheel_coordinates_m is not None
        self.assertLessEqual(max(abs(v) for v in result.compatibility.wheel_coordinates_m), 2.0e-8)
        self.assertEqual(tuple(root.corner_id for root in result.compatibility.roots), ("front_left", "front_right", "rear_left", "rear_right"))
        self.assertLessEqual(max(abs(root.state.road_gap_m) for root in result.compatibility.roots if root.state is not None), 2.0e-9)
        self.assertEqual(len(result.contact_coefficients), 4)
        for item in result.contact_coefficients:
            self.assertTrue(item.ok, item.message)
            assert item.value is not None
            self.assertGreater(item.value, 0.0)
            self.assertLess(abs(item.value - 1.0), 0.05)
        self.assertEqual(len(result.unsprung_gravity_forces), 4)
        for item in result.unsprung_gravity_forces:
            self.assertTrue(item.ok, item.message)
            assert item.value is not None
            self.assertLess(abs(item.value + 49.05), 0.1)

    def test_bench_veh_0009_jacobian_two_step_and_direct_finite_difference(self) -> None:
        result = self.nominal
        self.assertTrue(result.ok, result.message)
        assert result.jacobian is not None and result.jacobian.jacobian is not None
        self.assertTrue(result.jacobian.ok, result.jacobian.message)
        self.assertEqual(result.jacobian.coordinate_order, ("z_s_m", "phi_rad", "theta_rad"))
        self.assertEqual(result.jacobian.wheel_order, ("front_left", "front_right", "rear_left", "rear_right"))
        self.assertIsNotNone(result.jacobian.convergence_error)

        h = 1.5e-4
        plus = solve_road_compatibility(self.provider, replace(self.nominal_pose, z_s_m=h))
        minus = solve_road_compatibility(self.provider, replace(self.nominal_pose, z_s_m=-h))
        self.assertTrue(plus.ok, plus.message)
        self.assertTrue(minus.ok, minus.message)
        assert plus.wheel_coordinates_m is not None and minus.wheel_coordinates_m is not None
        direct = [(p - m) / (2.0 * h) for p, m in zip(plus.wheel_coordinates_m, minus.wheel_coordinates_m)]
        for row, expected in zip(result.jacobian.jacobian, direct):
            self.assertAlmostEqual(row[0], expected, places=4)

    def test_nonzero_pure_heave_and_combined_pose_close_road_without_clipping(self) -> None:
        pure = solve_road_compatibility(self.provider, replace(self.nominal_pose, z_s_m=0.004))
        self.assertTrue(pure.ok, pure.message)
        assert pure.wheel_coordinates_m is not None
        self.assertAlmostEqual(pure.wheel_coordinates_m[0], pure.wheel_coordinates_m[1], places=7)
        self.assertAlmostEqual(pure.wheel_coordinates_m[2], pure.wheel_coordinates_m[3], places=7)
        self.assertLess(max(abs(root.state.road_gap_m) for root in pure.roots if root.state is not None), 2.0e-8)

        combined_pose = replace(self.nominal_pose, z_s_m=0.0015, phi_rad=0.0020, theta_rad=-0.0015)
        combined = solve_road_compatibility(self.provider, combined_pose)
        self.assertTrue(combined.ok, combined.message)
        assert combined.wheel_coordinates_m is not None
        self.assertGreater(max(combined.wheel_coordinates_m) - min(combined.wheel_coordinates_m), 1.0e-3)
        front_steering = [root.state.point_state.steering_rotation_rad for root in combined.roots[:2] if root.state is not None]
        self.assertEqual(len(front_steering), 2)
        self.assertGreater(max(abs(float(v)) for v in front_steering), 1.0e-6)

    def test_contact_and_gravity_are_evaluated_from_point_virtual_work(self) -> None:
        result = self.nominal
        self.assertTrue(result.ok, result.message)
        masses = {item.corner_id: item for item in self.gravity.unsprung}
        h = 7.5e-6
        for root, coefficient, gravity_force in zip(result.compatibility.roots, result.contact_coefficients, result.unsprung_gravity_forces):
            assert root.wheel_coordinate_m is not None and coefficient.value is not None and gravity_force.value is not None
            plus = evaluate_corner_road_state(self.provider, self.nominal_pose, root.corner_id, root.wheel_coordinate_m + h)
            minus = evaluate_corner_road_state(self.provider, self.nominal_pose, root.corner_id, root.wheel_coordinate_m - h)
            direct_c = (plus.contact_road.position_m[2] - minus.contact_road.position_m[2]) / (2.0 * h)
            self.assertAlmostEqual(coefficient.value, direct_c, places=5)
            mass = masses[root.corner_id]
            u_plus = mass.mass_kg * self.gravity.g_mps2 * plus.wheel_center_road.position_m[2]
            u_minus = mass.mass_kg * self.gravity.g_mps2 * minus.wheel_center_road.position_m[2]
            direct_q = -(u_plus - u_minus) / (2.0 * h)
            self.assertAlmostEqual(gravity_force.value, direct_q, places=5)

    def test_out_of_domain_body_pose_fails_without_coordinate_clipping(self) -> None:
        outside = solve_road_compatibility(self.provider, replace(self.nominal_pose, z_s_m=0.050))
        self.assertFalse(outside.ok)
        self.assertEqual(outside.failure_code, WUFRRoadContactFailureCode.BODY_POSE_OUTSIDE_DOMAIN)


if __name__ == "__main__":
    unittest.main()
