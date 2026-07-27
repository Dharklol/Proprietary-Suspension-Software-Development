from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension import (
    PhysicalStateSolverConfig,
    build_nominal_wheel_reference,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
)
from pssd_suspension.wufr_zbar import load_wufr_zbar_fixture
from pssd_suspension.wufr_zbar_wheel import (
    RockerWheelDerivativeConfig,
    ZBarWheelStatus,
    solve_rocker_wheel_map,
    solve_wufr_zbar_wheel_state,
)

ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
ZBAR_FIXTURE_PATH = ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml"


class WufrZBarWheelCoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_optimumk_geometry_snapshot(GEOMETRY_PATH)
        cls.wheel_profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE_PATH)
        cls.physical_solver = PhysicalStateSolverConfig(
            q_L_min_rad=math.radians(-4.0),
            q_L_max_rad=math.radians(4.0),
            displacement_tolerance_m=2.0e-9,
            q_L_tolerance_rad=2.0e-9,
        )
        cls.derivative_config = RockerWheelDerivativeConfig(
            step_m=1.0e-4,
            second_step_m=5.0e-5,
            agreement_tolerance_rad_per_m=5.0e-2,
        )

    def _axle_inputs(self, axle: str):
        fixture = load_wufr_zbar_fixture(ZBAR_FIXTURE_PATH, axle)
        left_corner = self.geometry.corner(axle, "left")
        right_corner = self.geometry.corner(axle, "right")
        left_nominal = build_nominal_wheel_reference(self.wheel_profile, axle, "left")
        right_nominal = build_nominal_wheel_reference(self.wheel_profile, axle, "right")
        return fixture, left_corner, right_corner, left_nominal, right_nominal

    def _solve(self, axle: str, z_left: float, z_right: float, *, setting: int = 1, with_jacobian: bool = True):
        fixture, left_corner, right_corner, left_nominal, right_nominal = self._axle_inputs(axle)
        return solve_wufr_zbar_wheel_state(
            fixture,
            left_corner,
            right_corner,
            left_nominal,
            right_nominal,
            z_left,
            z_right,
            self.physical_solver,
            setting=setting,
            derivative_config=self.derivative_config,
            geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,
            with_wheel_jacobian=with_jacobian,
        )

    def test_nominal_front_and_rear_map_to_zero_wheel_force(self) -> None:
        for axle in ("front", "rear"):
            result = self._solve(axle, 0.0, 0.0, setting=1)
            self.assertEqual(result.status, ZBarWheelStatus.SUCCESS, result.message)
            self.assertEqual(result.coordinate_order, ("delta_z_wc_body_left_m", "delta_z_wc_body_right_m"))
            self.assertEqual(result.coordinate_units, ("m", "m"))
            self.assertEqual(len(result.J_d_wheel), 2)
            self.assertEqual(len(result.generalized_wheel_force_N), 2)
            self.assertAlmostEqual(result.generalized_wheel_force_N[0], 0.0, places=7)
            self.assertAlmostEqual(result.generalized_wheel_force_N[1], 0.0, places=7)
            self.assertIsNotNone(result.left_map)
            self.assertIsNotNone(result.right_map)
            self.assertIsNotNone(result.left_map.dtheta_R_dz_wc_body_rad_per_m)
            self.assertIsNotNone(result.right_map.dtheta_R_dz_wc_body_rad_per_m)
            self.assertLess(result.left_map.derivative_disagreement_rad_per_m or 0.0, 5.0e-2)
            self.assertLess(result.right_map.derivative_disagreement_rad_per_m or 0.0, 5.0e-2)

    def test_rocker_over_wheel_derivative_is_signed_and_two_step_checked(self) -> None:
        fixture, left_corner, _, left_nominal, _ = self._axle_inputs("front")
        _ = fixture
        result = solve_rocker_wheel_map(
            left_corner,
            left_nominal,
            0.0,
            self.physical_solver,
            derivative_config=self.derivative_config,
            geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,
        )
        self.assertTrue(result.ok, result.message)
        self.assertIsNotNone(result.dtheta_R_dz_wc_body_rad_per_m)
        self.assertNotEqual(result.dtheta_R_dz_wc_body_rad_per_m, 0.0)
        self.assertEqual(result.derivative_method, "centered_physical_wheel_coordinate")
        self.assertIsNotNone(result.derivative_step_m)
        self.assertIsNotNone(result.derivative_second_step_m)
        self.assertLess(result.derivative_second_step_m or math.inf, result.derivative_step_m or 0.0)

    def test_chain_rule_matches_rocker_torque_times_local_rocker_derivative(self) -> None:
        result = self._solve("front", 0.002, -0.0015, setting=3)
        self.assertTrue(result.ok, result.message)
        assert result.left_map is not None and result.right_map is not None and result.force is not None
        self.assertEqual(len(result.force.generalized_rocker_torque_Nm), 2)
        rho_l = result.left_map.dtheta_R_dz_wc_body_rad_per_m
        rho_r = result.right_map.dtheta_R_dz_wc_body_rad_per_m
        assert rho_l is not None and rho_r is not None
        expected = (
            result.force.generalized_rocker_torque_Nm[0] * rho_l,
            result.force.generalized_rocker_torque_Nm[1] * rho_r,
        )
        for actual, target in zip(result.generalized_wheel_force_N, expected):
            self.assertTrue(math.isclose(actual, target, rel_tol=1.0e-12, abs_tol=1.0e-10), (actual, target))

    def test_wheel_force_matches_independent_total_energy_gradient(self) -> None:
        axle = "rear"
        z_left, z_right = 0.0015, -0.0010
        center = self._solve(axle, z_left, z_right, setting=2)
        self.assertTrue(center.ok, center.message)
        h = 2.0e-5
        numerical = []
        for index in (0, 1):
            plus = [z_left, z_right]
            minus = [z_left, z_right]
            plus[index] += h
            minus[index] -= h
            state_plus = self._solve(axle, plus[0], plus[1], setting=2, with_jacobian=False)
            state_minus = self._solve(axle, minus[0], minus[1], setting=2, with_jacobian=False)
            self.assertTrue(state_plus.ok, state_plus.message)
            self.assertTrue(state_minus.ok, state_minus.message)
            assert state_plus.force is not None and state_minus.force is not None
            assert state_plus.force.stored_energy_J is not None and state_minus.force.stored_energy_J is not None
            numerical.append(-(state_plus.force.stored_energy_J - state_minus.force.stored_energy_J) / (2.0 * h))
        self.assertEqual(len(center.generalized_wheel_force_N), 2)
        for analytic, numeric in zip(center.generalized_wheel_force_N, numerical):
            self.assertTrue(math.isclose(analytic, numeric, rel_tol=5.0e-3, abs_tol=2.0e-1), (analytic, numeric))

    def test_high_level_provider_uses_frozen_setting_stiffness(self) -> None:
        result = self._solve("front", 0.001, -0.001, setting=5)
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.stiffness_N_per_m, 2300000.0)
        assert result.force is not None
        self.assertEqual(result.force.stiffness_N_per_m, 2300000.0)


if __name__ == "__main__":
    unittest.main()
