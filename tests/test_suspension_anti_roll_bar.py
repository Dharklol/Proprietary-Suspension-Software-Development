from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension import (
    AntiRollBarDefinition,
    AntiRollBarFailureCode,
    AntiRollBarReference,
    AntiRollBarStatus,
    check_anti_roll_bar_energy_gradient,
    evaluate_anti_roll_bar,
    evaluate_anti_roll_bar_law,
    load_wufr27_anti_roll_bar_package,
    stiffness_Nm_per_deg_to_Nm_per_rad,
    symmetric_differential_angle,
)


ROOT = Path(__file__).resolve().parents[1]


class SuspensionAntiRollBarTests(unittest.TestCase):
    def test_degree_to_radian_stiffness_conversion(self) -> None:
        self.assertTrue(
            math.isclose(
                stiffness_Nm_per_deg_to_Nm_per_rad(2560.0),
                146677.19555349075,
                rel_tol=1.0e-14,
            )
        )

    def test_synthetic_common_and_differential_bilateral_map(self) -> None:
        common = symmetric_differential_angle(0.010, 0.010, 1.0)
        self.assertTrue(common.ok)
        self.assertAlmostEqual(common.angle_rad, 0.0)

        differential = symmetric_differential_angle(0.010, -0.010, 1.0)
        self.assertTrue(differential.ok)
        self.assertAlmostEqual(differential.angle_rad, 0.020)
        self.assertAlmostEqual(differential.dphi_dz_left, 1.0)
        self.assertAlmostEqual(differential.dphi_dz_right, -1.0)

        definition = AntiRollBarDefinition(
            arb_id="SYNTHETIC_ARB",
            axle="synthetic",
            stiffness_Nm_per_rad=10000.0,
            source_id="BENCH-SUSP-0011",
            configuration_id="SYNTHETIC",
        )
        reference = AntiRollBarReference(
            reference_id="SYNTHETIC_ZERO",
            configuration_id="SYNTHETIC",
        )
        state = evaluate_anti_roll_bar(
            definition,
            reference,
            float(differential.angle_rad),
            dphi_dq=(float(differential.dphi_dz_left), float(differential.dphi_dz_right)),
            coordinate_order=("z_left_m", "z_right_m"),
            coordinate_units=("m", "m"),
        )
        self.assertTrue(state.ok)
        self.assertAlmostEqual(state.restoring_moment_Nm, 200.0)
        self.assertAlmostEqual(state.stored_energy_J, 2.0)
        self.assertEqual(state.generalized_force, (-200.0, 200.0))
        self.assertAlmostEqual(sum(state.generalized_force), 0.0)

    def test_signed_energy_gradient_matches_generalized_force(self) -> None:
        definition = AntiRollBarDefinition(
            arb_id="SYNTHETIC_ARB",
            axle="synthetic",
            stiffness_Nm_per_rad=10000.0,
            source_id="BENCH-SUSP-0011",
            configuration_id="SYNTHETIC",
        )
        reference = AntiRollBarReference(
            reference_id="SYNTHETIC_ZERO",
            configuration_id="SYNTHETIC",
        )
        check = check_anti_roll_bar_energy_gradient(
            definition,
            reference,
            0.020,
            1.0,
            step_sizes=(1.0e-6, 5.0e-7),
        )
        self.assertTrue(check.ok)
        self.assertAlmostEqual(check.expected_generalized_force, -200.0)
        self.assertLessEqual(max(check.absolute_residuals), 1.0e-8)

    def test_reference_shift_is_explicit(self) -> None:
        definition = AntiRollBarDefinition(
            arb_id="SYNTHETIC_ARB",
            axle="synthetic",
            stiffness_Nm_per_rad=10000.0,
            source_id="BENCH-SUSP-0011",
            configuration_id="SYNTHETIC",
        )
        reference = AntiRollBarReference(
            reference_id="SYNTHETIC_PRELOAD_REFERENCE",
            configuration_id="SYNTHETIC",
            zero_energy_angle_rad=0.003,
        )
        state = evaluate_anti_roll_bar(definition, reference, 0.020)
        self.assertTrue(state.ok)
        self.assertAlmostEqual(state.deformation_rad, 0.017)
        self.assertAlmostEqual(state.restoring_moment_Nm, 170.0)
        self.assertAlmostEqual(state.stored_energy_J, 1.445)

    def test_explicit_no_bar_returns_zero_without_inventing_zero_stiffness(self) -> None:
        reference = AntiRollBarReference(
            reference_id="NO_BAR_REF",
            configuration_id="SYNTHETIC",
        )
        state = evaluate_anti_roll_bar(
            None,
            reference,
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
        self.assertEqual(state.restoring_moment_Nm, 0.0)
        self.assertEqual(state.generalized_force, (0.0, 0.0))

    def test_missing_stiffness_and_domain_fail_explicitly(self) -> None:
        reference = AntiRollBarReference(
            reference_id="REF",
            configuration_id="SYNTHETIC",
        )
        missing = evaluate_anti_roll_bar(None, reference, 0.01)
        self.assertEqual(missing.failure_code, AntiRollBarFailureCode.MISSING_STIFFNESS_AUTHORITY)

        bounded = AntiRollBarDefinition(
            arb_id="BOUNDED",
            axle="synthetic",
            stiffness_Nm_per_rad=10000.0,
            source_id="BENCH-SUSP-0011",
            configuration_id="SYNTHETIC",
            max_abs_deformation_rad=0.02,
        )
        outside = evaluate_anti_roll_bar_law(bounded, 0.0201)
        self.assertEqual(outside.failure_code, AntiRollBarFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED)

    def test_wufr_reduced_package_reproduces_selected_values(self) -> None:
        package = load_wufr27_anti_roll_bar_package(
            ROOT / "data_catalog/wufr27_anti_roll_bar_package_v0.toml"
        )
        self.assertEqual(package.configuration_id, "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertFalse(package.installed_as_built_authority)
        self.assertEqual(package.front.assumption_ids, ("ASM-SUSP-0003",))
        self.assertEqual(package.rear.assumption_ids, ("ASM-SUSP-0003",))
        self.assertTrue(package.front.reduced_axle_level)
        self.assertTrue(package.rear.reduced_axle_level)
        self.assertAlmostEqual(package.source_front_stiffness_Nm_per_deg, 2560.0)
        self.assertAlmostEqual(package.source_rear_stiffness_Nm_per_deg, 2270.0)
        self.assertEqual(package.instron_status, "qualitative_corroboration_only")

        phi = math.radians(1.0)
        front = evaluate_anti_roll_bar(
            package.front,
            package.reference,
            phi,
            dphi_dq=1.0,
            coordinate_order=("phi_arb_rad",),
            coordinate_units=("rad",),
        )
        rear = evaluate_anti_roll_bar(package.rear, package.reference, phi)
        self.assertTrue(front.ok)
        self.assertTrue(rear.ok)
        self.assertTrue(math.isclose(float(front.restoring_moment_Nm), 2560.0, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(float(rear.restoring_moment_Nm), 2270.0, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(float(front.stored_energy_J), 22.340214425527417, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(float(rear.stored_energy_J), 19.80948701013564, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(front.generalized_force[0], -2560.0, rel_tol=1.0e-14))

    def test_configuration_mismatch_is_not_silently_repaired(self) -> None:
        definition = AntiRollBarDefinition(
            arb_id="ARB",
            axle="front",
            stiffness_Nm_per_rad=1000.0,
            source_id="SOURCE",
            configuration_id="A",
        )
        reference = AntiRollBarReference(reference_id="REF", configuration_id="B")
        state = evaluate_anti_roll_bar(definition, reference, 0.01)
        self.assertEqual(state.failure_code, AntiRollBarFailureCode.SOURCE_CONFIGURATION_MISMATCH)


if __name__ == "__main__":
    unittest.main()
