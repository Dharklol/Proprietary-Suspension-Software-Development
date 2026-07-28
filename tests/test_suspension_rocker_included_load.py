from __future__ import annotations

import unittest

from pssd_suspension.rocker_included_load import RockerPointLoad, evaluate_rocker_included_load


FRAME = "TEST_FRAME"
CONFIG = "TEST_CONFIG"
CASE = "TEST_CASE"


def _load(load_id: str, point: tuple[float, float, float], force: tuple[float, float, float]) -> RockerPointLoad:
    return RockerPointLoad(
        load_id=load_id,
        application_point_m=point,
        force_N=force,
        source_id=f"SOURCE_{load_id}",
        frame_id=FRAME,
        configuration_id=CONFIG,
        load_case_id=CASE,
    )


def _assert_vector(test: unittest.TestCase, actual, expected, places: int = 12) -> None:
    test.assertIsNotNone(actual)
    for value, target in zip(actual, expected):
        test.assertAlmostEqual(value, target, places=places)


class RockerIncludedLoadTests(unittest.TestCase):
    def test_exact_three_dimensional_hand_case(self) -> None:
        loads = (
            _load("one", (0.4, -0.2, 0.3), (10.0, 20.0, -5.0)),
            _load("two", (0.1, 0.2, 0.3), (-4.0, 3.0, 8.0)),
            _load("three", (0.1, -0.2, 0.8), (2.0, -6.0, 1.0)),
        )
        result = evaluate_rocker_included_load(
            rocker_pivot_m=(0.1, -0.2, 0.3),
            rocker_axis=(0.0, 0.0, 2.0),
            loads=loads,
            missing_load_ids=("not_modeled",),
            frame_id=FRAME,
            configuration_id=CONFIG,
            load_case_id=CASE,
        )
        self.assertTrue(result.ok, result.message)
        _assert_vector(self, result.included_resultant_force_N, (8.0, 17.0, 4.0))
        _assert_vector(self, result.included_resultant_moment_Nm, (6.2, 2.5, 7.6))
        _assert_vector(self, result.pivot_force_contribution_N, (-8.0, -17.0, -4.0))
        _assert_vector(self, result.pivot_moment_contribution_Nm, (-6.2, -2.5, 0.0))
        self.assertAlmostEqual(result.free_axis_moment_residual_Nm, 7.6, places=12)
        _assert_vector(self, result.final_force_residual_N, (0.0, 0.0, 0.0))
        _assert_vector(self, result.final_moment_residual_Nm, (0.0, 0.0, 7.6))
        _assert_vector(self, result.perpendicular_moment_residual_Nm, (0.0, 0.0, 0.0))
        self.assertAlmostEqual(result.support_axis_moment_component_Nm, 0.0, places=12)
        self.assertFalse(result.complete_hardware_reaction)

    def test_translation_invariance(self) -> None:
        base = (
            _load("a", (0.3, 0.0, 0.0), (1.0, 2.0, 3.0)),
            _load("b", (0.0, -0.4, 0.2), (-2.0, 1.0, 0.5)),
        )
        first = evaluate_rocker_included_load(
            rocker_pivot_m=(0.0, 0.0, 0.0),
            rocker_axis=(1.0, 2.0, 3.0),
            loads=base,
            missing_load_ids=("missing",),
            frame_id=FRAME,
            configuration_id=CONFIG,
            load_case_id=CASE,
        )
        shift = (5.0, -7.0, 11.0)
        translated = tuple(
            _load(
                load.load_id,
                tuple(load.application_point_m[i] + shift[i] for i in range(3)),
                load.force_N,
            )
            for load in base
        )
        second = evaluate_rocker_included_load(
            rocker_pivot_m=shift,
            rocker_axis=(1.0, 2.0, 3.0),
            loads=translated,
            missing_load_ids=("missing",),
            frame_id=FRAME,
            configuration_id=CONFIG,
            load_case_id=CASE,
        )
        self.assertTrue(first.ok and second.ok)
        _assert_vector(self, second.included_resultant_force_N, first.included_resultant_force_N)
        _assert_vector(self, second.included_resultant_moment_Nm, first.included_resultant_moment_Nm)
        _assert_vector(self, second.pivot_force_contribution_N, first.pivot_force_contribution_N)
        _assert_vector(self, second.pivot_moment_contribution_Nm, first.pivot_moment_contribution_Nm)
        self.assertAlmostEqual(second.free_axis_moment_residual_Nm, first.free_axis_moment_residual_Nm, places=12)

    def test_force_reversal_and_scaling(self) -> None:
        base_loads = (
            _load("a", (0.2, 0.1, 0.0), (3.0, -2.0, 5.0)),
            _load("b", (-0.1, 0.4, 0.3), (1.0, 4.0, -2.0)),
        )

        def solve(scale: float):
            return evaluate_rocker_included_load(
                rocker_pivot_m=(0.0, 0.0, 0.0),
                rocker_axis=(0.0, 1.0, 0.0),
                loads=tuple(
                    _load(load.load_id, load.application_point_m, tuple(scale * value for value in load.force_N))
                    for load in base_loads
                ),
                missing_load_ids=("missing",),
                frame_id=FRAME,
                configuration_id=CONFIG,
                load_case_id=CASE,
            )

        base = solve(1.0)
        reversed_result = solve(-1.0)
        scaled = solve(3.5)
        self.assertTrue(base.ok and reversed_result.ok and scaled.ok)
        for field in (
            "included_resultant_force_N",
            "included_resultant_moment_Nm",
            "pivot_force_contribution_N",
            "pivot_moment_contribution_Nm",
            "final_moment_residual_Nm",
        ):
            original = getattr(base, field)
            _assert_vector(self, getattr(reversed_result, field), tuple(-value for value in original))
            _assert_vector(self, getattr(scaled, field), tuple(3.5 * value for value in original))
        self.assertAlmostEqual(reversed_result.free_axis_moment_residual_Nm, -base.free_axis_moment_residual_Nm, places=12)
        self.assertAlmostEqual(scaled.free_axis_moment_residual_Nm, 3.5 * base.free_axis_moment_residual_Nm, places=12)

    def test_zero_free_axis_moment_balances_fully(self) -> None:
        result = evaluate_rocker_included_load(
            rocker_pivot_m=(0.0, 0.0, 0.0),
            rocker_axis=(0.0, 0.0, 1.0),
            loads=(_load("axial", (0.0, 0.0, 0.5), (0.0, 0.0, -20.0)),),
            missing_load_ids=("missing",),
            frame_id=FRAME,
            configuration_id=CONFIG,
            load_case_id=CASE,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.free_axis_moment_residual_Nm, 0.0)
        _assert_vector(self, result.final_moment_residual_Nm, (0.0, 0.0, 0.0))
        self.assertTrue(result.included_set_balances_about_free_axis)


if __name__ == "__main__":
    unittest.main()
