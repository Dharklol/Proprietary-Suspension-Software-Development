from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from pssd_suspension import (
    AntiRollBarDefinition,
    AntiRollBarReference,
    check_anti_roll_bar_energy_gradient,
    evaluate_anti_roll_bar,
    symmetric_differential_coordinate,
)
from pssd_suspension.wufr_anti_roll_bar import load_wufr27_blade_anti_roll_bar_package


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "benchmarks/suspension/suspension_anti_roll_bar_result_v0.1.0.toml"
PACKAGE_PATH = ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"


class SuspensionAntiRollBarResultRecordTests(unittest.TestCase):
    def test_frozen_wufr_result_record_matches_provider(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            result = tomllib.load(stream)
        self.assertEqual(result["model_id"], "MOD-SUSP-0005")
        self.assertEqual(result["authorization_id"], "AUTH-SUSP-0005")
        self.assertEqual(result["assumption_ids"], ["ASM-SUSP-0003"])
        self.assertFalse(result["installed_as_built_authority"])
        self.assertFalse(result["vehicle_equilibrium_evaluated"])
        self.assertTrue(result["blade_component_stiffness_evaluated"])
        self.assertFalse(result["z_bar_geometry_map_evaluated"])

        package = load_wufr27_blade_anti_roll_bar_package(PACKAGE_PATH)
        b12 = result["BENCH-SUSP-0012"]
        self.assertEqual(
            list(package.solidworks_fea_stiffness_N_per_mm),
            b12["governing_stiffness_N_per_mm"],
        )
        self.assertEqual(
            [item.definition.stiffness_action_per_coordinate for item in package.settings],
            b12["governing_stiffness_N_per_m"],
        )
        self.assertEqual(list(package.simulink_comparison_N_per_mm), b12["simulink_comparison_N_per_mm"])
        self.assertEqual(list(package.instron_comparison_N_per_mm), b12["instron_comparison_N_per_mm"])
        self.assertEqual(
            list(package.matlab_reduced_axle_comparison_Nm_per_deg),
            b12["matlab_reduced_axle_comparison_Nm_per_deg"],
        )
        self.assertFalse(b12["interpolation_authorized"])
        self.assertFalse(b12["z_bar_geometry_map_authorized"])
        self.assertFalse(b12["generalized_force_available_without_map"])

        for index, (expected_force, expected_energy) in enumerate(
            zip(b12["one_mm_force_N"], b12["one_mm_energy_J"]), start=1
        ):
            state = evaluate_anti_roll_bar(
                package.definition_for_setting(index), package.reference, 0.001
            )
            self.assertTrue(state.ok)
            self.assertAlmostEqual(state.elastic_action, expected_force, places=12)
            self.assertAlmostEqual(state.stored_energy_J, expected_energy, places=12)
            self.assertFalse(state.generalized_force_available)

        energy = check_anti_roll_bar_energy_gradient(
            package.definition_for_setting(3),
            package.reference,
            0.001,
            1.0,
            step_sizes=(1.0e-7, 5.0e-8),
        )
        self.assertTrue(energy.ok)
        self.assertLessEqual(max(energy.absolute_residuals), 1.0e-7)

    def test_frozen_synthetic_result_record_matches_provider(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            result = tomllib.load(stream)
        b11 = result["BENCH-SUSP-0011"]

        definition = AntiRollBarDefinition(
            arb_id="BENCH_SUSP_0011_ARB",
            axle="synthetic",
            stiffness_action_per_coordinate=10000.0,
            elastic_coordinate_unit="m",
            elastic_action_unit="N",
            source_id="BENCH-SUSP-0011",
            configuration_id="SYNTHETIC",
            max_abs_deformation=0.050,
        )
        reference = AntiRollBarReference(
            reference_id="BENCH_SUSP_0011_ZERO",
            configuration_id="SYNTHETIC",
            elastic_coordinate_unit="m",
        )
        mapping = symmetric_differential_coordinate(0.010, -0.010)
        state = evaluate_anti_roll_bar(
            definition,
            reference,
            float(mapping.deformation_m),
            ds_dq=(float(mapping.ds_dz_left), float(mapping.ds_dz_right)),
            coordinate_order=("z_left_m", "z_right_m"),
            coordinate_units=("m", "m"),
        )
        self.assertTrue(state.ok)
        self.assertAlmostEqual(state.deformation, b11["differential_deformation_m"], places=15)
        self.assertAlmostEqual(state.elastic_action, b11["differential_action_N"], places=12)
        self.assertAlmostEqual(state.stored_energy_J, b11["differential_energy_J"], places=12)
        self.assertEqual(list(state.generalized_force), b11["differential_generalized_force_N"])

        energy = check_anti_roll_bar_energy_gradient(
            definition,
            reference,
            float(mapping.deformation_m),
            1.0,
            step_sizes=(1.0e-6, 5.0e-7),
        )
        self.assertTrue(energy.ok)
        self.assertLessEqual(max(energy.absolute_residuals), 1.0e-8)
        self.assertLessEqual(b11["max_energy_gradient_residual_N"], 1.0e-8)


if __name__ == "__main__":
    unittest.main()
