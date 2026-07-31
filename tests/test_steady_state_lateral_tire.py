from __future__ import annotations

import unittest

from pssd_tire.steady_state_lateral import (
    SteadyStateLateralOperatingState,
    evaluate_curve,
    evaluate_table,
    invert_lateral_force,
)
from pssd_tire.steady_state_lateral_benchmarks import (
    CANONICAL_CONVENTION,
    SYNTHETIC_SOURCE,
    affine_state_cell,
    peak_post_peak_table,
    signed_nonlinear_curve,
)


class SteadyStateLateralCurveTests(unittest.TestCase):
    def test_exact_knot_preserves_stored_value_and_reports_one_sided_slopes(self) -> None:
        response = evaluate_curve(signed_nonlinear_curve(), 0.1)

        self.assertEqual(response.lateral_force_N, 1000.0)
        self.assertTrue(response.exact_knot)
        self.assertAlmostEqual(response.left_segment_slope_N_per_rad, 10_000.0)
        self.assertAlmostEqual(response.right_segment_slope_N_per_rad, -2_000.0)
        self.assertFalse(response.derivative_unique)
        self.assertEqual(len(response.segment_ids), 2)

    def test_open_segment_is_affine_and_has_unique_slope(self) -> None:
        response = evaluate_curve(signed_nonlinear_curve(), 0.05)

        self.assertAlmostEqual(response.lateral_force_N, 500.0)
        self.assertAlmostEqual(response.interpolation_fraction, 0.5)
        self.assertAlmostEqual(response.left_segment_slope_N_per_rad, 10_000.0)
        self.assertAlmostEqual(response.right_segment_slope_N_per_rad, 10_000.0)
        self.assertTrue(response.derivative_unique)


class SteadyStateLateralStateInterpolationTests(unittest.TestCase):
    def _query(self) -> SteadyStateLateralOperatingState:
        return SteadyStateLateralOperatingState(
            slip_angle_rad=0.03,
            normal_load_N=1500.0,
            inclination_rad=0.01,
            pressure_Pa=90_000.0,
            state_id="INTERIOR",
            source_id=SYNTHETIC_SOURCE,
            source_convention_id=CANONICAL_CONVENTION,
        )

    def test_complete_2x2x2_cell_matches_affine_oracle(self) -> None:
        response = evaluate_table(affine_state_cell(), self._query())

        self.assertAlmostEqual(response.lateral_force_N, 50.0)
        self.assertAlmostEqual(response.left_segment_slope_N_per_rad, 5000.0)
        self.assertAlmostEqual(response.right_segment_slope_N_per_rad, 5000.0)
        self.assertTrue(response.derivative_unique)
        self.assertEqual(len(response.participating_curve_ids), 8)
        self.assertAlmostEqual(
            sum(weight for _, weight in response.state_interpolation_weights), 1.0
        )
        for _, weight in response.state_interpolation_weights:
            self.assertAlmostEqual(weight, 0.125)

    def test_exact_operating_state_uses_one_curve(self) -> None:
        table = affine_state_cell()
        curve = table.curves[0]
        query = SteadyStateLateralOperatingState(
            slip_angle_rad=0.02,
            normal_load_N=curve.normal_load_N,
            inclination_rad=curve.inclination_rad,
            pressure_Pa=curve.pressure_Pa,
            state_id="EXACT",
            source_id=SYNTHETIC_SOURCE,
            source_convention_id=CANONICAL_CONVENTION,
        )
        response = evaluate_table(table, query)
        self.assertEqual(response.participating_curve_ids, (curve.curve_id,))
        self.assertEqual(response.state_interpolation_weights, ((curve.curve_id, 1.0),))


class SteadyStateLateralInverseTests(unittest.TestCase):
    def _invert(self, force: float, selector: str | None = None):
        return invert_lateral_force(
            peak_post_peak_table(),
            normal_load_N=1000.0,
            inclination_rad=0.0,
            pressure_Pa=82_737.1,
            requested_lateral_force_N=force,
            source_id=SYNTHETIC_SOURCE,
            source_convention_id=CANONICAL_CONVENTION,
            branch_selector=selector,
        )

    def test_all_signed_roots_are_retained(self) -> None:
        result = self._invert(700.0)
        self.assertEqual(result.status, "multiple_roots")
        self.assertEqual(len(result.candidates), 2)
        self.assertAlmostEqual(result.candidates[0].slip_angle_rad, 0.125)
        self.assertAlmostEqual(result.candidates[1].slip_angle_rad, 0.26)
        self.assertFalse(result.branch_selection_applied)
        self.assertIsNone(result.selected_candidate)

    def test_named_source_branches_select_without_magnitude_guessing(self) -> None:
        pre = self._invert(700.0, "named_pre_peak_branch")
        post = self._invert(700.0, "named_post_peak_branch")
        self.assertAlmostEqual(pre.selected_candidate.slip_angle_rad, 0.125)
        self.assertAlmostEqual(post.selected_candidate.slip_angle_rad, 0.26)

    def test_shared_knot_root_is_deduplicated_and_preserves_both_branches(self) -> None:
        result = self._invert(1000.0)
        self.assertEqual(len(result.candidates), 1)
        candidate = result.candidates[0]
        self.assertAlmostEqual(candidate.slip_angle_rad, 0.2)
        self.assertEqual(candidate.branch_id, "shared_branch_boundary")
        self.assertEqual(candidate.contributing_branch_ids, ("pre_peak", "post_peak"))


if __name__ == "__main__":
    unittest.main()
