from __future__ import annotations

from dataclasses import replace
import math
import unittest

from pssd_suspension.wufr_interface_statics import (
    CompleteCarrierWrench,
    Level1CornerGeometry,
    WufrInterfaceStaticsStatus,
    solve_wufr_level1_interface_statics,
)


EXPECTED = (
    -486.797726581690,
    780.251166344441,
    -54.176236183913,
    499.766045573140,
    26.394714235571,
    -654.215373361056,
    -524.095610408825,
    389.319114514492,
    -214.991224462526,
    -243.099797295896,
    -164.692329354707,
    412.130712370746,
    114.545638554030,
    -654.215373361056,
    -524.095610408825,
    389.319114514492,
    740.690663077577,
    517.427895045907,
)


def _unit(values: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = math.sqrt(sum(value * value for value in values))
    return tuple(value / mag for value in values)  # type: ignore[return-value]


def _front_geometry() -> Level1CornerGeometry:
    return Level1CornerGeometry(
        axle="front",
        side="left",
        frame_id="synthetic_frame",
        configuration_id="BENCH-SUSP-0021",
        geometry_source_id="BENCH-SUSP-0021",
        carrier_reference_m=(0.0, 0.0, 0.0),
        upper_arm_reference_m=(0.2, 0.4, 0.3),
        lower_arm_reference_m=(-0.3, 0.4, -0.2),
        upper_hinge_point_m=(-0.2, 0.5, 0.5),
        upper_hinge_axis_unit=_unit((1.0, 0.2, 0.1)),
        lower_hinge_point_m=(-0.25, 0.55, -0.45),
        lower_hinge_axis_unit=_unit((1.0, -0.1, 0.2)),
        upper_spherical_point_m=(0.45, 0.72, 0.55),
        lower_spherical_point_m=(0.35, 0.66, -0.48),
        lateral_body_point_m=(0.10, 0.84, 0.02),
        lateral_remote_point_m=(1.20, 1.15, 0.25),
        lateral_source_id="synthetic_current_tie_rod",
        actuation_body_point_m=(0.50, 0.30, 0.72),
        actuation_remote_point_m=(0.92, -0.18, 0.94),
        actuation_owner="upper_a_arm",
        actuation_source_id="synthetic_front_pullrod",
    )


def _wrench() -> CompleteCarrierWrench:
    return CompleteCarrierWrench(
        frame_id="synthetic_frame",
        reference_point_m=(0.0, 0.0, 0.0),
        force_N=(120.0, -85.0, -650.0),
        moment_Nm=(20.0, -35.0, 15.0),
        source_id="BENCH-SUSP-0021",
        load_case_id="analytical_fixture",
        complete=True,
    )


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[i] + b[i] for i in range(3))  # type: ignore[return-value]


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


class WufrInterfaceStaticsTests(unittest.TestCase):
    def test_analytical_18x18_fixture(self) -> None:
        result = solve_wufr_level1_interface_statics(_front_geometry(), _wrench())
        self.assertEqual(result.status, WufrInterfaceStaticsStatus.SUCCESS, result.message)
        self.assertEqual(len(result.solution), 18)
        for actual, expected in zip(result.solution, EXPECTED):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)
        expected_lengths = (1.0116323442832382, 0.5257375771237967, 0.7539893898457722)
        for actual, expected in zip(result.characteristic_lengths_m, expected_lengths):
            self.assertAlmostEqual(actual, expected, delta=1.0e-12)
        self.assertAlmostEqual(result.condition_number_inf or 0.0, 256.1483168750569, delta=1.0e-8)
        for residual in result.body_residuals:
            self.assertLessEqual(residual.force_inf_norm_N, 1.0e-9)
            self.assertLessEqual(residual.moment_inf_norm_Nm, 1.0e-9)
        self.assertIsNotNone(result.upper_hinge)
        self.assertIsNotNone(result.lower_hinge)
        assert result.upper_hinge is not None and result.lower_hinge is not None
        self.assertLessEqual(abs(result.upper_hinge.moment_axis_component_Nm), 1.0e-12)
        self.assertLessEqual(abs(result.lower_hinge.moment_axis_component_Nm), 1.0e-12)
        self.assertIsNotNone(result.lateral)
        self.assertIsNotNone(result.actuation)
        assert result.lateral is not None and result.actuation is not None
        self.assertAlmostEqual(result.lateral.axial_force_N, EXPECTED[16], delta=1.0e-8)
        self.assertAlmostEqual(result.actuation.axial_force_N, EXPECTED[17], delta=1.0e-8)

    def test_rigid_translation_invariance(self) -> None:
        geometry = _front_geometry()
        wrench = _wrench()
        baseline = solve_wufr_level1_interface_statics(geometry, wrench)
        self.assertTrue(baseline.ok, baseline.message)
        delta = (2.3, -1.7, 0.41)
        translated_geometry = replace(
            geometry,
            carrier_reference_m=_add(geometry.carrier_reference_m, delta),
            upper_arm_reference_m=_add(geometry.upper_arm_reference_m, delta),
            lower_arm_reference_m=_add(geometry.lower_arm_reference_m, delta),
            upper_hinge_point_m=_add(geometry.upper_hinge_point_m, delta),
            lower_hinge_point_m=_add(geometry.lower_hinge_point_m, delta),
            upper_spherical_point_m=_add(geometry.upper_spherical_point_m, delta),
            lower_spherical_point_m=_add(geometry.lower_spherical_point_m, delta),
            lateral_body_point_m=_add(geometry.lateral_body_point_m, delta),
            lateral_remote_point_m=_add(geometry.lateral_remote_point_m, delta),
            actuation_body_point_m=_add(geometry.actuation_body_point_m, delta),
            actuation_remote_point_m=_add(geometry.actuation_remote_point_m, delta),
        )
        translated_wrench = replace(wrench, reference_point_m=_add(wrench.reference_point_m, delta))
        translated = solve_wufr_level1_interface_statics(translated_geometry, translated_wrench)
        self.assertTrue(translated.ok, translated.message)
        for actual, expected in zip(translated.solution, baseline.solution):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)

    def test_external_wrench_reference_translation_invariance(self) -> None:
        geometry = _front_geometry()
        baseline_wrench = _wrench()
        baseline = solve_wufr_level1_interface_statics(geometry, baseline_wrench)
        self.assertTrue(baseline.ok, baseline.message)
        new_ref = (0.37, -0.22, 0.18)
        shift = tuple(-value for value in new_ref)
        correction = _cross(shift, baseline_wrench.force_N)
        moment_at_new_ref = _add(baseline_wrench.moment_Nm, correction)
        shifted = solve_wufr_level1_interface_statics(
            geometry,
            replace(baseline_wrench, reference_point_m=new_ref, moment_Nm=moment_at_new_ref),
        )
        self.assertTrue(shifted.ok, shifted.message)
        for actual, expected in zip(shifted.solution, baseline.solution):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)

    def test_hinge_axis_sign_flip_preserves_physical_reactions(self) -> None:
        geometry = _front_geometry()
        baseline = solve_wufr_level1_interface_statics(geometry, _wrench())
        flipped = solve_wufr_level1_interface_statics(
            replace(
                geometry,
                upper_hinge_axis_unit=tuple(-value for value in geometry.upper_hinge_axis_unit),
                lower_hinge_axis_unit=tuple(-value for value in geometry.lower_hinge_axis_unit),
            ),
            _wrench(),
        )
        self.assertTrue(baseline.ok, baseline.message)
        self.assertTrue(flipped.ok, flipped.message)
        assert baseline.upper_hinge and baseline.lower_hinge and flipped.upper_hinge and flipped.lower_hinge
        for actual, expected in zip(flipped.upper_hinge.force_N, baseline.upper_hinge.force_N):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)
        for actual, expected in zip(flipped.lower_hinge.force_N, baseline.lower_hinge.force_N):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)
        for actual, expected in zip(flipped.upper_hinge.moment_Nm, baseline.upper_hinge.moment_Nm):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)
        for actual, expected in zip(flipped.lower_hinge.moment_Nm, baseline.lower_hinge.moment_Nm):
            self.assertAlmostEqual(actual, expected, delta=1.0e-8)
        for index in (10, 11, 12, 13, 14, 15, 16, 17):
            self.assertAlmostEqual(flipped.solution[index], baseline.solution[index], delta=1.0e-8)

    def test_rear_actuation_column_stays_on_lower_arm(self) -> None:
        geometry = replace(
            _front_geometry(),
            axle="rear",
            lateral_source_id="synthetic_current_toe_link",
            actuation_owner="lower_a_arm",
            actuation_body_point_m=(0.45, 0.28, -0.72),
            actuation_remote_point_m=(0.95, -0.20, -0.92),
            actuation_source_id="synthetic_rear_pushrod",
        )
        result = solve_wufr_level1_interface_statics(geometry, _wrench())
        self.assertTrue(result.ok, result.message)
        # Column 17 is the actuation rod. It must be identically zero on UCA rows
        # and nonzero on LCA rows for the rear topology.
        self.assertTrue(all(abs(result.equilibrium_matrix[row][17]) <= 1.0e-15 for row in range(6, 12)))
        self.assertTrue(any(abs(result.equilibrium_matrix[row][17]) > 1.0e-12 for row in range(12, 18)))
        self.assertIsNotNone(result.actuation)
        assert result.actuation is not None
        self.assertEqual(result.actuation.body_id, "lower_a_arm")
        self.assertEqual(result.actuation.element_id, "rear_pushrod")


if __name__ == "__main__":
    unittest.main()
