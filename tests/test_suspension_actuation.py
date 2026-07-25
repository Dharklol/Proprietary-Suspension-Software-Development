from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest

from pssd_suspension import (
    ActuationAttachment,
    ActuationFailureCode,
    ActuationGeometry,
    ActuationSolverConfig,
    ActuationStatus,
    PhysicalStateSolverConfig,
    SuspensionPoint,
    build_nominal_wheel_reference,
    evaluate_local_derivative,
    ideal_coilover_state,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    solve_actuation_q_L_state,
    solve_body_vertical_actuation_state,
    solve_rocker_closure,
)


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
ACTUATION_FIXTURE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml"


def _load(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _point(name: str, xyz: tuple[float, float, float]) -> SuspensionPoint:
    mm = tuple(1000.0 * value for value in xyz)
    return SuspensionPoint(source_name=name, source_position_mm=mm, position_m=xyz)


def _synthetic_actuation() -> ActuationGeometry:
    return ActuationGeometry(
        outboard_attachment=_point("arm", (2.0, 0.0, 0.0)),
        chassis_attachment=_point("damper_chassis", (0.0, 2.0, 0.0)),
        rocker_axis_reference=_point("axis", (0.0, 0.0, 1.0)),
        rocker_pivot=_point("pivot", (0.0, 0.0, 0.0)),
        rocker_rod_point=_point("rod", (1.0, 0.0, 0.0)),
        rocker_coil_point=_point("coil", (0.0, 1.0, 0.0)),
        attachment=ActuationAttachment.UPPER_ARM,
    )


class SuspensionActuationImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_optimumk_geometry_snapshot(GEOMETRY_PATH)
        cls.wheel_profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE_PATH)
        cls.fixture = _load(ACTUATION_FIXTURE_PATH)

    def test_analytical_rocker_closure_selects_continuation_root(self) -> None:
        actuation = _synthetic_actuation()
        theta_expected = 0.4
        rod = (math.cos(theta_expected), math.sin(theta_expected), 0.0)
        current_arm = (rod[0] + 1.0, rod[1], 0.0)
        closure = solve_rocker_closure(
            actuation,
            current_arm,
            predecessor_theta_R_rad=theta_expected - 0.05,
        )
        self.assertTrue(closure.ok, closure.message)
        self.assertAlmostEqual(float(closure.theta_R_rad), theta_expected, places=12)
        self.assertLessEqual(abs(float(closure.rod_length_residual_m)), 1.0e-12)

        length, displacement, coil = ideal_coilover_state(actuation, theta_expected)
        expected_coil = (-math.sin(theta_expected), math.cos(theta_expected), 0.0)
        expected_length = math.dist(expected_coil, (0.0, 2.0, 0.0))
        self.assertAlmostEqual(length, expected_length, places=12)
        self.assertAlmostEqual(displacement, expected_length - 1.0, places=12)
        for got, want in zip(coil, expected_coil):
            self.assertAlmostEqual(got, want, places=12)

    def test_analytical_unreachable_and_ambiguous_roots_fail_explicitly(self) -> None:
        actuation = _synthetic_actuation()
        unreachable = solve_rocker_closure(actuation, (5.0, 0.0, 0.0))
        self.assertEqual(unreachable.status, ActuationStatus.FAILURE)
        self.assertEqual(unreachable.failure_code, ActuationFailureCode.NO_ROCKER_ROOT)

        # For current arm [1,1,0] and unit rocker/rod geometry, theta=0 and
        # theta=pi/2 are both exact closure roots.  A predecessor at pi/4 gives
        # no unique continuation choice and must not be silently resolved.
        ambiguous = solve_rocker_closure(
            actuation,
            (1.0, 1.0, 0.0),
            predecessor_theta_R_rad=math.pi / 4.0,
        )
        self.assertEqual(ambiguous.status, ActuationStatus.FAILURE)
        self.assertEqual(ambiguous.failure_code, ActuationFailureCode.ROCKER_BRANCH_AMBIGUITY)
        self.assertGreaterEqual(len(ambiguous.candidate_roots_rad), 2)

    def test_degenerate_rocker_axis_fails(self) -> None:
        actuation = _synthetic_actuation()
        degenerate = ActuationGeometry(
            outboard_attachment=actuation.outboard_attachment,
            chassis_attachment=actuation.chassis_attachment,
            rocker_axis_reference=_point("axis", (0.0, 0.0, 0.0)),
            rocker_pivot=actuation.rocker_pivot,
            rocker_rod_point=actuation.rocker_rod_point,
            rocker_coil_point=actuation.rocker_coil_point,
            attachment=actuation.attachment,
        )
        result = solve_rocker_closure(degenerate, (2.0, 0.0, 0.0))
        self.assertEqual(result.failure_code, ActuationFailureCode.DEGENERATE_ROCKER_AXIS)

    def test_signed_derivative_and_conditioned_reciprocal(self) -> None:
        derivative = evaluate_local_derivative(
            z_center_m=0.0,
            delta_l_center_m=0.0,
            z_minus_m=-0.1,
            delta_l_minus_m=0.02,
            z_plus_m=0.1,
            delta_l_plus_m=-0.02,
        )
        self.assertTrue(derivative.ok)
        self.assertAlmostEqual(float(derivative.rho_dw), -0.2, places=12)
        self.assertAlmostEqual(float(derivative.rho_wd), -5.0, places=12)
        self.assertEqual(derivative.method, "centered_physical_wheel_coordinate")

        zero = evaluate_local_derivative(
            z_center_m=0.0,
            delta_l_center_m=0.0,
            z_minus_m=-0.1,
            delta_l_minus_m=0.0,
            z_plus_m=0.1,
            delta_l_plus_m=0.0,
        )
        self.assertTrue(zero.ok)
        self.assertEqual(zero.rho_dw, 0.0)
        self.assertFalse(zero.reciprocal_available)
        self.assertIsNone(zero.rho_wd)

    def test_wufr_nominal_front_and_rear_match_source_lengths(self) -> None:
        for axle in ("front", "rear"):
            for side in ("left", "right"):
                corner = self.geometry.corner(axle, side)
                nominal = build_nominal_wheel_reference(self.wheel_profile, axle, side)
                state = solve_actuation_q_L_state(
                    corner,
                    nominal,
                    0.0,
                    geometry_id=self.geometry.geometry_id,
                    source_authority=self.geometry.authority,
                )
                self.assertTrue(state.ok, f"{axle} {side}: {state.message}")
                self.assertEqual(state.owning_arm, self.fixture[axle]["actuation_attachment"])
                self.assertLessEqual(
                    abs(float(state.current_push_pull_length_m) - 0.001 * self.fixture[axle]["nominal_push_pull_length_mm"]),
                    2.0e-6,
                )
                self.assertLessEqual(
                    abs(float(state.current_coilover_length_m) - 0.001 * self.fixture[axle]["nominal_coilover_length_mm"]),
                    2.0e-6,
                )
                self.assertLessEqual(abs(float(state.rod_length_residual_m)), 1.0e-12)
                self.assertAlmostEqual(float(state.delta_L_d_m), 0.0, places=12)
                self.assertFalse(state.installed_limits_evaluated)

    def _check_source_branch(self, axle: str, side: str, indices: list[int]) -> None:
        corner = self.geometry.corner(axle, side)
        nominal = build_nominal_wheel_reference(self.wheel_profile, axle, side)
        predecessor = None
        length_tol = self.fixture["tolerances"]["implementation_length_match_m"]
        displacement_tol = self.fixture["tolerances"]["implementation_displacement_match_m"]
        rod_tol = self.fixture["tolerances"]["rod_length_residual_m"]
        q_key = f"{axle}_{side}_q_L_deg"
        for index in indices:
            source = self.fixture["states"][index]
            state = solve_actuation_q_L_state(
                corner,
                nominal,
                math.radians(source[q_key]),
                predecessor=predecessor,
                geometry_id=self.geometry.geometry_id,
                source_authority=self.geometry.authority,
            )
            self.assertTrue(state.ok, f"{axle} {side} heave={source['heave_mm']}: {state.message}")
            self.assertLessEqual(
                abs(float(state.current_coilover_length_m) - 0.001 * source[f"{axle}_coilover_length_mm"]),
                length_tol,
            )
            self.assertLessEqual(
                abs(float(state.delta_L_d_m) - 0.001 * source[f"{axle}_coilover_displacement_mm"]),
                displacement_tol,
            )
            self.assertLessEqual(abs(float(state.rod_length_residual_m)), rod_tol)
            predecessor = state

    def test_wufr_all_eleven_states_front_rear_and_bilateral(self) -> None:
        # Each branch begins from nominal and continues outward so the rocker and
        # upstream suspension solvers retain explicit branch history.
        negative_heave_from_nominal = [5, 4, 3, 2, 1, 0]
        positive_heave_from_nominal = [5, 6, 7, 8, 9, 10]
        for axle in ("front", "rear"):
            for side in ("left", "right"):
                self._check_source_branch(axle, side, negative_heave_from_nominal)
                self._check_source_branch(axle, side, positive_heave_from_nominal)

    def test_physical_wheel_derivative_is_signed_and_not_optimumk_motion_ratio(self) -> None:
        corner = self.geometry.corner("front", "left")
        nominal = build_nominal_wheel_reference(self.wheel_profile, "front", "left")
        physical = PhysicalStateSolverConfig(
            q_L_min_rad=math.radians(-4.0),
            q_L_max_rad=math.radians(4.0),
            displacement_tolerance_m=2.0e-9,
            q_L_tolerance_rad=2.0e-9,
        )
        result = solve_body_vertical_actuation_state(
            corner,
            nominal,
            0.0,
            physical,
            actuation_config=ActuationSolverConfig(derivative_step_m=1.0e-4),
            geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,
        )
        self.assertTrue(result.ok, result.message)
        self.assertIsNotNone(result.rho_dw)
        self.assertLess(float(result.rho_dw), 0.0)
        self.assertEqual(result.derivative_method, "centered_physical_wheel_coordinate")
        historical = self.fixture["states"][5]["front_source_motion_ratio_heave"]
        self.assertGreater(historical, 0.0)
        self.assertGreater(abs(float(result.rho_dw) - historical), 0.1)


if __name__ == "__main__":
    unittest.main()
