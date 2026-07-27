from __future__ import annotations

from dataclasses import replace
import inspect
import math
from pathlib import Path
import unittest

from pssd_suspension import Axle, Side, build_nominal_wheel_reference, load_wufr26_wheel_reference_profile
from pssd_vehicle import load_wufr_static_gravity_allocation
from pssd_vehicle.wufr_road_contact import (
    WUFRRoadContactError,
    WUFRRoadContactFailureCode,
    evaluate_corner_road_state,
    evaluate_wufr_road_contact,
    ideal_rigid_circle_contact,
    load_wufr_road_contact_provider,
    solve_road_compatibility,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml"
SUSPENSION = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
STEERING = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
WHOLE_VEHICLE = ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml"
GRAVITY = ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml"


class WUFRRigidCircleContactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE)
        cls.provider = load_wufr_road_contact_provider(
            source_path=SOURCE,
            suspension_geometry_path=SUSPENSION,
            wheel_profile_path=WHEEL_PROFILE,
            steering_geometry_path=STEERING,
            whole_vehicle_path=WHOLE_VEHICLE,
        )
        cls.gravity = load_wufr_static_gravity_allocation(GRAVITY)
        cls.nominal_pose = cls.provider.nominal_body_pose()

    def test_bench_veh_0010_radius_is_loaded_from_existing_wheel_profile(self) -> None:
        self.assertAlmostEqual(self.provider.tire_radius_m, self.profile.front.tire_radius_m, places=15)
        self.assertAlmostEqual(self.provider.tire_radius_m, self.profile.rear.tire_radius_m, places=15)
        self.assertAlmostEqual(self.provider.tire_radius_m, 0.23241, places=15)
        self.assertEqual(self.provider.source.assumption_id, "ASM-VEH-0005")
        self.assertEqual(self.provider.source.equation_id, "EQ-VEH-0014")
        implementation = (ROOT / "src/pssd_vehicle/wufr_road_contact.py").read_text(encoding="utf-8")
        # The numeric source radius belongs to the frozen wheel-reference fixture, not implementation code.
        self.assertNotIn("0.23241", implementation)

    def test_bench_veh_0010_exact_circle_geometry_and_sign_invariance(self) -> None:
        center = (0.12, -0.34, 0.56)
        wheel_normal = (0.0, math.sqrt(0.5), math.sqrt(0.5))
        road_normal = (0.0, 0.0, 1.0)
        result = ideal_rigid_circle_contact(center, wheel_normal, road_normal, self.provider.tire_radius_m)
        radial = tuple(result.contact_point_m[i] - center[i] for i in range(3))
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in radial)), self.provider.tire_radius_m, places=12)
        self.assertAlmostEqual(sum(radial[i] * wheel_normal[i] for i in range(3)), 0.0, places=12)
        projected = tuple(road_normal[i] - sum(road_normal[j] * wheel_normal[j] for j in range(3)) * wheel_normal[i] for i in range(3))
        projected_norm = math.sqrt(sum(v * v for v in projected))
        expected_e = tuple(v / projected_norm for v in projected)
        for actual, expected in zip(result.radial_direction_to_center, expected_e):
            self.assertAlmostEqual(actual, expected, places=12)

        flipped = ideal_rigid_circle_contact(
            center,
            tuple(-v for v in wheel_normal),
            road_normal,
            self.provider.tire_radius_m,
        )
        for actual, expected in zip(flipped.contact_point_m, result.contact_point_m):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_bench_veh_0010_upright_wheel_limit(self) -> None:
        center = (1.0, 2.0, 3.0)
        result = ideal_rigid_circle_contact(
            center,
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            self.provider.tire_radius_m,
        )
        self.assertEqual(result.contact_point_m[:2], center[:2])
        self.assertAlmostEqual(result.contact_point_m[2], center[2] - self.provider.tire_radius_m, places=12)

    def test_bench_veh_0010_nominal_wufr_formula_outputs(self) -> None:
        expected = {
            (Axle.FRONT, Side.LEFT): (0.000159242280, 0.615984170, 0.0),
            (Axle.FRONT, Side.RIGHT): (0.000159242280, -0.615984170, 0.0),
            (Axle.REAR, Side.LEFT): (-0.000035395821, 0.603285406, 0.0),
            (Axle.REAR, Side.RIGHT): (-0.000035395821, -0.603285406, 0.0),
        }
        for identity, expected_point in expected.items():
            axle, side = identity
            nominal = build_nominal_wheel_reference(self.profile, axle, side)
            result = ideal_rigid_circle_contact(
                nominal.center_m,
                nominal.plane_normal,
                (0.0, 0.0, 1.0),
                self.provider.tire_radius_m,
            )
            self.assertAlmostEqual(result.contact_point_m[2], 0.0, places=12)
            for actual, target in zip(result.contact_point_m, expected_point):
                self.assertLessEqual(abs(actual - target), 2.0e-9)
            source_track_y = self.profile.axle(axle).half_track_m * (1.0 if side is Side.LEFT else -1.0)
            self.assertLessEqual(abs(result.contact_point_m[1] - source_track_y), 2.0e-6)
            self.assertGreater(abs(result.contact_point_m[0]), 1.0e-8)

    def test_bench_veh_0010_degenerate_projection_is_structured_failure(self) -> None:
        with self.assertRaises(WUFRRoadContactError) as context:
            ideal_rigid_circle_contact(
                (0.0, 0.0, 1.0),
                (0.0, 0.0, 1.0),
                (0.0, 0.0, 1.0),
                self.provider.tire_radius_m,
            )
        self.assertEqual(context.exception.code, WUFRRoadContactFailureCode.CONTACT_GEOMETRY_DEGENERATE)

    def test_bench_veh_0010_contact_api_excludes_unreviewed_tire_inputs(self) -> None:
        parameters = set(inspect.signature(ideal_rigid_circle_contact).parameters)
        self.assertEqual(
            parameters,
            {
                "wheel_center_m",
                "wheel_plane_normal",
                "road_normal",
                "radius_m",
                "unit_normal_tolerance",
                "projection_min",
            },
        )
        for forbidden in ("width", "pressure", "load", "temperature", "speed", "deflection", "contact_patch"):
            self.assertNotIn(forbidden, parameters)


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

    def test_bench_veh_0009_nominal_roots_contact_coefficients_and_gravity(self) -> None:
        result = self.nominal
        self.assertTrue(result.ok, result.message)
        assert result.compatibility.wheel_coordinates_m is not None
        self.assertLessEqual(max(abs(v) for v in result.compatibility.wheel_coordinates_m), 2.0e-8)
        self.assertEqual(
            tuple(root.corner_id for root in result.compatibility.roots),
            ("front_left", "front_right", "rear_left", "rear_right"),
        )
        self.assertLessEqual(
            max(abs(root.state.road_gap_m) for root in result.compatibility.roots if root.state is not None),
            2.0e-9,
        )
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
        front_steering = [
            root.state.point_state.steering_rotation_rad
            for root in combined.roots[:2]
            if root.state is not None
        ]
        self.assertEqual(len(front_steering), 2)
        self.assertGreater(max(abs(float(v)) for v in front_steering), 1.0e-6)

    def test_contact_and_gravity_are_evaluated_from_point_virtual_work(self) -> None:
        result = self.nominal
        self.assertTrue(result.ok, result.message)
        masses = {item.corner_id: item for item in self.gravity.unsprung}
        h = 7.5e-5
        for root, coefficient, gravity_force in zip(
            result.compatibility.roots,
            result.contact_coefficients,
            result.unsprung_gravity_forces,
        ):
            assert root.wheel_coordinate_m is not None
            assert coefficient.value is not None
            assert gravity_force.value is not None
            def direct(step: float) -> tuple[float, float]:
                plus = evaluate_corner_road_state(
                    self.provider,
                    self.nominal_pose,
                    root.corner_id,
                    root.wheel_coordinate_m + step,
                )
                minus = evaluate_corner_road_state(
                    self.provider,
                    self.nominal_pose,
                    root.corner_id,
                    root.wheel_coordinate_m - step,
                )
                direct_c = (plus.contact_road.position_m[2] - minus.contact_road.position_m[2]) / (2.0 * step)
                mass = masses[root.corner_id]
                u_plus = mass.mass_kg * self.gravity.g_mps2 * plus.wheel_center_road.position_m[2]
                u_minus = mass.mass_kg * self.gravity.g_mps2 * minus.wheel_center_road.position_m[2]
                direct_q = -(u_plus - u_minus) / (2.0 * step)
                return direct_c, direct_q

            coarse_c, coarse_q = direct(2.0 * h)
            fine_c, fine_q = direct(h)
            direct_c = (4.0 * fine_c - coarse_c) / 3.0
            direct_q = (4.0 * fine_q - coarse_q) / 3.0
            self.assertLessEqual(abs(coefficient.value - direct_c), 1.0e-8 + 1.0e-6 * max(1.0, abs(direct_c)))
            self.assertLessEqual(abs(gravity_force.value - direct_q), 1.0e-6)

    def test_out_of_domain_body_pose_fails_without_coordinate_clipping(self) -> None:
        outside = solve_road_compatibility(self.provider, replace(self.nominal_pose, z_s_m=0.050))
        self.assertFalse(outside.ok)
        self.assertEqual(outside.failure_code, WUFRRoadContactFailureCode.BODY_POSE_OUTSIDE_DOMAIN)


if __name__ == "__main__":
    unittest.main()
