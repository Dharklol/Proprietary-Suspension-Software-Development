from __future__ import annotations
import math
from pathlib import Path
import unittest

from pssd_suspension.wufr_zbar import (
    ZBarFailureCode,
    ZBarStatus,
    evaluate_two_arm_force,
    load_wufr_zbar_fixture,
)
from pssd_suspension.wufr_zbar_nominal import solve_nominal_zbar_mechanism

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml"


class WufrZBarImplementationTests(unittest.TestCase):
    def test_nominal_front_and_rear_close_at_zero_energy(self) -> None:
        for axle in ("front", "rear"):
            fixture = load_wufr_zbar_fixture(FIXTURE, axle)
            result = solve_nominal_zbar_mechanism(fixture, 0.0, 0.0)
            self.assertEqual(result.status, ZBarStatus.SUCCESS, result.message)
            self.assertAlmostEqual(result.d_left_m or 0.0, 0.0, places=9)
            self.assertAlmostEqual(result.d_right_m or 0.0, 0.0, places=9)
            self.assertLess(abs(result.link_residual_left_m or 0.0), 1e-9)
            self.assertLess(abs(result.link_residual_right_m or 0.0), 1e-9)
            self.assertEqual(len(result.J_d_m_per_rad), 2)
            self.assertLess(result.jacobian_max_disagreement_m_per_rad or 0.0, 5e-4)

    def test_small_rocker_inputs_are_reachable_and_conservative(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE, "front")
        for ql, qr in ((0.01, 0.01), (0.01, -0.01), (-0.01, 0.01)):
            state = solve_nominal_zbar_mechanism(fixture, ql, qr)
            self.assertTrue(state.ok, state.message)
            force = evaluate_two_arm_force(state, setting=1, stiffness_N_per_m=280000.0)
            self.assertTrue(force.ok, force.message)
            self.assertGreaterEqual(force.stored_energy_J or 0.0, 0.0)
            self.assertEqual(len(force.generalized_rocker_torque_Nm), 2)

    def test_discrete_setting_and_stiffness_pair_cannot_be_mismatched(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE, "front")
        state = solve_nominal_zbar_mechanism(fixture, 0.01, -0.01)
        self.assertTrue(state.ok, state.message)
        mismatch = evaluate_two_arm_force(state, setting=1, stiffness_N_per_m=2300000.0)
        self.assertEqual(mismatch.status, ZBarStatus.FAILURE)
        self.assertEqual(mismatch.failure_code, ZBarFailureCode.SOURCE_MISMATCH)
        self.assertIn("280000", mismatch.message)

    def test_left_right_reversal_preserves_energy_for_symmetric_front_fixture(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE, "front")
        a = solve_nominal_zbar_mechanism(fixture, 0.01, -0.01)
        b = solve_nominal_zbar_mechanism(fixture, -0.01, 0.01)
        self.assertTrue(a.ok and b.ok, (a.message, b.message))
        fa = evaluate_two_arm_force(a, setting=3, stiffness_N_per_m=400000.0)
        fb = evaluate_two_arm_force(b, setting=3, stiffness_N_per_m=400000.0)
        self.assertAlmostEqual(fa.stored_energy_J or 0.0, fb.stored_energy_J or 0.0, places=8)

    def test_energy_gradient_matches_generalized_rocker_torque(self) -> None:
        fixture = load_wufr_zbar_fixture(FIXTURE, "rear")
        ql, qr = 0.008, -0.006
        state = solve_nominal_zbar_mechanism(fixture, ql, qr)
        self.assertTrue(state.ok, state.message)
        force = evaluate_two_arm_force(state, setting=2, stiffness_N_per_m=300000.0)
        self.assertTrue(force.ok)
        h = 2e-6
        numerical = []
        for index in (0, 1):
            plus = [ql, qr]
            minus = [ql, qr]
            plus[index] += h
            minus[index] -= h
            sp = solve_nominal_zbar_mechanism(fixture, plus[0], plus[1], with_jacobian=False)
            sm = solve_nominal_zbar_mechanism(fixture, minus[0], minus[1], with_jacobian=False)
            fp = evaluate_two_arm_force(sp, setting=2, stiffness_N_per_m=300000.0)
            fm = evaluate_two_arm_force(sm, setting=2, stiffness_N_per_m=300000.0)
            numerical.append(-((fp.stored_energy_J or 0.0)-(fm.stored_energy_J or 0.0))/(2*h))
        self.assertEqual(len(force.generalized_rocker_torque_Nm), 2)
        for analytic, numeric in zip(force.generalized_rocker_torque_Nm, numerical):
            self.assertTrue(math.isclose(analytic, numeric, rel_tol=2e-3, abs_tol=2e-3), (analytic, numeric))


if __name__ == "__main__":
    unittest.main()
