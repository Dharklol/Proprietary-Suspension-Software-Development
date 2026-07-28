from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_vehicle.wufr_static_equilibrium import (
    BODY_ORDER,
    CORNER_ORDER,
    RESULT_LABEL,
    WUFRStaticEquilibriumStatus,
    evaluate_wufr_suspension_composition,
    load_wufr_static_equilibrium_provider,
    solve_wufr_static_equilibrium,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_catalog/wufr27_static_equilibrium_composition_v0.toml"
ROAD_CONTACT = ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml"
SUSPENSION = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
STEERING = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
WHOLE_VEHICLE = ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml"
GRAVITY = ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml"
SPRING = ROOT / "data_catalog/wufr27_spring_package_v0.toml"
ZBAR = ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml"


class WUFRStaticEquilibriumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = load_wufr_static_equilibrium_provider(
            source_path=SOURCE,
            road_contact_source_path=ROAD_CONTACT,
            suspension_geometry_path=SUSPENSION,
            wheel_profile_path=WHEEL_PROFILE,
            steering_geometry_path=STEERING,
            whole_vehicle_path=WHOLE_VEHICLE,
            gravity_path=GRAVITY,
            spring_package_path=SPRING,
            zbar_fixture_path=ZBAR,
        )

    def test_nominal_suspension_composition_preserves_provider_sum(self) -> None:
        result = evaluate_wufr_suspension_composition(
            self.provider,
            (0.0, 0.0, 0.0, 0.0),
            front_arb_setting=1,
            rear_arb_setting=1,
        )
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.front_arb_setting, 1)
        self.assertEqual(result.rear_arb_setting, 1)
        self.assertEqual(len(result.spring_states), 4)
        self.assertEqual(len(result.generalized_spring_force_N), 4)
        self.assertEqual(len(result.generalized_arb_force_N), 4)
        self.assertEqual(len(result.generalized_suspension_force_N), 4)
        for spring, arb, total in zip(
            result.generalized_spring_force_N,
            result.generalized_arb_force_N,
            result.generalized_suspension_force_N,
        ):
            self.assertAlmostEqual(total, spring + arb, places=10)
        self.assertAlmostEqual(result.arb_energy_J or 1.0, 0.0, places=9)
        self.assertAlmostEqual(
            result.stored_energy_J or 0.0,
            (result.spring_energy_J or 0.0) + (result.arb_energy_J or 0.0),
            places=12,
        )

    def test_setting_1_fixture_converges_with_positive_unmodified_reactions(self) -> None:
        result = solve_wufr_static_equilibrium(
            self.provider,
            front_arb_setting=1,
            rear_arb_setting=1,
        )
        self.assertEqual(result.status, WUFRStaticEquilibriumStatus.SUCCESS, result.message)
        self.assertEqual(result.result_label, RESULT_LABEL)
        self.assertTrue(result.complete_static_road_reaction)
        self.assertFalse(result.installed_as_built_authority)
        self.assertFalse(result.historical_scale_reconstruction_used)
        assert result.solve is not None
        assert result.contact_recovery is not None
        assert result.energy_gradient is not None
        assert result.physical_closure is not None
        self.assertEqual(result.solve.body_coordinate_order, BODY_ORDER)
        self.assertEqual(result.solve.wheel_coordinate_order, CORNER_ORDER)
        self.assertTrue(all(math.isfinite(value) for value in result.solve.q_body))
        self.assertTrue(all(value > 0.0 for value in result.contact_recovery.normal_reaction_N))
        self.assertLess(result.solve.scaled_residual_norm or math.inf, 1.0e-7)
        self.assertLess(
            max(abs(value) for value in result.contact_recovery.wheel_equilibrium_residual),
            self.provider.config.wheel_equilibrium_residual_tolerance_N,
        )
        self.assertLessEqual(
            result.energy_gradient.maximum_absolute_residual or math.inf,
            self.provider.config.energy_gradient_absolute_tolerance,
        )
        self.assertLessEqual(
            result.physical_closure.maximum_force_residual_N or math.inf,
            self.provider.config.physical_force_residual_tolerance_N,
        )
        self.assertLessEqual(
            result.physical_closure.maximum_moment_residual_Nm or math.inf,
            self.provider.config.physical_moment_residual_tolerance_Nm,
        )

    def test_two_bounded_initial_guesses_select_same_continuation_solution(self) -> None:
        first = solve_wufr_static_equilibrium(
            self.provider,
            front_arb_setting=1,
            rear_arb_setting=1,
            initial_q_body=(0.0, 0.0, 0.0),
        )
        second = solve_wufr_static_equilibrium(
            self.provider,
            front_arb_setting=1,
            rear_arb_setting=1,
            initial_q_body=(-0.003, 0.001, -0.001),
        )
        self.assertTrue(first.ok, first.message)
        self.assertTrue(second.ok, second.message)
        assert first.solve is not None and second.solve is not None
        for left, right in zip(first.solve.q_body, second.solve.q_body):
            self.assertTrue(math.isclose(left, right, rel_tol=0.0, abs_tol=2.0e-7), (left, right))
        assert first.contact_recovery is not None and second.contact_recovery is not None
        for left, right in zip(
            first.contact_recovery.normal_reaction_N,
            second.contact_recovery.normal_reaction_N,
        ):
            self.assertTrue(math.isclose(left, right, rel_tol=0.0, abs_tol=2.0e-3), (left, right))


if __name__ == "__main__":
    unittest.main()
