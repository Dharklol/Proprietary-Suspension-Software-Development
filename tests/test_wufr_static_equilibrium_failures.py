from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import unittest

from pssd_vehicle.wufr_static_equilibrium import (
    WUFRStaticEquilibriumFailureCode,
    WUFRStaticEquilibriumStatus,
    evaluate_wufr_suspension_composition,
    load_wufr_static_equilibrium_provider,
    solve_wufr_static_equilibrium,
)


ROOT = Path(__file__).resolve().parents[1]


def _provider():
    return load_wufr_static_equilibrium_provider(
        source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v0.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


class WUFRStaticEquilibriumFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = _provider()

    def test_front_and_rear_arb_settings_are_required_and_never_defaulted(self) -> None:
        for front, rear in ((0, 1), (1, 6), (True, 1), (1, False)):
            result = solve_wufr_static_equilibrium(
                self.provider,
                front_arb_setting=front,
                rear_arb_setting=rear,
            )
            self.assertEqual(result.status, WUFRStaticEquilibriumStatus.FAILURE)
            self.assertEqual(result.failure_code, WUFRStaticEquilibriumFailureCode.INVALID_ARB_SETTING)
            self.assertIsNone(result.solve)

    def test_nonfinite_initial_state_fails_before_provider_evaluation(self) -> None:
        result = solve_wufr_static_equilibrium(
            self.provider,
            front_arb_setting=1,
            rear_arb_setting=1,
            initial_q_body=(0.0, math.nan, 0.0),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT)
        self.assertIsNone(result.solve)

    def test_wheel_coordinate_contract_is_not_repaired(self) -> None:
        result = evaluate_wufr_suspension_composition(
            self.provider,
            (0.0, 0.0, 0.0),
            front_arb_setting=1,
            rear_arb_setting=1,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT)
        self.assertEqual(result.generalized_suspension_force_N, ())

    def test_unreachable_body_bounds_propagate_kernel_failure_without_clipping(self) -> None:
        solver = replace(
            self.provider.quasi_static_config,
            lower_bounds=(-1.0e-5, -1.0e-5, -1.0e-5),
            upper_bounds=(1.0e-5, 1.0e-5, 1.0e-5),
            max_iterations=4,
        )
        bounded = replace(self.provider, quasi_static_config=solver)
        result = solve_wufr_static_equilibrium(
            bounded,
            front_arb_setting=1,
            rear_arb_setting=1,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticEquilibriumFailureCode.EQUILIBRIUM_FAILURE)
        self.assertIsNotNone(result.solve)
        assert result.solve is not None
        for value, lower, upper in zip(result.solve.q_body, solver.lower_bounds, solver.upper_bounds):
            assert lower is not None and upper is not None
            self.assertGreaterEqual(value, lower)
            self.assertLessEqual(value, upper)

    def test_result_boundary_never_promotes_structural_or_installed_authority(self) -> None:
        source = self.provider.source
        self.assertFalse(source.installed_as_built_authority)
        self.assertFalse(source.physical_correlation_authority)
        self.assertFalse(source.carrier_wrench_authority)
        self.assertFalse(source.structural_load_case_authority)
        self.assertFalse(source.default_setting_authorized)
        self.assertFalse(source.interpolation_authorized)


if __name__ == "__main__":
    unittest.main()
