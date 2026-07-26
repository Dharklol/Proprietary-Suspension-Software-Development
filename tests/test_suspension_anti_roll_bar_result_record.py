from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest

from pssd_suspension import (
    AntiRollBarDefinition,
    AntiRollBarReference,
    check_anti_roll_bar_energy_gradient,
    evaluate_anti_roll_bar,
    load_wufr27_anti_roll_bar_package,
    symmetric_differential_coordinate,
)


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
        self.assertFalse(result["blade_component_stiffness_evaluated"])

        package = load_wufr27_anti_roll_bar_package(PACKAGE_PATH)
        phi = math.radians(1.0)
        front = evaluate_anti_roll_bar(
            package.front,
            package.reference,
            phi,
            ds_dq=1.0,
            coordinate_order=("phi_arb_rad",),
            coordinate_units=("rad",),
        )
        rear = evaluate_anti_roll_bar(package.rear, package.reference, phi)
        self.assertTrue(front.ok)
        self.assertTrue(rear.ok)

        b12 = result["BENCH-SUSP-0012"]
        self.assertTrue(math.isclose(package.front.stiffness_action_per_coordinate, b12["front_stiffness_Nm_per_rad"], rel_tol=1e-14))
        self.assertTrue(math.isclose(package.rear.stiffness_action_per_coordinate, b12["rear_stiffness_Nm_per_rad"], rel_tol=1e-14))
        self.assertTrue(math.isclose(float(front.elastic_action), b12["front_one_degree_action_Nm"], rel_tol=1e-14))
        self.assertTrue(math.isclose(float(rear.elastic_action), b12["rear_one_degree_action_Nm"], rel_tol=1e-14))
        self.assertTrue(math.isclose(float(front.stored_energy_J), b12["front_one_degree_energy_J"], rel_tol=1e-14))
        self.assertTrue(math.isclose(float(rear.stored_energy_J), b12["rear_one_degree_energy_J"], rel_tol=1e-14))
        self.assertTrue(math.isclose(front.generalized_force[0], b12["front_one_degree_generalized_force"], rel_tol=1e-14))
        self.assertTrue(package.front.reduced_axle_level)
        self.assertTrue(b12["reduced_axle_level"])

        energy = check_anti_roll_bar_energy_gradient(
            package.front,
            package.reference,
            phi,
            1.0,
            step_sizes=(1.0e-6, 5.0e-7),
        )
        self.assertTrue(energy.ok)
        self.assertLessEqual(max(energy.absolute_residuals), 1.0e-6)
        self.assertLessEqual(b12["front_energy_check_max_residual"], 1.0e-6)

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
