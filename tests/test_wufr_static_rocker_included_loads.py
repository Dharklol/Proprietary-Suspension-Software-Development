from __future__ import annotations

from dataclasses import replace
import unittest

from scripts.run_wufr_static_rocker_included_load_benchmarks import provider
from pssd_suspension.wufr_static_level1_interface_loads import (
    WUFRStaticLevel1Status,
    evaluate_wufr_static_level1_interface_loads,
)
from pssd_suspension.wufr_static_rocker_included_loads import (
    CORNER_ORDER,
    MISSING_LOAD_ID,
    WUFRStaticRockerFailureCode,
    evaluate_wufr_static_rocker_included_loads,
)


class WufrStaticRockerIncludedLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = provider()
        cls.level1 = evaluate_wufr_static_level1_interface_loads(cls.provider.level1_provider)
        if not cls.level1.ok:
            raise RuntimeError(cls.level1.message)
        cls.result = evaluate_wufr_static_rocker_included_loads(
            cls.provider,
            level1_result=cls.level1,
        )

    def test_four_corner_composition_succeeds_atomically(self) -> None:
        self.assertTrue(self.result.ok, self.result.message)
        self.assertEqual(tuple(c.corner_id for c in self.result.corners), CORNER_ORDER)
        self.assertTrue(self.result.complete_for_named_included_load_set)
        self.assertFalse(self.result.complete_hardware_reaction)
        self.assertFalse(self.result.complete_rocker_equilibrium)
        self.assertFalse(self.result.actual_damper_force_applied)

    def test_exact_point_load_handoffs_and_missing_damper_identity(self) -> None:
        for corner in self.result.corners:
            included = corner.included_result
            self.assertIsNotNone(included)
            self.assertEqual(
                included.included_load_ids,
                ("push_pull", "conservative_spring", "physical_arb_link"),
            )
            self.assertEqual(included.missing_load_ids, (MISSING_LOAD_ID,))
            self.assertFalse(included.complete_hardware_reaction)
            push_pull = included.included_loads[0]
            actuation = corner.interface_result.solve.actuation
            self.assertEqual(push_pull.force_N, actuation.force_on_remote_N)
            self.assertEqual(push_pull.application_point_m, actuation.remote_point_m)
            self.assertEqual(push_pull.source_id, actuation.source_id)
            spring = included.included_loads[1]
            self.assertEqual(spring.force_N, corner.spring_result.force_on_rocker_N)
            self.assertEqual(spring.application_point_m, corner.spring_result.rocker_eye_m)
            arb = included.included_loads[2]
            side_force = corner.arb_link_result.left if corner.side == "left" else corner.arb_link_result.right
            pickup = (
                corner.arb_mechanism_result.rocker_pickup_left_m
                if corner.side == "left"
                else corner.arb_mechanism_result.rocker_pickup_right_m
            )
            self.assertEqual(arb.force_N, side_force.force_on_rocker_N)
            self.assertEqual(arb.application_point_m, pickup)

    def test_residuals_pass_without_free_axis_repair(self) -> None:
        self.assertLessEqual(self.result.maximum_force_residual_N, 1.0e-10)
        self.assertLessEqual(self.result.maximum_perpendicular_moment_residual_Nm, 1.0e-10)
        self.assertLessEqual(self.result.maximum_support_axis_moment_component_Nm, 1.0e-10)
        for corner in self.result.corners:
            included = corner.included_result
            self.assertIsNotNone(included.free_axis_moment_residual_Nm)
            self.assertEqual(
                included.final_moment_residual_Nm,
                tuple(
                    included.free_axis_moment_residual_Nm * value
                    for value in included.rocker_axis_unit
                ),
            )

    def test_unit_damper_influence_is_geometry_only(self) -> None:
        for corner in self.result.corners:
            influence = corner.damper_unit_influence
            self.assertEqual(influence.unit_force_N, 1.0)
            self.assertFalse(influence.actual_force_magnitude_assumed)
            self.assertFalse(influence.actual_force_authorized)
            for reaction, direction in zip(
                influence.d_pivot_force_d_damper_force,
                influence.positive_direction_chassis_to_rocker,
            ):
                self.assertAlmostEqual(reaction, -direction, places=14)
            axis_component = sum(
                a * b
                for a, b in zip(
                    influence.rocker_axis_unit,
                    influence.d_pivot_moment_d_damper_force_m,
                )
            )
            self.assertAlmostEqual(axis_component, 0.0, places=12)

    def test_upstream_failure_and_reorder_publish_no_partial_corners(self) -> None:
        failed = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(
                self.level1,
                status=WUFRStaticLevel1Status.FAILURE,
                message="injected",
            ),
        )
        self.assertFalse(failed.ok)
        self.assertEqual(failed.failure_code, WUFRStaticRockerFailureCode.UPSTREAM_LEVEL1_RESULT_FAILURE)
        self.assertEqual(failed.corners, ())
        reordered = evaluate_wufr_static_rocker_included_loads(
            self.provider,
            level1_result=replace(
                self.level1,
                corners=(self.level1.corners[1], self.level1.corners[0], *self.level1.corners[2:]),
            ),
        )
        self.assertFalse(reordered.ok)
        self.assertEqual(reordered.failure_code, WUFRStaticRockerFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH)
        self.assertEqual(reordered.corners, ())


if __name__ == "__main__":
    unittest.main()
