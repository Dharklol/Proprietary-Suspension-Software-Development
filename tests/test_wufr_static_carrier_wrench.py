from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension.geometry import Axle
from pssd_vehicle.force_coordinates import BodyPose, assemble_wrenches
from pssd_vehicle.wufr_static_carrier_wrench import (
    CORNER_ORDER,
    build_level1_to_road_transform,
    evaluate_wufr_static_carrier_wrenches,
    load_wufr_static_carrier_wrench_provider,
    pullback_road_wrench_to_level1,
    pushforward_level1_wrench_to_road,
    transform_level1_point_to_road,
)


ROOT = Path(__file__).resolve().parents[1]


def _provider():
    return load_wufr_static_carrier_wrench_provider(
        source_path=ROOT / "data_catalog/wufr27_static_carrier_wrench_v0.toml",
        static_equilibrium_result_path=ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json",
        static_equilibrium_source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v1.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


class WufrStaticCarrierWrenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = _provider()
        cls.result = evaluate_wufr_static_carrier_wrenches(cls.provider)
        if not cls.result.ok:
            raise AssertionError(f"carrier-wrench setup failed: {cls.result.failure_code} {cls.result.message}")

    def test_four_complete_static_case_wrenches_are_returned_in_canonical_order(self) -> None:
        result = self.result
        self.assertEqual(tuple(corner.corner_id for corner in result.corners), CORNER_ORDER)
        self.assertTrue(result.complete_for_authorized_static_gravity_case)
        self.assertFalse(result.complete_physical_hardware_wrench)
        self.assertFalse(result.maneuver_complete)
        self.assertFalse(result.installed_as_built_authority)
        self.assertFalse(result.integrated_level1_linkage_result_authority)
        self.assertFalse(result.hidden_balancing_wrench_used)

    def test_per_corner_force_is_road_reaction_plus_exact_unsprung_gravity(self) -> None:
        for corner in self.result.corners:
            self.assertTrue(corner.ok, corner.message)
            assert corner.road_force_wrench is not None
            assert corner.unsprung_gravity_wrench is not None
            assert corner.road_resultant is not None
            expected = tuple(
                corner.road_force_wrench.force_N[index]
                + corner.unsprung_gravity_wrench.force_N[index]
                for index in range(3)
            )
            for actual, target in zip(corner.road_resultant.resultant_force_N, expected):
                self.assertAlmostEqual(actual, target, delta=1.0e-12)
            self.assertEqual(corner.road_force_wrench.free_couple_Nm, (0.0, 0.0, 0.0))
            self.assertEqual(corner.unsprung_gravity_wrench.free_couple_Nm, (0.0, 0.0, 0.0))
            self.assertAlmostEqual(corner.unsprung_gravity_wrench.force_N[2], -49.05, delta=1.0e-12)
            self.assertAlmostEqual(
                corner.road_resultant.resultant_force_N[2],
                float(corner.road_reaction_N) - 49.05,
                delta=1.0e-12,
            )

    def test_per_corner_moment_matches_independent_cross_product_assembly(self) -> None:
        for corner in self.result.corners:
            assert corner.carrier_reference_road is not None
            assert corner.road_force_wrench is not None
            assert corner.unsprung_gravity_wrench is not None
            assert corner.road_resultant is not None
            road_moment = _cross(
                _sub(
                    corner.road_force_wrench.application_point.position_m,
                    corner.carrier_reference_road.position_m,
                ),
                corner.road_force_wrench.force_N,
            )
            gravity_moment = _cross(
                _sub(
                    corner.unsprung_gravity_wrench.application_point.position_m,
                    corner.carrier_reference_road.position_m,
                ),
                corner.unsprung_gravity_wrench.force_N,
            )
            expected = tuple(road_moment[index] + gravity_moment[index] for index in range(3))
            for actual, target in zip(corner.road_resultant.resultant_moment_Nm, expected):
                self.assertAlmostEqual(actual, target, delta=1.0e-12)

    def test_carrier_reference_is_exact_current_upper_lower_midpoint(self) -> None:
        for corner in self.result.corners:
            assert corner.upper_spherical_level1_m is not None
            assert corner.lower_spherical_level1_m is not None
            assert corner.carrier_reference_level1_m is not None
            expected = tuple(
                0.5
                * (
                    corner.upper_spherical_level1_m[index]
                    + corner.lower_spherical_level1_m[index]
                )
                for index in range(3)
            )
            for actual, target in zip(corner.carrier_reference_level1_m, expected):
                self.assertAlmostEqual(actual, target, delta=1.0e-14)

    def test_road_and_level1_wrenches_are_exact_rigid_representations(self) -> None:
        for corner in self.result.corners:
            assert corner.level1_wrench is not None
            assert corner.road_resultant is not None
            self.assertEqual(
                corner.level1_wrench.frame_id,
                "WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL",
            )
            self.assertTrue(corner.level1_wrench.complete)
            self.assertLessEqual(float(corner.round_trip_force_residual_N), 1.0e-10)
            self.assertLessEqual(float(corner.round_trip_moment_residual_Nm), 1.0e-10)
            self.assertGreater(
                max(abs(value) for value in corner.level1_wrench.force_N[:2]),
                0.0,
                "nonzero roll/pitch must not be erased by assuming road/body frame identity",
            )

    def test_bounded_synthetic_nonzero_pose_preserves_frame_round_trip(self) -> None:
        nominal = self.provider.equilibrium_provider.nominal_body_pose()
        pose = BodyPose(
            inertial_frame_id=nominal.inertial_frame_id,
            inertial_origin_id=nominal.inertial_origin_id,
            body_frame_id=nominal.body_frame_id,
            body_origin_id=nominal.body_origin_id,
            body_origin_position_m=nominal.body_origin_position_m,
            z_s_m=0.004,
            phi_rad=0.012,
            theta_rad=-0.016,
            psi_rad=0.0,
            authority="BENCH-VEH-0015 bounded synthetic nonzero pose",
        )
        transform = build_level1_to_road_transform(self.provider, pose, Axle.FRONT)
        point_level1 = (0.031, 0.544, 0.207)
        point_road = transform_level1_point_to_road(transform, point_level1)
        self.assertTrue(all(math.isfinite(value) for value in point_road))

        force_level1 = (117.0, -43.0, 612.0)
        moment_level1 = (8.2, -3.1, 1.7)
        force_road, moment_road = pushforward_level1_wrench_to_road(
            transform, force_level1, moment_level1
        )
        recovered_force, recovered_moment = pullback_road_wrench_to_level1(
            transform, force_road, moment_road
        )
        for actual, target in zip(recovered_force, force_level1):
            self.assertAlmostEqual(actual, target, delta=1.0e-12)
        for actual, target in zip(recovered_moment, moment_level1):
            self.assertAlmostEqual(actual, target, delta=1.0e-12)
        self.assertGreater(
            max(abs(force_road[i] - force_level1[i]) for i in range(3)),
            1.0e-3,
            "bounded roll/pitch must materially rotate the wrench components",
        )

    def test_reference_change_preserves_force_and_exact_moment_transport(self) -> None:
        corner = self.result.corners[0]
        assert corner.road_force_wrench is not None
        assert corner.unsprung_gravity_wrench is not None
        assert corner.carrier_reference_road is not None
        assert corner.road_resultant is not None
        moved = type(corner.carrier_reference_road)(
            point_id="moved_reference",
            frame_id=corner.carrier_reference_road.frame_id,
            origin_id=corner.carrier_reference_road.origin_id,
            position_m=tuple(
                corner.carrier_reference_road.position_m[index]
                + (0.1, -0.05, 0.03)[index]
                for index in range(3)
            ),
            role="synthetic alternate reference",
            source_id=corner.carrier_reference_road.source_id,
            configuration_id=corner.carrier_reference_road.configuration_id,
            authority="BENCH-VEH-0015",
            fixed_role="road_fixed",
        )
        moved_result = assemble_wrenches(
            (corner.road_force_wrench, corner.unsprung_gravity_wrench), moved
        )
        self.assertEqual(moved_result.resultant_force_N, corner.road_resultant.resultant_force_N)
        shift = _sub(corner.carrier_reference_road.position_m, moved.position_m)
        expected = tuple(
            corner.road_resultant.resultant_moment_Nm[index]
            + _cross(shift, corner.road_resultant.resultant_force_N)[index]
            for index in range(3)
        )
        for actual, target in zip(moved_result.resultant_moment_Nm, expected):
            self.assertAlmostEqual(actual, target, delta=1.0e-12)

    def test_four_corner_reconstruction_matches_accepted_physical_closure(self) -> None:
        result = self.result
        self.assertLessEqual(float(result.maximum_force_residual_N), 1.0e-6)
        self.assertLessEqual(float(result.maximum_moment_residual_Nm), 1.0e-6)
        self.assertLessEqual(float(result.accepted_force_match_residual_N), 1.0e-10)
        self.assertLessEqual(float(result.accepted_moment_match_residual_Nm), 1.0e-10)
        assert result.reconstruction_at_road_origin is not None
        for actual, target in zip(
            result.reconstruction_at_road_origin.resultant_force_N,
            result.accepted_closure_force_N,
        ):
            self.assertAlmostEqual(actual, target, delta=1.0e-10)
        for actual, target in zip(
            result.reconstruction_at_road_origin.resultant_moment_Nm,
            result.accepted_closure_moment_Nm,
        ):
            self.assertAlmostEqual(actual, target, delta=1.0e-10)


if __name__ == "__main__":
    unittest.main()
