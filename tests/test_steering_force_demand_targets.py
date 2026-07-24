from __future__ import annotations

from pathlib import Path
import unittest

from pssd_steering import load_geometry
from pssd_steering.derived import assign_inside_outside
from pssd_steering.optimization import load_historical_fit_target, load_pose_set
from pssd_steering.optimization.force_demand_targets import (
    ForceDemandStateDefinition,
    SteeringDifferentialRegime,
    build_force_demand_operating_target_set,
    classify_heading_pair,
    differential_heading_reference,
    force_demand_slip_differential,
)
from pssd_tire import TireOperatingPoint, load_lateral_force_branch_set


ROOT = Path(__file__).resolve().parents[1]


class SteeringForceDemandTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.geometry = load_geometry(
            ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
        )
        self.sampling = load_historical_fit_target(
            ROOT / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
        )
        self.pose_set = load_pose_set(
            ROOT / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
        )
        self.branch_set = load_lateral_force_branch_set(
            ROOT / "benchmarks/tires/SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml"
        )
        self.inside_point = TireOperatingPoint(222.0, 0.0, 83.0)
        self.outside_point = TireOperatingPoint(1112.0, 2.0, 83.0)

    def test_pr28_endpoint_is_pro_because_1p3_deg_does_not_close_ackermann_gap(self) -> None:
        reference = differential_heading_reference(
            32.18468832,
            wheelbase_m=self.geometry.wheelbase,
            steering_axis_track_m=self.geometry.steering_axis_track,
            slip_differential_deg=1.3,
        )
        self.assertAlmostEqual(22.868696046212865, reference.ackermann_outside_heading_magnitude_deg)
        self.assertAlmostEqual(9.315992273787135, reference.ackermann_inside_minus_outside_gap_deg)
        self.assertAlmostEqual(24.168696046212865, reference.corrected_outside_heading_magnitude_deg)
        self.assertAlmostEqual(8.015992273787135, reference.corrected_inside_minus_outside_gap_deg)
        self.assertEqual(SteeringDifferentialRegime.PRO_ACKERMANN, reference.regime)

    def test_pr28_near_center_can_already_cross_slightly_anti(self) -> None:
        inside_heading = 3.6966375
        utilization = 15.0 / 102.0
        reference = differential_heading_reference(
            inside_heading,
            wheelbase_m=self.geometry.wheelbase,
            steering_axis_track_m=self.geometry.steering_axis_track,
            slip_differential_deg=1.3 * utilization,
        )
        self.assertAlmostEqual(3.7104805345791045, reference.corrected_outside_heading_magnitude_deg)
        self.assertEqual(SteeringDifferentialRegime.ANTI_ACKERMANN, reference.regime)
        self.assertLess(reference.corrected_inside_minus_outside_gap_deg, 0.0)

    def test_force_demand_inversion_can_cross_from_anti_to_pro_with_steer_angle(self) -> None:
        differential = force_demand_slip_differential(
            self.branch_set,
            self.inside_point,
            self.outside_point,
            inside_lateral_force_magnitude_n=300.0,
            outside_lateral_force_magnitude_n=2500.0,
        )
        self.assertAlmostEqual(7.2142857142857135, differential.outside_minus_inside_slip_deg)

        moderate = differential_heading_reference(
            15.0,
            wheelbase_m=self.geometry.wheelbase,
            steering_axis_track_m=self.geometry.steering_axis_track,
            slip_differential_deg=differential.outside_minus_inside_slip_deg,
        )
        endpoint = differential_heading_reference(
            32.18468832,
            wheelbase_m=self.geometry.wheelbase,
            steering_axis_track_m=self.geometry.steering_axis_track,
            slip_differential_deg=differential.outside_minus_inside_slip_deg,
        )
        self.assertEqual(SteeringDifferentialRegime.ANTI_ACKERMANN, moderate.regime)
        self.assertEqual(SteeringDifferentialRegime.PRO_ACKERMANN, endpoint.regime)

    def test_explicit_force_schedule_builds_mixed_regime_target_without_prescribing_it(self) -> None:
        maximum_input = max(abs(value) for value in self.sampling.inputs)
        utilization = tuple(abs(value) / maximum_input for value in self.sampling.inputs)
        inside_force = tuple(300.0 * value for value in utilization)
        outside_force = tuple(2500.0 * value for value in utilization)
        definition = ForceDemandStateDefinition(
            state_id="nominal",
            inside_operating_point=self.inside_point,
            outside_operating_point=self.outside_point,
            inside_lateral_force_magnitude_by_sample=inside_force,
            outside_lateral_force_magnitude_by_sample=outside_force,
            authority="synthetic force-demand software verification only",
        )
        target_set = build_force_demand_operating_target_set(
            self.sampling,
            self.pose_set,
            self.branch_set,
            (definition,),
            target_set_id="SYNTHETIC-FORCE-DEMAND-TARGET",
            version="0.1.0",
            wheelbase_m=self.geometry.wheelbase,
            steering_axis_track_m=self.geometry.steering_axis_track,
            authority="test",
        )
        target = target_set.state_map["nominal"]
        sign = self.sampling.canonical_to_target_output_sign

        index_15 = self.sampling.inputs.index(15.0)
        assignment_15 = assign_inside_outside(
            sign * target.left_outputs[index_15],
            sign * target.right_outputs[index_15],
        )
        self.assertEqual(
            SteeringDifferentialRegime.ANTI_ACKERMANN,
            classify_heading_pair(
                assignment_15.inside_incremental_magnitude,
                assignment_15.outside_incremental_magnitude,
            ),
        )

        index_102 = self.sampling.inputs.index(102.0)
        assignment_102 = assign_inside_outside(
            sign * target.left_outputs[index_102],
            sign * target.right_outputs[index_102],
        )
        self.assertEqual(
            SteeringDifferentialRegime.PRO_ACKERMANN,
            classify_heading_pair(
                assignment_102.inside_incremental_magnitude,
                assignment_102.outside_incremental_magnitude,
            ),
        )

        provenance = dict(target.provenance)
        self.assertIn("anti_ackermann", provenance["regime_counts"])
        self.assertIn("pro_ackermann", provenance["regime_counts"])

    def test_force_schedule_rejects_out_of_branch_demand(self) -> None:
        count = len(self.sampling.inputs)
        inside = [100.0] * count
        outside = [1000.0] * count
        center = self.sampling.inputs.index(0.0)
        inside[center] = 0.0
        outside[center] = 0.0
        outside[-1] = 3000.0
        definition = ForceDemandStateDefinition(
            state_id="nominal",
            inside_operating_point=self.inside_point,
            outside_operating_point=self.outside_point,
            inside_lateral_force_magnitude_by_sample=tuple(inside),
            outside_lateral_force_magnitude_by_sample=tuple(outside),
        )
        with self.assertRaises(ValueError):
            build_force_demand_operating_target_set(
                self.sampling,
                self.pose_set,
                self.branch_set,
                (definition,),
                target_set_id="OUT-OF-RANGE",
                version="0.1.0",
                wheelbase_m=self.geometry.wheelbase,
                steering_axis_track_m=self.geometry.steering_axis_track,
                authority="test",
            )


if __name__ == "__main__":
    unittest.main()
