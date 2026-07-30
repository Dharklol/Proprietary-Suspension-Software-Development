from __future__ import annotations

from dataclasses import replace
import math
import unittest

from scripts.run_wufr_static_rocker_included_load_benchmarks import provider
from pssd_suspension.rocker_included_load import RockerPointLoad, evaluate_rocker_included_load
from pssd_suspension.wufr_static_level1_interface_loads import (
    WUFRStaticLevel1Status,
    evaluate_wufr_static_level1_interface_loads,
)
from pssd_suspension.wufr_static_rocker_included_loads import (
    WUFRStaticRockerFailureCode,
    evaluate_wufr_static_rocker_included_loads,
)


class WufrStaticRockerFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = provider()
        cls.level1 = evaluate_wufr_static_level1_interface_loads(cls.provider.level1_provider)
        if not cls.level1.ok:
            raise RuntimeError(cls.level1.message)
        cls.success = evaluate_wufr_static_rocker_included_loads(
            cls.provider,
            level1_result=cls.level1,
        )
        if not cls.success.ok:
            raise RuntimeError(cls.success.message)

    def assert_failed_without_partial(self, result, code) -> None:
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, code)
        self.assertEqual(result.corners, ())

    def test_unsuccessful_upstream_result_rejects_collection(self) -> None:
        result = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(
                self.level1,
                status=WUFRStaticLevel1Status.FAILURE,
                message="injected upstream failure",
            ),
        )
        self.assert_failed_without_partial(
            result,
            WUFRStaticRockerFailureCode.UPSTREAM_LEVEL1_RESULT_FAILURE,
        )

    def test_missing_or_reordered_corner_rejects_collection(self) -> None:
        missing = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(self.level1, corners=self.level1.corners[:3]),
        )
        self.assert_failed_without_partial(
            missing,
            WUFRStaticRockerFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
        )
        reordered = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(
                self.level1,
                corners=(self.level1.corners[1], self.level1.corners[0], *self.level1.corners[2:]),
            ),
        )
        self.assert_failed_without_partial(
            reordered,
            WUFRStaticRockerFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
        )

    def test_moved_push_pull_point_and_reversed_axis_reject_collection(self) -> None:
        first = self.level1.corners[0]
        shifted_point = (
            first.solve.actuation.remote_point_m[0] + 1.0e-4,
            first.solve.actuation.remote_point_m[1],
            first.solve.actuation.remote_point_m[2],
        )
        moved_axial = replace(first.solve.actuation, remote_point_m=shifted_point)
        moved_corner = replace(first, solve=replace(first.solve, actuation=moved_axial))
        moved = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(self.level1, corners=(moved_corner, *self.level1.corners[1:])),
        )
        self.assert_failed_without_partial(
            moved,
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
        )

        reversed_axis = tuple(-value for value in first.solve.actuation.unit_axis_body_to_remote)
        reversed_axial = replace(first.solve.actuation, unit_axis_body_to_remote=reversed_axis)
        reversed_corner = replace(first, solve=replace(first.solve, actuation=reversed_axial))
        reversed_result = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(self.level1, corners=(reversed_corner, *self.level1.corners[1:])),
        )
        self.assert_failed_without_partial(
            reversed_result,
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
        )

    def test_configuration_state_and_load_case_mismatch_reject_collection(self) -> None:
        wrong_configuration = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(self.level1, configuration_id="wrong_configuration"),
        )
        self.assert_failed_without_partial(
            wrong_configuration,
            WUFRStaticRockerFailureCode.CONFIGURATION_MISMATCH,
        )
        wrong_state = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(self.level1, static_state_id="wrong_state"),
        )
        self.assert_failed_without_partial(
            wrong_state,
            WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
        )
        first = self.level1.corners[0]
        wrong_load_case_corner = replace(
            first,
            solve=replace(first.solve, load_case_id="wrong_load_case"),
        )
        wrong_load_case = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(
                self.level1,
                corners=(wrong_load_case_corner, *self.level1.corners[1:]),
            ),
        )
        self.assert_failed_without_partial(
            wrong_load_case,
            WUFRStaticRockerFailureCode.LOAD_CASE_MISMATCH,
        )

    def test_nonfinite_actuation_endpoint_rejects_collection(self) -> None:
        first = self.level1.corners[0]
        nonfinite_axial = replace(
            first.solve.actuation,
            remote_point_m=(math.nan, *first.solve.actuation.remote_point_m[1:]),
        )
        nonfinite_corner = replace(first, solve=replace(first.solve, actuation=nonfinite_axial))
        result = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(self.level1, corners=(nonfinite_corner, *self.level1.corners[1:])),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.corners, ())
        self.assertIn(
            result.failure_code,
            {
                WUFRStaticRockerFailureCode.STATE_IDENTITY_MISMATCH,
                WUFRStaticRockerFailureCode.NONFINITE_OUTPUT,
            },
        )

    def test_unit_influence_matches_independent_kernel_evaluation(self) -> None:
        for corner in self.success.corners:
            influence = corner.damper_unit_influence
            unit = RockerPointLoad(
                load_id="unit_non_spring_damper",
                application_point_m=influence.application_point_m,
                force_N=influence.positive_direction_chassis_to_rocker,
                source_id="BENCH-SUSP-0034:independent_unit_force",
                frame_id=corner.rocker_result.frame_id,
                configuration_id=corner.rocker_result.configuration_id,
                load_case_id=corner.rocker_result.load_case_id,
            )
            independent = evaluate_rocker_included_load(
                rocker_pivot_m=influence.rocker_pivot_m,
                rocker_axis=influence.rocker_axis_unit,
                loads=(unit,),
                missing_load_ids=(),
                frame_id=corner.rocker_result.frame_id,
                configuration_id=corner.rocker_result.configuration_id,
                load_case_id=corner.rocker_result.load_case_id,
                axle=corner.axle,
                side=corner.side,
            )
            self.assertTrue(independent.ok, independent.message)
            for actual, expected in zip(
                influence.d_pivot_force_d_damper_force,
                independent.pivot_force_contribution_N,
            ):
                self.assertAlmostEqual(actual, expected, places=12)
            for actual, expected in zip(
                influence.d_pivot_moment_d_damper_force_m,
                independent.pivot_moment_contribution_Nm,
            ):
                self.assertAlmostEqual(actual, expected, places=12)
            self.assertAlmostEqual(
                influence.d_free_axis_moment_d_damper_force_m,
                independent.free_axis_moment_residual_Nm,
                places=12,
            )
            self.assertFalse(influence.actual_force_magnitude_assumed)
            self.assertFalse(influence.actual_force_authorized)


if __name__ == "__main__":
    unittest.main()
