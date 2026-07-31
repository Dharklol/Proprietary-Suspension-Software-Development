from __future__ import annotations

import math
import unittest
from dataclasses import replace

from pssd_tire.steady_state_lateral import (
    SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED,
    SteadyStateLateralFailure,
    SteadyStateLateralOperatingState,
    SteadyStateLateralTable,
    evaluate_curve,
    evaluate_table,
    invert_lateral_force,
    require_r25b_runtime_activation,
)
from pssd_tire.steady_state_lateral_benchmarks import (
    CANONICAL_CONVENTION,
    SYNTHETIC_SOURCE,
    affine_state_cell,
    peak_post_peak_table,
    signed_nonlinear_curve,
)


class SteadyStateLateralFailureTests(unittest.TestCase):
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

    def test_out_of_domain_fails_without_clipping(self) -> None:
        with self.assertRaises(SteadyStateLateralFailure) as context:
            evaluate_curve(signed_nonlinear_curve(), 0.25)
        self.assertEqual(context.exception.failure_code, "slip_out_of_domain")

    def test_nonfinite_query_fails(self) -> None:
        with self.assertRaises(SteadyStateLateralFailure) as context:
            evaluate_curve(signed_nonlinear_curve(), math.nan)
        self.assertEqual(context.exception.failure_code, "nonfinite_input")

    def test_malformed_source_curve_is_rejected(self) -> None:
        with self.assertRaises(SteadyStateLateralFailure) as context:
            replace(
                signed_nonlinear_curve(),
                curve_id="BAD",
                slip_angle_rad=(0.0, 0.0),
                lateral_force_N=(0.0, 1.0),
            )
        self.assertEqual(context.exception.failure_code, "source_curve_invalid")

    def test_missing_corner_fails_entire_query(self) -> None:
        table = affine_state_cell()
        incomplete = SteadyStateLateralTable(table_id="INCOMPLETE", curves=table.curves[:-1])
        with self.assertRaises(SteadyStateLateralFailure) as context:
            evaluate_table(incomplete, self._query())
        self.assertEqual(context.exception.failure_code, "interpolation_cell_incomplete")

    def test_identity_mismatch_fails_without_partial_subset(self) -> None:
        table = affine_state_cell()
        curves = list(table.curves)
        curves[-1] = replace(curves[-1], intended_tire_id="OTHER_TIRE")
        mismatch = SteadyStateLateralTable(table_id="MISMATCH", curves=tuple(curves))
        with self.assertRaises(SteadyStateLateralFailure) as context:
            evaluate_table(mismatch, self._query())
        self.assertEqual(context.exception.failure_code, "interpolation_identity_mismatch")

    def test_operating_state_extrapolation_is_rejected(self) -> None:
        query = replace(self._query(), normal_load_N=2500.0)
        with self.assertRaises(SteadyStateLateralFailure) as context:
            evaluate_table(affine_state_cell(), query)
        self.assertEqual(context.exception.failure_code, "operating_state_out_of_domain")

    def test_force_out_of_domain_fails(self) -> None:
        with self.assertRaises(SteadyStateLateralFailure) as context:
            invert_lateral_force(
                peak_post_peak_table(),
                normal_load_N=1000.0,
                inclination_rad=0.0,
                pressure_Pa=82_737.1,
                requested_lateral_force_N=1200.0,
                source_id=SYNTHETIC_SOURCE,
                source_convention_id=CANONICAL_CONVENTION,
            )
        self.assertEqual(context.exception.failure_code, "force_demand_out_of_domain")

    def test_horizontal_coincident_segment_is_interval_ambiguity(self) -> None:
        curve = replace(
            signed_nonlinear_curve(),
            curve_id="HORIZONTAL",
            slip_angle_rad=(0.0, 0.1, 0.2, 0.3),
            lateral_force_N=(0.0, 100.0, 100.0, 0.0),
            segment_branch_ids=("pre_peak", "plateau", "post_peak"),
        )
        table = SteadyStateLateralTable(table_id="HORIZONTAL", curves=(curve,))
        with self.assertRaises(SteadyStateLateralFailure) as context:
            invert_lateral_force(
                table,
                normal_load_N=1000.0,
                inclination_rad=0.0,
                pressure_Pa=82_737.1,
                requested_lateral_force_N=100.0,
                source_id=SYNTHETIC_SOURCE,
                source_convention_id=CANONICAL_CONVENTION,
            )
        self.assertEqual(context.exception.failure_code, "inverse_branch_ambiguous")

    def test_real_r25b_activation_remains_blocked(self) -> None:
        self.assertFalse(SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED)
        with self.assertRaises(SteadyStateLateralFailure) as context:
            require_r25b_runtime_activation()
        self.assertEqual(context.exception.failure_code, "source_specific_activation_blocked")


if __name__ == "__main__":
    unittest.main()
