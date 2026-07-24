from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_steering import load_geometry
from pssd_steering.derived import exact_ackermann_outside_reference
from pssd_steering.optimization import load_historical_fit_target, load_pose_set
from pssd_steering.optimization.tire_targets import (
    TireDifferentialStateDefinition,
    build_tire_informed_operating_target_set,
    peak_grip_slip_angle_differential,
)
from pssd_tire import TireOperatingPoint, load_lateral_summary_grid


ROOT = Path(__file__).resolve().parents[1]


class SteeringTireTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grid = load_lateral_summary_grid(
            ROOT / "benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml"
        )
        self.sampling = load_historical_fit_target(
            ROOT / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
        )
        self.pose_set = load_pose_set(
            ROOT / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
        )
        self.geometry = load_geometry(
            ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
        )
        self.inside = TireOperatingPoint(222.0, 0.0, 83.0)
        self.outside = TireOperatingPoint(1112.0, 2.0, 83.0)
        self.utilization = tuple(
            abs(value) / 102.0 for value in self.sampling.inputs
        )

    def test_frozen_peak_slip_differential_is_1p3_deg(self) -> None:
        differential = peak_grip_slip_angle_differential(
            self.grid, self.inside, self.outside
        )
        self.assertEqual(9.6, differential.inside.peak_slip_angle_magnitude_deg)
        self.assertEqual(10.9, differential.outside.peak_slip_angle_magnitude_deg)
        self.assertAlmostEqual(
            1.3, differential.outside_minus_inside_peak_slip_deg
        )

    def test_builder_preserves_inside_and_corrects_outside_symmetrically(self) -> None:
        definition = TireDifferentialStateDefinition(
            state_id="nominal",
            inside_operating_point=self.inside,
            outside_operating_point=self.outside,
            slip_utilization_by_sample=self.utilization,
            authority="software verification TTC-envelope reference pair",
        )
        target_set = build_tire_informed_operating_target_set(
            self.sampling,
            self.pose_set,
            self.grid,
            (definition,),
            target_set_id="TEST-TIRE-TARGET",
            version="0.1.0",
            wheelbase_m=self.geometry.wheelbase,
            steering_axis_track_m=self.geometry.steering_axis_track,
            authority="test",
        )
        target = target_set.state_map["nominal"]
        center = self.sampling.inputs.index(0.0)
        self.assertEqual(0.0, target.left_outputs[center])
        self.assertEqual(0.0, target.right_outputs[center])

        index_left = 0
        self.assertAlmostEqual(
            self.sampling.left_outputs[index_left], target.left_outputs[index_left]
        )
        inside_deg = abs(
            self.sampling.canonical_to_target_output_sign
            * self.sampling.left_outputs[index_left]
        )
        ackermann_out_deg = math.degrees(
            exact_ackermann_outside_reference(
                math.radians(inside_deg),
                self.geometry.wheelbase,
                self.geometry.steering_axis_track,
            )
        )
        corrected_out_deg = ackermann_out_deg + 1.3
        target_right_canonical = (
            self.sampling.canonical_to_target_output_sign
            * target.right_outputs[index_left]
        )
        self.assertAlmostEqual(
            corrected_out_deg, abs(target_right_canonical), places=10
        )

        index_right = -1
        self.assertAlmostEqual(
            self.sampling.right_outputs[index_right], target.right_outputs[index_right]
        )
        target_left_canonical = (
            self.sampling.canonical_to_target_output_sign
            * target.left_outputs[index_right]
        )
        self.assertAlmostEqual(
            corrected_out_deg, abs(target_left_canonical), places=10
        )

    def test_censored_operating_point_is_not_admitted_as_peak_target(self) -> None:
        definition = TireDifferentialStateDefinition(
            state_id="nominal",
            inside_operating_point=TireOperatingPoint(445.0, 2.0, 69.0),
            outside_operating_point=self.outside,
            slip_utilization_by_sample=self.utilization,
        )
        with self.assertRaises(ValueError):
            build_tire_informed_operating_target_set(
                self.sampling,
                self.pose_set,
                self.grid,
                (definition,),
                target_set_id="TEST-CENSORED",
                version="0.1.0",
                wheelbase_m=self.geometry.wheelbase,
                steering_axis_track_m=self.geometry.steering_axis_track,
                authority="test",
            )

    def test_utilization_schedule_is_explicit_and_centered(self) -> None:
        bad = list(self.utilization)
        bad[self.sampling.inputs.index(0.0)] = 0.1
        definition = TireDifferentialStateDefinition(
            state_id="nominal",
            inside_operating_point=self.inside,
            outside_operating_point=self.outside,
            slip_utilization_by_sample=tuple(bad),
        )
        with self.assertRaises(ValueError):
            build_tire_informed_operating_target_set(
                self.sampling,
                self.pose_set,
                self.grid,
                (definition,),
                target_set_id="TEST-BAD-CENTER",
                version="0.1.0",
                wheelbase_m=self.geometry.wheelbase,
                steering_axis_track_m=self.geometry.steering_axis_track,
                authority="test",
            )


if __name__ == "__main__":
    unittest.main()
