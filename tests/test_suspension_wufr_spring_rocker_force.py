from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import unittest

from pssd_suspension import (
    build_nominal_wheel_reference,
    evaluate_spring_from_actuation,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    load_wufr27_spring_package,
    solve_actuation_q_L_state,
)
from pssd_suspension.wufr_spring_rocker_force import (
    WufrSpringRockerForceFailureCode,
    WufrSpringRockerForceStatus,
    physical_spring_force_at_rocker,
    recover_wufr_spring_rocker_force,
)


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY_PATH = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
SPRING_PACKAGE_PATH = ROOT / "data_catalog/wufr27_spring_package_v0.toml"


def _norm(a: tuple[float, float, float]) -> float:
    return math.sqrt(sum(value * value for value in a))


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


class WufrSpringRockerForceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_optimumk_geometry_snapshot(GEOMETRY_PATH)
        cls.wheel_profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE_PATH)
        cls.spring_package = load_wufr27_spring_package(SPRING_PACKAGE_PATH)

    def _nominal(self, axle: str, side: str):
        corner = self.geometry.corner(axle, side)
        nominal_wheel = build_nominal_wheel_reference(self.wheel_profile, axle, side)
        actuation = solve_actuation_q_L_state(
            corner,
            nominal_wheel,
            0.0,
            geometry_id=self.geometry.geometry_id,
            source_authority=self.geometry.authority,
        )
        self.assertTrue(actuation.ok, actuation.message)
        definition = self.spring_package.front if axle == "front" else self.spring_package.rear
        spring = evaluate_spring_from_actuation(
            definition,
            self.spring_package.reference,
            actuation,
            use_local_rho_dw_when_available=False,
        )
        self.assertTrue(spring.ok, spring.message)
        result = recover_wufr_spring_rocker_force(corner, actuation, spring)
        self.assertEqual(result.status, WufrSpringRockerForceStatus.SUCCESS, result.message)
        return corner, actuation, spring, result

    def test_nominal_front_rear_bilateral_geometry_force_and_virtual_work_identity(self) -> None:
        for axle in ("front", "rear"):
            expected_length = (
                self.spring_package.front_nominal_coilover_length_m
                if axle == "front"
                else self.spring_package.rear_nominal_coilover_length_m
            )
            expected_force = (
                self.spring_package.front_nominal_force_N
                if axle == "front"
                else self.spring_package.rear_nominal_force_N
            )
            for side in ("left", "right"):
                with self.subTest(axle=axle, side=side):
                    _corner, _actuation, spring, result = self._nominal(axle, side)
                    assert result.chassis_to_rocker_unit is not None
                    assert result.force_on_rocker_N is not None
                    assert result.force_on_chassis_N is not None
                    self.assertAlmostEqual(float(result.eye_to_eye_length_m), expected_length, delta=2.0e-6)
                    self.assertAlmostEqual(float(spring.force_N), expected_force, delta=1.0e-6)
                    self.assertAlmostEqual(float(result.spring_force_magnitude_N), expected_force, delta=1.0e-6)
                    self.assertAlmostEqual(_norm(result.chassis_to_rocker_unit), 1.0, places=12)
                    self.assertAlmostEqual(_norm(result.force_on_rocker_N), expected_force, delta=1.0e-9)
                    for value in _add(result.force_on_rocker_N, result.force_on_chassis_N):
                        self.assertAlmostEqual(value, 0.0, delta=1.0e-10)
                    self.assertAlmostEqual(float(result.rocker_torque_identity_residual_Nm), 0.0, delta=1.0e-10)
                    self.assertAlmostEqual(
                        float(result.rocker_axis_torque_Nm),
                        float(result.generalized_rocker_torque_from_virtual_work_Nm),
                        delta=1.0e-10,
                    )
                    self.assertTrue(result.spring_only)
                    self.assertFalse(result.installed_as_built_authority)

    def test_bilateral_nominal_force_geometry_mirrors_lateral_component(self) -> None:
        for axle in ("front", "rear"):
            _cl, _al, _sl, left = self._nominal(axle, "left")
            _cr, _ar, _sr, right = self._nominal(axle, "right")
            assert left.force_on_rocker_N is not None and right.force_on_rocker_N is not None
            self.assertAlmostEqual(left.force_on_rocker_N[0], right.force_on_rocker_N[0], delta=1.0e-9)
            self.assertAlmostEqual(left.force_on_rocker_N[1], -right.force_on_rocker_N[1], delta=1.0e-9)
            self.assertAlmostEqual(left.force_on_rocker_N[2], right.force_on_rocker_N[2], delta=1.0e-9)

    def test_synthetic_three_dimensional_case_satisfies_exact_identity(self) -> None:
        result = physical_spring_force_at_rocker(
            chassis_eye_m=(0.13, -0.22, 0.31),
            rocker_eye_m=(0.41, 0.17, 0.55),
            rocker_pivot_m=(0.05, 0.09, 0.12),
            rocker_axis=(0.7, -0.2, 0.5),
            spring_force_magnitude_N=812.3,
            axle="synthetic",
            side="left",
            spring_id="synthetic",
            spring_source_id="BENCH-SUSP-0025",
            configuration_id="synthetic-3d",
            assumption_ids=("ASM-SUSP-0007",),
        )
        self.assertTrue(result.ok, result.message)
        assert result.force_on_rocker_N is not None and result.force_on_chassis_N is not None
        self.assertAlmostEqual(_norm(result.force_on_rocker_N), 812.3, delta=1.0e-10)
        self.assertAlmostEqual(float(result.rocker_torque_identity_residual_Nm), 0.0, delta=1.0e-10)
        for value in _add(result.force_on_rocker_N, result.force_on_chassis_N):
            self.assertAlmostEqual(value, 0.0, delta=1.0e-10)

    def test_degenerate_eye_line_and_negative_force_fail_closed(self) -> None:
        degenerate = physical_spring_force_at_rocker(
            chassis_eye_m=(1.0, 2.0, 3.0),
            rocker_eye_m=(1.0, 2.0, 3.0),
            rocker_pivot_m=(0.0, 0.0, 0.0),
            rocker_axis=(1.0, 0.0, 0.0),
            spring_force_magnitude_N=100.0,
        )
        self.assertFalse(degenerate.ok)
        self.assertEqual(degenerate.failure_code, WufrSpringRockerForceFailureCode.DEGENERATE_EYE_LINE)
        self.assertIsNone(degenerate.force_on_rocker_N)

        negative = physical_spring_force_at_rocker(
            chassis_eye_m=(0.0, 0.0, 0.0),
            rocker_eye_m=(0.0, 1.0, 0.0),
            rocker_pivot_m=(0.0, 0.0, 0.0),
            rocker_axis=(1.0, 0.0, 0.0),
            spring_force_magnitude_N=-1.0,
        )
        self.assertFalse(negative.ok)
        self.assertEqual(negative.failure_code, WufrSpringRockerForceFailureCode.NEGATIVE_SPRING_FORCE)

    def test_configuration_and_current_eye_length_mismatch_fail_closed(self) -> None:
        corner, actuation, spring, _result = self._nominal("front", "left")
        mismatch = recover_wufr_spring_rocker_force(
            corner,
            actuation,
            replace(spring, configuration_id="not-the-current-car"),
        )
        self.assertFalse(mismatch.ok)
        self.assertEqual(mismatch.failure_code, WufrSpringRockerForceFailureCode.SOURCE_MISMATCH)

        length_mismatch = recover_wufr_spring_rocker_force(
            corner,
            actuation,
            replace(spring, current_coilover_length_m=float(spring.current_coilover_length_m) + 1.0e-3),
        )
        self.assertFalse(length_mismatch.ok)
        self.assertEqual(length_mismatch.failure_code, WufrSpringRockerForceFailureCode.EYE_LENGTH_MISMATCH)


if __name__ == "__main__":
    unittest.main()
