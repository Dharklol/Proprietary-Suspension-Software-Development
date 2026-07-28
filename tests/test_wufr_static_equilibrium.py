from __future__ import annotations

from pathlib import Path
import unittest

from pssd_vehicle.wufr_static_equilibrium import (
    BODY_ORDER,
    CORNER_ORDER,
    RESULT_LABEL,
    evaluate_wufr_suspension_composition,
    load_wufr_static_equilibrium_provider,
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

    def test_source_and_numerical_contract_are_explicit(self) -> None:
        self.assertEqual(self.provider.source.result_label, RESULT_LABEL)
        self.assertEqual(self.provider.source.body_order, BODY_ORDER)
        self.assertEqual(self.provider.source.wheel_order, CORNER_ORDER)
        self.assertFalse(self.provider.source.default_setting_authorized)
        self.assertFalse(self.provider.source.interpolation_authorized)
        self.assertFalse(self.provider.source.installed_as_built_authority)
        self.assertEqual(self.provider.quasi_static_config.coordinate_scales, (0.005, 0.005, 0.005))
        self.assertEqual(self.provider.quasi_static_config.residual_absolute_tolerance, 1.0e-7)
        self.assertEqual(self.provider.quasi_static_config.residual_relative_tolerance, 1.0e-7)
        self.assertEqual(self.provider.quasi_static_config.finite_difference_relative_step, 0.02)
        self.assertEqual(self.provider.config.energy_gradient_step_multipliers, (0.02, 0.01))
        self.assertEqual(self.provider.config.energy_gradient_absolute_tolerance, 0.01)

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
        self.assertEqual(len(result.spring_actuation_states), 4)
        self.assertEqual(len(result.generalized_spring_force_N), 4)
        self.assertEqual(len(result.generalized_arb_force_N), 4)
        self.assertEqual(len(result.generalized_suspension_force_N), 4)
        for spring, arb, total in zip(
            result.generalized_spring_force_N,
            result.generalized_arb_force_N,
            result.generalized_suspension_force_N,
        ):
            self.assertAlmostEqual(total, spring + arb, places=10)
        self.assertIsNotNone(result.arb_energy_J)
        self.assertAlmostEqual(float(result.arb_energy_J), 0.0, places=9)
        self.assertIsNotNone(result.stored_energy_J)
        self.assertIsNotNone(result.spring_energy_J)
        self.assertAlmostEqual(
            float(result.stored_energy_J),
            float(result.spring_energy_J) + float(result.arb_energy_J),
            places=12,
        )

    def test_spring_states_retain_source_zbar_actuation_geometry(self) -> None:
        result = evaluate_wufr_suspension_composition(
            self.provider,
            (0.0, 0.0, 0.0, 0.0),
            front_arb_setting=1,
            rear_arb_setting=1,
        )
        self.assertTrue(result.ok, result.message)
        assert result.front_arb_state is not None and result.rear_arb_state is not None
        maps = (
            result.front_arb_state.left_map,
            result.front_arb_state.right_map,
            result.rear_arb_state.left_map,
            result.rear_arb_state.right_map,
        )
        for enriched, mapping in zip(result.spring_actuation_states, maps):
            self.assertIsNotNone(mapping)
            assert mapping is not None and mapping.actuation_state is not None
            source = mapping.actuation_state
            self.assertEqual(enriched.axle, source.axle)
            self.assertEqual(enriched.side, source.side)
            self.assertEqual(enriched.q_L_rad, source.q_L_rad)
            self.assertEqual(enriched.q_U_rad, source.q_U_rad)
            self.assertEqual(enriched.rocker_theta_rad, source.rocker_theta_rad)
            self.assertEqual(enriched.rocker_rod_point_m, source.rocker_rod_point_m)
            self.assertEqual(enriched.rocker_coilover_point_m, source.rocker_coilover_point_m)
            self.assertEqual(enriched.current_coilover_length_m, source.current_coilover_length_m)
            self.assertEqual(enriched.delta_z_wc_body_m, source.delta_z_wc_body_m)
            self.assertEqual(enriched.source_fixture_id, source.source_fixture_id)
            self.assertEqual(enriched.configuration_id, source.configuration_id)
            self.assertEqual(
                enriched.derivative_method,
                "analytic_dL_dtheta_times_branch_preserving_dtheta_dz",
            )
            self.assertIsNotNone(enriched.rho_dw)


if __name__ == "__main__":
    unittest.main()
