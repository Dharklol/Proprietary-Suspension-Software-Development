"""Tests for downstream steering R&D figure specifications."""

from __future__ import annotations

import unittest

from pssd_viz import FigureAvailability
from pssd_viz.steering_figures import (
    motion_state_comparison_spec,
    steering_residual_spec,
    steering_response_comparison_spec,
    tire_force_branch_spec,
    unavailable_figure_spec,
)


class SteeringFigureSuiteTests(unittest.TestCase):
    def test_response_and_residual_specs_preserve_supplied_values(self) -> None:
        inputs = (-10.0, 0.0, 10.0)
        target_left = (-3.0, 0.0, 3.0)
        target_right = (-2.5, 0.0, 2.5)
        actual_left = (-2.9, 0.0, 3.2)
        actual_right = (-2.7, 0.0, 2.4)

        response = steering_response_comparison_spec(
            figure_id="FIG-TEST-STEER-001",
            title="response",
            inputs_deg=inputs,
            left_target_deg=target_left,
            right_target_deg=target_right,
            left_response_deg=actual_left,
            right_response_deg=actual_right,
            configuration_id="TEST",
            authority="test only",
            source_ids=("test",),
        )
        self.assertEqual(len(response.series), 4)
        self.assertEqual(response.series[2].y, actual_left)

        residual = steering_residual_spec(
            figure_id="FIG-TEST-STEER-002",
            title="residual",
            inputs_deg=inputs,
            left_target_deg=target_left,
            right_target_deg=target_right,
            left_response_deg=actual_left,
            right_response_deg=actual_right,
            configuration_id="TEST",
            authority="test only",
            source_ids=("test",),
        )
        self.assertAlmostEqual(residual.series[0].y[0], 0.1)
        self.assertAlmostEqual(residual.series[0].y[-1], 0.2)
        self.assertAlmostEqual(residual.series[1].y[0], -0.2)
        self.assertAlmostEqual(residual.series[1].y[-1], -0.1)

    def test_tire_branch_and_motion_specs_are_downstream_data_contracts(self) -> None:
        tire = tire_force_branch_spec(
            figure_id="FIG-TEST-TIRE-001",
            title="tire",
            curves=(("branch", (0.0, 2.0, 4.0), (0.0, 100.0, 180.0)),),
            configuration_id="TIRE-TEST",
            authority="synthetic",
            source_ids=("fixture",),
        )
        self.assertEqual(tire.series[0].x[-1], 4.0)
        self.assertEqual(tire.series[0].y[-1], 180.0)

        motion = motion_state_comparison_spec(
            figure_id="FIG-TEST-MOTION-001",
            title="motion",
            velocity_center_s_m=(-0.8, 0.8),
            left_heading_deg=(40.0, 3.0),
            right_heading_deg=(35.0, 9.0),
            configuration_id="MOTION-TEST",
            authority="synthetic",
            source_ids=("fixture",),
            state_ids=("rear", "front"),
        )
        self.assertEqual(motion.metadata.model_id, "MOD-VEH-0002")
        self.assertEqual(motion.metadata.state_ids, ("rear", "front"))

    def test_unavailable_source_figure_cannot_be_blank(self) -> None:
        spec = unavailable_figure_spec(
            figure_id="FIG-TEST-UNAVAILABLE-001",
            title="missing source",
            x_quantity="Slip angle",
            x_unit="deg",
            y_quantity="Fy",
            y_unit="N",
            model_id="TIRE-TEST",
            configuration_id="MISSING",
            authority="source gated",
            reason="Reviewed branch values are unavailable.",
        )
        self.assertIs(spec.availability, FigureAvailability.UNAVAILABLE)
        self.assertEqual(spec.series, ())
        self.assertIn("unavailable", spec.unavailable_reason.lower())


if __name__ == "__main__":
    unittest.main()
