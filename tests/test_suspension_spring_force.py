from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension import (
    ActuationStateResult,
    ActuationStatus,
    Axle,
    SpringDefinition,
    SpringFailureCode,
    SpringLawKind,
    SpringReference,
    SpringStatus,
    SuspensionSpringError,
    check_spring_energy_gradient,
    compression_from_coilover_reference,
    compression_from_seat_length,
    evaluate_spring_from_actuation,
    evaluate_spring_from_coilover,
    evaluate_spring_law,
    generalized_spring_force,
    load_wufr27_spring_package,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "data_catalog/wufr27_spring_package_v0.toml"


class SuspensionSpringForceTests(unittest.TestCase):
    def test_linear_hand_case(self) -> None:
        spring = SpringDefinition(
            spring_id="SYNTH_LINEAR",
            kind=SpringLawKind.LINEAR,
            free_length_m=0.100,
            source_id="BENCH-SUSP-0009",
            configuration_id="SYNTHETIC",
            linear_rate_N_per_m=10000.0,
        )
        result = evaluate_spring_law(spring, 0.020)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.force_N, 200.0)
        self.assertAlmostEqual(result.stored_energy_J, 2.0)
        self.assertAlmostEqual(result.tangent_stiffness_N_per_m, 10000.0)

    def test_explicit_reference_preload_and_unseated_failure(self) -> None:
        reference = SpringReference(
            reference_id="SYNTH_REF",
            configuration_id="SYNTHETIC",
            reference_coilover_length_m=0.200,
            preload_compression_m=0.005,
        )
        result = compression_from_coilover_reference(
            current_coilover_length_m=0.190,
            reference=reference,
            free_length_m=0.100,
        )
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.x_s_m, 0.015)
        self.assertAlmostEqual(result.seat_separation_m, 0.085)

        zero_preload = SpringReference(
            reference_id="ZERO_REF",
            configuration_id="SYNTHETIC",
            reference_coilover_length_m=0.200,
        )
        unseated = compression_from_coilover_reference(
            current_coilover_length_m=0.201,
            reference=zero_preload,
            free_length_m=0.100,
        )
        self.assertFalse(unseated.ok)
        self.assertEqual(unseated.failure_code, SpringFailureCode.SPRING_UNSEATED)
        self.assertLess(unseated.x_s_m, 0.0)

        seat_unseated = compression_from_seat_length(free_length_m=0.100, seat_separation_m=0.101)
        self.assertEqual(seat_unseated.failure_code, SpringFailureCode.SPRING_UNSEATED)
        self.assertAlmostEqual(seat_unseated.x_s_m, -0.001)

    def test_signed_generalized_force_and_energy_gradient(self) -> None:
        spring = SpringDefinition(
            spring_id="SYNTH_LINEAR",
            kind=SpringLawKind.LINEAR,
            free_length_m=0.100,
            source_id="BENCH-SUSP-0009",
            configuration_id="SYNTHETIC",
            linear_rate_N_per_m=10000.0,
        )
        generalized = generalized_spring_force(
            200.0,
            -0.25,
            coordinate_order=("q_m",),
            coordinate_units=("m",),
        )
        self.assertTrue(generalized.ok)
        self.assertEqual(generalized.generalized_force, (-50.0,))

        check = check_spring_energy_gradient(spring, 0.020, -0.25, step_sizes=(1.0e-6, 5.0e-7))
        self.assertTrue(check.ok)
        self.assertAlmostEqual(check.expected_generalized_force, -50.0)
        self.assertEqual(len(check.finite_difference_generalized_force), 2)
        self.assertLess(max(check.absolute_residuals), 5.0e-10)

    def test_vector_generalized_force_preserves_coordinate_order_and_units(self) -> None:
        result = generalized_spring_force(
            200.0,
            (-0.25, 0.10),
            coordinate_order=("z_s_m", "phi_rad"),
            coordinate_units=("m", "rad"),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.coordinate_order, ("z_s_m", "phi_rad"))
        self.assertEqual(result.coordinate_units, ("m", "rad"))
        self.assertEqual(result.generalized_force, (-50.0, 20.0))

        bad_units = generalized_spring_force(
            200.0,
            (-0.25, 0.10),
            coordinate_order=("z_s_m", "phi_rad"),
            coordinate_units=("m",),
        )
        self.assertEqual(bad_units.failure_code, SpringFailureCode.JACOBIAN_UNAVAILABLE)

    def test_piecewise_linear_force_hand_case_and_no_extrapolation(self) -> None:
        spring = SpringDefinition(
            spring_id="SYNTH_TABLE",
            kind=SpringLawKind.PIECEWISE_LINEAR_FORCE,
            free_length_m=0.100,
            source_id="BENCH-SUSP-0009",
            configuration_id="SYNTHETIC",
            domain_max_m=0.020,
            force_points=((0.0, 0.0), (0.010, 100.0), (0.020, 240.0)),
        )
        result = evaluate_spring_law(spring, 0.015)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.force_N, 170.0)
        self.assertAlmostEqual(result.stored_energy_J, 1.175)
        self.assertAlmostEqual(result.tangent_stiffness_N_per_m, 14000.0)
        self.assertEqual(result.segment_index, 1)

        outside = evaluate_spring_law(spring, 0.021)
        self.assertFalse(outside.ok)
        self.assertEqual(outside.failure_code, SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED)

    def test_affine_tangent_law_is_integrated_not_multiplied(self) -> None:
        spring = SpringDefinition(
            spring_id="SYNTH_AFFINE",
            kind=SpringLawKind.AFFINE_TANGENT,
            free_length_m=0.100,
            source_id="BENCH-SUSP-0010",
            configuration_id="SYNTHETIC",
            tangent_rate_intercept_N_per_m=30000.0,
            tangent_rate_gradient_N_per_m2=6000.0 / 0.057,
            domain_max_m=0.057,
        )
        x_s = 0.02108946120919228
        result = evaluate_spring_law(spring, x_s)
        self.assertTrue(result.ok)
        self.assertAlmostEqual(result.force_N, 656.0925401754539, places=9)
        self.assertAlmostEqual(result.tangent_stiffness_N_per_m, 32219.94328517813, places=8)
        self.assertNotAlmostEqual(result.force_N, result.tangent_stiffness_N_per_m * x_s, places=6)

        outside = evaluate_spring_law(spring, 0.0570001)
        self.assertEqual(outside.failure_code, SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED)

    def test_wufr27_package_reproduces_reviewed_nominal_values(self) -> None:
        package = load_wufr27_spring_package(PACKAGE_PATH)
        self.assertEqual(package.configuration_id, "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertFalse(package.installed_as_built_authority)
        self.assertEqual(package.front.assumption_ids, ("ASM-SUSP-0002",))
        self.assertEqual(package.rear.assumption_ids, ("ASM-SUSP-0002",))
        self.assertEqual(package.shockpot_reported_raw, "44m")

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
        self.assertAlmostEqual(front.x_s_m, 0.02110065294783212, places=14)
        self.assertAlmostEqual(rear.x_s_m, 0.02108946120919228, places=14)
        self.assertAlmostEqual(front.force_N, package.front_nominal_force_N, places=9)
        self.assertAlmostEqual(rear.force_N, package.rear_nominal_force_N, places=9)
        self.assertAlmostEqual(
            rear.tangent_stiffness_N_per_m,
            package.rear_nominal_tangent_rate_N_per_m,
            places=8,
        )
        self.assertFalse(front.installed_as_built_authority)
        self.assertFalse(rear.installed_as_built_authority)

    def test_actuation_composition_uses_signed_rho_dw(self) -> None:
        package = load_wufr27_spring_package(PACKAGE_PATH)
        actuation = ActuationStateResult(
            axle=Axle.FRONT,
            side="left",
            status=ActuationStatus.SUCCESS,
            current_coilover_length_m=package.front_nominal_coilover_length_m,
            rho_dw=-0.8272377682304447,
            configuration_id=package.configuration_id,
            source_authority="synthetic test composition",
        )
        result = evaluate_spring_from_actuation(package.front, package.reference, actuation)
        self.assertTrue(result.ok)
        self.assertTrue(result.generalized_force_available)
        self.assertEqual(result.coordinate_order, ("delta_z_wc_body_m",))
        self.assertEqual(result.coordinate_units, ("m",))
        self.assertAlmostEqual(result.generalized_force[0], result.force_N * actuation.rho_dw)
        self.assertLess(result.generalized_force[0], 0.0)

    def test_upstream_and_configuration_failures_are_structured(self) -> None:
        package = load_wufr27_spring_package(PACKAGE_PATH)
        failed_actuation = ActuationStateResult(
            axle=Axle.FRONT,
            side="left",
            status=ActuationStatus.FAILURE,
            message="synthetic upstream failure",
        )
        failed = evaluate_spring_from_actuation(package.front, package.reference, failed_actuation)
        self.assertEqual(failed.failure_code, SpringFailureCode.UPSTREAM_ACTUATION_FAILURE)

        other_ref = SpringReference(
            reference_id="OTHER",
            configuration_id="OTHER_CONFIG",
            reference_coilover_length_m=0.1857,
        )
        mismatch = evaluate_spring_from_coilover(
            package.front,
            other_ref,
            package.front_nominal_coilover_length_m,
        )
        self.assertEqual(mismatch.failure_code, SpringFailureCode.MISSING_REFERENCE_LENGTH)

    def test_malformed_constitutive_laws_are_rejected(self) -> None:
        with self.assertRaises(SuspensionSpringError):
            SpringDefinition(
                spring_id="BAD",
                kind=SpringLawKind.PIECEWISE_LINEAR_FORCE,
                free_length_m=0.100,
                source_id="TEST",
                configuration_id="TEST",
                domain_max_m=0.020,
                force_points=((0.001, 0.0), (0.020, 200.0)),
            )
        with self.assertRaises(SuspensionSpringError):
            SpringDefinition(
                spring_id="BAD_AFFINE",
                kind=SpringLawKind.AFFINE_TANGENT,
                free_length_m=0.100,
                source_id="TEST",
                configuration_id="TEST",
                tangent_rate_intercept_N_per_m=30000.0,
                tangent_rate_gradient_N_per_m2=1000.0,
            )


if __name__ == "__main__":
    unittest.main()
