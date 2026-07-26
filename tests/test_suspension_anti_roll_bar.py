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
    symmetric_differential_coordinate,
)


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

    def test_degree_to_radian_stiffness_conversion(self) -> None:
        self.assertTrue(
            math.isclose(
                stiffness_Nm_per_deg_to_Nm_per_rad(2560.0),
                146677.19555349075,
                rel_tol=1.0e-14,
            )
        )

    def test_synthetic_common_and_differential_bilateral_map(self) -> None:
        common = symmetric_differential_coordinate(0.010, 0.010)
        self.assertTrue(common.ok)
        self.assertAlmostEqual(common.deformation_m, 0.0)

        differential = symmetric_differential_coordinate(0.010, -0.010)
        self.assertTrue(differential.ok)
        self.assertAlmostEqual(differential.deformation_m, 0.020)
        self.assertAlmostEqual(differential.ds_dz_left, 1.0)
        self.assertAlmostEqual(differential.ds_dz_right, -1.0)

        state = evaluate_anti_roll_bar(
            self.synthetic_definition(),
            self.synthetic_reference(),
            float(differential.deformation_m),
            ds_dq=(float(differential.ds_dz_left), float(differential.ds_dz_right)),
            coordinate_order=("z_left_m", "z_right_m"),
            coordinate_units=("m", "m"),
        )
        self.assertTrue(state.ok)
        self.assertEqual(state.elastic_coordinate_unit, "m")
        self.assertEqual(state.elastic_action_unit, "N")
        self.assertAlmostEqual(state.elastic_action, 200.0)
        self.assertAlmostEqual(state.stored_energy_J, 2.0)
        self.assertEqual(state.generalized_force, (-200.0, 200.0))
        self.assertAlmostEqual(sum(state.generalized_force), 0.0)

    def test_signed_energy_gradient_matches_generalized_force(self) -> None:
        check = check_anti_roll_bar_energy_gradient(
            self.synthetic_definition(),
            self.synthetic_reference(),
            0.020,
            1.0,
            step_sizes=(1.0e-6, 5.0e-7),
        )
        self.assertTrue(check.ok)
        self.assertAlmostEqual(check.expected_generalized_force, -200.0)
        self.assertLessEqual(max(check.absolute_residuals), 1.0e-8)

    def test_reference_shift_is_explicit(self) -> None:
        state = evaluate_anti_roll_bar(
            self.synthetic_definition(),
            self.synthetic_reference(zero=0.003),
            0.020,
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
            self.synthetic_definition(max_abs_deformation=0.020),
            0.0201,
        )
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
        self.assertEqual(package.front.elastic_coordinate_unit, "rad")
        self.assertEqual(package.front.elastic_action_unit, "N*m")
        self.assertAlmostEqual(package.source_front_stiffness_Nm_per_deg, 2560.0)
        self.assertAlmostEqual(package.source_rear_stiffness_Nm_per_deg, 2270.0)
        self.assertEqual(package.instron_status, "qualitative_corroboration_only")

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
        self.assertTrue(math.isclose(float(front.elastic_action), 2560.0, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(float(rear.elastic_action), 2270.0, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(float(front.stored_energy_J), 22.340214425527417, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(float(rear.stored_energy_J), 19.80948701013564, rel_tol=1.0e-14))
        self.assertTrue(math.isclose(front.generalized_force[0], -2560.0, rel_tol=1.0e-14))

    def test_configuration_or_coordinate_unit_mismatch_is_not_silently_repaired(self) -> None:
        definition = AntiRollBarDefinition(
            arb_id="ARB",
            axle="front",
            stiffness_action_per_coordinate=1000.0,
            elastic_coordinate_unit="rad",
            elastic_action_unit="N*m",
            source_id="SOURCE",
            configuration_id="A",
        )
        bad_config = AntiRollBarReference(
            reference_id="REF",
            configuration_id="B",
            elastic_coordinate_unit="rad",
        )
        config_state = evaluate_anti_roll_bar(definition, bad_config, 0.01)
        self.assertEqual(config_state.failure_code, AntiRollBarFailureCode.SOURCE_CONFIGURATION_MISMATCH)

        bad_unit = AntiRollBarReference(
            reference_id="REF",
            configuration_id="A",
            elastic_coordinate_unit="m",
        )
        unit_state = evaluate_anti_roll_bar(definition, bad_unit, 0.01)
        self.assertEqual(unit_state.failure_code, AntiRollBarFailureCode.SOURCE_CONFIGURATION_MISMATCH)


if __name__ == "__main__":
    unittest.main()
