from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import unittest

from pssd_suspension.wufr_zbar import (
    ZBarAxleFixture,
    ZBarForceResult,
    ZBarMechanismResult,
    ZBarStatus,
    evaluate_two_arm_force,
    load_wufr_zbar_fixture,
)
from pssd_suspension.wufr_zbar_link_force import (
    ZBarLinkForceFailureCode,
    ZBarLinkForceStatus,
    recover_single_link_force,
    recover_wufr_zbar_physical_link_forces,
)
from pssd_suspension.wufr_zbar_nominal import solve_nominal_zbar_mechanism


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml"


def _norm(values: tuple[float, float, float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(a[i] * b[i] for i in range(3))


class WufrZBarPhysicalLinkForceTests(unittest.TestCase):
    def test_nominal_front_and_rear_recover_zero_physical_link_force(self) -> None:
        for axle in ("front", "rear"):
            with self.subTest(axle=axle):
                fixture = load_wufr_zbar_fixture(FIXTURE_PATH, axle)
                state = solve_nominal_zbar_mechanism(fixture, 0.0, 0.0)
                self.assertTrue(state.ok, state.message)
                force = evaluate_two_arm_force(state, setting=1, stiffness_N_per_m=280000.0)
                self.assertTrue(force.ok, force.message)
                result = recover_wufr_zbar_physical_link_forces(fixture, state, force)
                self.assertEqual(result.status, ZBarLinkForceStatus.SUCCESS, result.message)
                assert result.left is not None and result.right is not None
                for side in (result.left, result.right):
                    self.assertAlmostEqual(side.axial_force_N, 0.0, delta=1.0e-8)
                    self.assertAlmostEqual(side.physical_rocker_torque_Nm, 0.0, delta=1.0e-9)
                    self.assertAlmostEqual(_norm(side.force_on_rocker_N), 0.0, delta=1.0e-8)

    def test_front_differential_state_recovers_signed_axial_forces_and_torque(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE_PATH, "front")
        state = solve_nominal_zbar_mechanism(fixture, 0.01, -0.01)
        self.assertTrue(state.ok, state.message)
        force = evaluate_two_arm_force(state, setting=3, stiffness_N_per_m=400000.0)
        self.assertTrue(force.ok, force.message)
        result = recover_wufr_zbar_physical_link_forces(fixture, state, force)
        self.assertTrue(result.ok, result.message)
        assert result.left is not None and result.right is not None
        for side in (result.left, result.right):
            self.assertGreater(abs(side.projection_u_dot_n), 1.0e-6)
            self.assertAlmostEqual(_norm(side.link_axis_blade_to_rocker), 1.0, places=12)
            self.assertAlmostEqual(_norm(side.blade_transverse_unit), 1.0, places=12)
            self.assertAlmostEqual(side.axial_force_N * side.projection_u_dot_n, side.elastic_transverse_force_N, delta=1.0e-8)
            for a, b in zip(side.force_on_rocker_N, side.force_on_blade_N):
                self.assertAlmostEqual(a, -b, delta=1.0e-12)
            self.assertAlmostEqual(side.rocker_torque_residual_Nm or 0.0, 0.0, delta=1.0e-8)
        self.assertFalse(math.isclose(result.left.axial_force_N, 0.0, abs_tol=1.0e-8))
        self.assertFalse(math.isclose(result.right.axial_force_N, 0.0, abs_tol=1.0e-8))

    def test_rear_asymmetric_state_reproduces_existing_generalized_rocker_torque(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE_PATH, "rear")
        state = solve_nominal_zbar_mechanism(fixture, 0.008, -0.006)
        self.assertTrue(state.ok, state.message)
        force = evaluate_two_arm_force(state, setting=2, stiffness_N_per_m=300000.0)
        self.assertTrue(force.ok, force.message)
        result = recover_wufr_zbar_physical_link_forces(fixture, state, force)
        self.assertTrue(result.ok, result.message)
        assert result.left is not None and result.right is not None
        self.assertEqual(len(force.generalized_rocker_torque_Nm), 2)
        self.assertAlmostEqual(result.left.physical_rocker_torque_Nm, force.generalized_rocker_torque_Nm[0], delta=1.0e-8)
        self.assertAlmostEqual(result.right.physical_rocker_torque_Nm, force.generalized_rocker_torque_Nm[1], delta=1.0e-8)

    def test_force_vectors_are_collinear_with_current_link_axis(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE_PATH, "front")
        state = solve_nominal_zbar_mechanism(fixture, 0.01, -0.01)
        force = evaluate_two_arm_force(state, setting=3, stiffness_N_per_m=400000.0)
        result = recover_wufr_zbar_physical_link_forces(fixture, state, force)
        self.assertTrue(result.ok, result.message)
        assert result.left and result.right
        for side in (result.left, result.right):
            cross = (
                side.link_axis_blade_to_rocker[1] * side.force_on_rocker_N[2] - side.link_axis_blade_to_rocker[2] * side.force_on_rocker_N[1],
                side.link_axis_blade_to_rocker[2] * side.force_on_rocker_N[0] - side.link_axis_blade_to_rocker[0] * side.force_on_rocker_N[2],
                side.link_axis_blade_to_rocker[0] * side.force_on_rocker_N[1] - side.link_axis_blade_to_rocker[1] * side.force_on_rocker_N[0],
            )
            self.assertLessEqual(_norm(cross), 1.0e-9)

    def test_degenerate_projection_fails_without_substituting_generalized_force(self) -> None:
        result = recover_single_link_force(
            side="synthetic",
            blade_tip_m=(0.0, 0.0, 0.0),
            rocker_pickup_m=(1.0, 0.0, 0.0),
            blade_transverse_unit=(0.0, 1.0, 0.0),
            elastic_transverse_force_N=100.0,
            rocker_pivot_m=(0.0, 0.0, 0.0),
            rocker_axis_unit=(0.0, 0.0, 1.0),
            nominal_link_length_m=1.0,
            expected_generalized_rocker_torque_Nm=None,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, ZBarLinkForceFailureCode.DEGENERATE_LINK_PROJECTION)
        self.assertIsNone(result.side_force)

    def test_upstream_failure_and_source_mismatch_are_fail_closed(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE_PATH, "front")
        good_state = solve_nominal_zbar_mechanism(fixture, 0.01, -0.01)
        good_force = evaluate_two_arm_force(good_state, setting=1, stiffness_N_per_m=280000.0)
        failed_state = ZBarMechanismResult(ZBarStatus.FAILURE, axle="front", message="synthetic upstream failure")
        result = recover_wufr_zbar_physical_link_forces(fixture, failed_state, good_force)
        self.assertEqual(result.failure_code, ZBarLinkForceFailureCode.UPSTREAM_MECHANISM_FAILURE)

        bad_fixture = replace(fixture, axle="rear")
        mismatch = recover_wufr_zbar_physical_link_forces(bad_fixture, good_state, good_force)
        self.assertEqual(mismatch.failure_code, ZBarLinkForceFailureCode.SOURCE_MISMATCH)

    def test_compression_is_preserved_as_negative_when_projection_and_elastic_action_require_it(self) -> None:
        result = recover_single_link_force(
            side="synthetic",
            blade_tip_m=(0.0, 0.0, 0.0),
            rocker_pickup_m=(1.0, 0.0, 0.0),
            blade_transverse_unit=(1.0, 0.0, 0.0),
            elastic_transverse_force_N=-25.0,
            rocker_pivot_m=(0.0, 0.0, 0.0),
            rocker_axis_unit=(0.0, 0.0, 1.0),
            nominal_link_length_m=1.0,
            expected_generalized_rocker_torque_Nm=0.0,
        )
        self.assertTrue(result.ok, result.message)
        assert result.side_force is not None
        self.assertAlmostEqual(result.side_force.axial_force_N, -25.0)
        self.assertLess(result.side_force.axial_force_N, 0.0)
        self.assertAlmostEqual(_dot(result.side_force.force_on_blade_N, (1.0, 0.0, 0.0)), -25.0)


if __name__ == "__main__":
    unittest.main()
