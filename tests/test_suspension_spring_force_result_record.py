from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from pssd_suspension import (
    SpringDefinition,
    SpringFailureCode,
    SpringLawKind,
    check_spring_energy_gradient,
    evaluate_spring_from_coilover,
    evaluate_spring_law,
    load_wufr27_spring_package,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "benchmarks/suspension/suspension_spring_force_result_v0.1.0.toml"
PACKAGE_PATH = ROOT / "data_catalog/wufr27_spring_package_v0.toml"


class SuspensionSpringForceResultRecordTests(unittest.TestCase):
    def test_frozen_result_record_matches_executable_provider(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            result = tomllib.load(stream)

        self.assertEqual(result["model_id"], "MOD-SUSP-0004")
        self.assertEqual(result["authorization_id"], "AUTH-SUSP-0004")
        self.assertEqual(result["assumption_ids"], ["ASM-SUSP-0002"])
        self.assertFalse(result["installed_as_built_authority"])
        self.assertFalse(result["vehicle_equilibrium_evaluated"])

        package = load_wufr27_spring_package(PACKAGE_PATH)
        front = evaluate_spring_from_coilover(
            package.front,
            package.reference,
            package.front_nominal_coilover_length_m,
        )
        rear = evaluate_spring_from_coilover(
            package.rear,
            package.reference,
            package.rear_nominal_coilover_length_m,
        )
        self.assertTrue(front.ok)
        self.assertTrue(rear.ok)

        b10 = result["BENCH-SUSP-0010"]
        self.assertAlmostEqual(front.x_s_m, b10["front_nominal_compression_m"], places=14)
        self.assertAlmostEqual(rear.x_s_m, b10["rear_nominal_compression_m"], places=14)
        self.assertAlmostEqual(front.force_N, b10["front_nominal_force_N"], places=9)
        self.assertAlmostEqual(rear.force_N, b10["rear_nominal_force_N"], places=9)
        self.assertAlmostEqual(
            rear.tangent_stiffness_N_per_m,
            b10["rear_nominal_tangent_stiffness_N_per_m"],
            places=8,
        )

        outside = evaluate_spring_law(package.rear, 0.0570001)
        self.assertEqual(outside.failure_code, SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED)
        self.assertEqual(outside.failure_code.value, b10["rear_outside_failure_code"])

        energy = check_spring_energy_gradient(
            package.rear,
            float(rear.x_s_m),
            -1.0,
            step_sizes=(1.0e-6, 5.0e-7),
        )
        self.assertTrue(energy.ok)
        self.assertAlmostEqual(max(energy.absolute_residuals), b10["rear_energy_check_max_residual"], places=15)

    def test_synthetic_table_values_match_frozen_record(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            result = tomllib.load(stream)
        table = SpringDefinition(
            spring_id="BENCH_SUSP_0009_TABLE",
            kind=SpringLawKind.PIECEWISE_LINEAR_FORCE,
            free_length_m=0.100,
            source_id="BENCH-SUSP-0009",
            configuration_id="SYNTHETIC",
            domain_max_m=0.020,
            force_points=((0.0, 0.0), (0.010, 100.0), (0.020, 240.0)),
        )
        state = evaluate_spring_law(table, 0.015)
        self.assertTrue(state.ok)
        b9 = result["BENCH-SUSP-0009"]
        self.assertLessEqual(abs(float(state.force_N) - 170.0), b9["table_force_error_N"] + 1.0e-15)
        self.assertLessEqual(abs(float(state.stored_energy_J) - 1.175), b9["table_energy_error_J"] + 1.0e-15)
        self.assertLessEqual(abs(float(state.tangent_stiffness_N_per_m) - 14000.0), b9["table_tangent_error_N_per_m"] + 1.0e-15)


if __name__ == "__main__":
    unittest.main()
