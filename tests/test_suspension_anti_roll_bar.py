from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension import (
    AntiRollBarDefinition,
    AntiRollBarFailureCode,
    AntiRollBarReference,
    AntiRollBarStatus,
    SuspensionAntiRollBarError,
    check_anti_roll_bar_energy_gradient,
    evaluate_anti_roll_bar,
    evaluate_anti_roll_bar_law,
    symmetric_differential_coordinate,
)
from pssd_suspension.wufr_anti_roll_bar import load_wufr27_blade_anti_roll_bar_package


ROOT = Path(__file__).resolve().parents[1]


class SuspensionAntiRollBarTests(unittest.TestCase):
    @staticmethod
    def synthetic_definition(*, max_abs_deformation: float | None = None) -> AntiRollBarDefinition:
        return AntiRollBarDefinition(
            arb_id="SYNTHETIC_ARB",
            axle="synthetic",
            stiffness_action_per_coordinate=10000.0,
            elastic_coordinate_unit="m",
            elastic_action_unit="N",
            source_id="BENCH-SUSP-0011",
            configuration_id="SYNTHETIC",
            max_abs_deformation=max_abs_deformation,
        )

    @staticmethod
    def synthetic_reference(*, zero: float = 0.0) -> AntiRollBarReference:
        return AntiRollBarReference(
            reference_id="SYNTHETIC_REF",
            configuration_id="SYNTHETIC",
            elastic_coordinate_unit="m",
            zero_energy_coordinate=zero,
        )

    def test_synthetic_common_and_differential_bilateral_map(self) -> None:
        common = symmetric_differential_coordinate(0.010, 0.010)
        self.assertTrue(common.ok)
        self.assertAlmostEqual(common.deformation_m, 0.0)

        differential = symmetric_differential_coordinate(0.010, -0.010)
        self.assertTrue(differential.ok)
        state = evaluate_anti_roll_bar(
            self.synthetic_definition(),
            self.synthetic_reference(),
            float(differential.deformation_m),
            ds_dq=(float(differential.ds_dz_left), float(differential.ds_dz_right)),
            coordinate_order=("z_left_m", "z_right_m"),
            coordinate_units=("m", "m"),
        )
        self.assertTrue(state.ok)
        self.assertAlmostEqual(state.elastic_action, 200.0)
        self.assertAlmostEqual(state.stored_energy_J, 2.0)
        self.assertEqual(state.generalized_force, (-200.0, 200.0))

    def test_signed_energy_gradient_matches_generalized_force(self) -> None:
        check = check_anti_roll_bar_energy_gradient(
            self.synthetic_definition(), self.synthetic_reference(), 0.020, 1.0,
            step_sizes=(1.0e-6, 5.0e-7),
        )
        self.assertTrue(check.ok)
        self.assertAlmostEqual(check.expected_generalized_force, -200.0)
        self.assertLessEqual(max(check.absolute_residuals), 1.0e-8)

    def test_reference_shift_is_explicit(self) -> None:
        state = evaluate_anti_roll_bar(
            self.synthetic_definition(), self.synthetic_reference(zero=0.003), 0.020
        )
        self.assertTrue(state.ok)
        self.assertAlmostEqual(state.deformation, 0.017)
        self.assertAlmostEqual(state.elastic_action, 170.0)
        self.assertAlmostEqual(state.stored_energy_J, 1.445)

    def test_explicit_no_bar_returns_zero_without_inventing_zero_stiffness(self) -> None:
        state = evaluate_anti_roll_bar(
            None,
            self.synthetic_reference(),
            0.2,
            enabled=False,
            coordinate_order=("z_left_m", "z_right_m"),
            coordinate_units=("m", "m"),
            disabled_arb_id="NO_BAR",
            disabled_axle="rear",
            disabled_source_id="BENCH-SUSP-0011",
        )
        self.assertEqual(state.status, AntiRollBarStatus.NO_BAR)
        self.assertFalse(state.enabled)
        self.assertEqual(state.stored_energy_J, 0.0)
        self.assertEqual(state.elastic_action, 0.0)
        self.assertEqual(state.generalized_force, (0.0, 0.0))

    def test_missing_stiffness_and_domain_fail_explicitly(self) -> None:
        missing = evaluate_anti_roll_bar(None, self.synthetic_reference(), 0.01)
        self.assertEqual(missing.failure_code, AntiRollBarFailureCode.MISSING_STIFFNESS_AUTHORITY)
        outside = evaluate_anti_roll_bar_law(
            self.synthetic_definition(max_abs_deformation=0.020), 0.0201
        )
        self.assertEqual(outside.failure_code, AntiRollBarFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED)

    def test_wufr_package_uses_discrete_solidworks_blade_stiffness(self) -> None:
        package = load_wufr27_blade_anti_roll_bar_package(
            ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"
        )
        self.assertEqual(package.solidworks_fea_stiffness_N_per_mm, (280.0, 300.0, 400.0, 700.0, 2300.0))
        self.assertEqual(package.simulink_comparison_N_per_mm, (285.0, 309.0, 400.0, 724.0, 2628.0))
        self.assertEqual(package.instron_comparison_N_per_mm, (900.0, 980.0, 1320.0, 1970.0, 2630.0))
        self.assertEqual(package.matlab_reduced_axle_comparison_Nm_per_deg, (2560.0, 2270.0))
        self.assertFalse(package.interpolation_authorized)
        self.assertFalse(package.geometry_map_authorized)
        self.assertFalse(package.installed_as_built_authority)

        expected_force = (280.0, 300.0, 400.0, 700.0, 2300.0)
        expected_energy = (0.140, 0.150, 0.200, 0.350, 1.150)
        for setting, force, energy in zip(range(1, 6), expected_force, expected_energy):
            definition = package.definition_for_setting(setting)
            self.assertEqual(definition.elastic_coordinate_unit, "m")
            self.assertEqual(definition.elastic_action_unit, "N")
            self.assertFalse(definition.reduced_axle_level)
            self.assertEqual(definition.stiffness_action_per_coordinate, force * 1000.0)
            state = evaluate_anti_roll_bar(definition, package.reference, 0.001)
            self.assertTrue(state.ok)
            self.assertTrue(math.isclose(float(state.elastic_action), force, rel_tol=0.0, abs_tol=1.0e-12))
            self.assertTrue(math.isclose(float(state.stored_energy_J), energy, rel_tol=0.0, abs_tol=1.0e-12))
            self.assertFalse(state.generalized_force_available)

    def test_wufr_setting_selection_does_not_interpolate(self) -> None:
        package = load_wufr27_blade_anti_roll_bar_package(
            ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"
        )
        with self.assertRaises(SuspensionAntiRollBarError):
            package.definition_for_setting(2.5)  # type: ignore[arg-type]
        with self.assertRaises(SuspensionAntiRollBarError):
            package.definition_for_setting(0)
        with self.assertRaises(SuspensionAntiRollBarError):
            package.definition_for_setting(6)

    def test_wufr_blade_coordinate_energy_gradient_is_conservative(self) -> None:
        package = load_wufr27_blade_anti_roll_bar_package(
            ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"
        )
        check = check_anti_roll_bar_energy_gradient(
            package.definition_for_setting(3), package.reference, 0.001, 1.0,
            step_sizes=(1.0e-7, 5.0e-8),
        )
        self.assertTrue(check.ok)
        self.assertAlmostEqual(check.expected_generalized_force, -400.0)
        self.assertLessEqual(max(check.absolute_residuals), 1.0e-7)

    def test_configuration_or_coordinate_unit_mismatch_is_not_silently_repaired(self) -> None:
        definition = AntiRollBarDefinition(
            arb_id="ARB", axle="front", stiffness_action_per_coordinate=1000.0,
            elastic_coordinate_unit="rad", elastic_action_unit="N*m",
            source_id="SOURCE", configuration_id="A",
        )
        bad_config = AntiRollBarReference(
            reference_id="REF", configuration_id="B", elastic_coordinate_unit="rad"
        )
        self.assertEqual(
            evaluate_anti_roll_bar(definition, bad_config, 0.01).failure_code,
            AntiRollBarFailureCode.SOURCE_CONFIGURATION_MISMATCH,
        )
        bad_unit = AntiRollBarReference(
            reference_id="REF", configuration_id="A", elastic_coordinate_unit="m"
        )
        self.assertEqual(
            evaluate_anti_roll_bar(definition, bad_unit, 0.01).failure_code,
            AntiRollBarFailureCode.SOURCE_CONFIGURATION_MISMATCH,
        )


if __name__ == "__main__":
    unittest.main()
