from __future__ import annotations

from pathlib import Path
import math
import unittest

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    evaluate_operating_state_candidate,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)
from pssd_steering.optimization.force_demand_targets import (
    ForceDemandStateDefinition,
    build_force_demand_operating_target_set,
)
from pssd_steering.optimization.motion_force_targets import (
    MotionAwareForceDemandStateDefinition,
    build_motion_aware_force_demand_operating_target_set,
    motion_aware_force_demand_heading_pair,
)
from pssd_tire import TireOperatingPoint, load_lateral_force_branch_set
from pssd_vehicle import FourWheelPlanarGeometry, PlanarMotionSample, PlanarMotionSchedule


ROOT = Path(__file__).resolve().parents[1]


class MotionAwareForceDemandTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.steering_geometry = load_geometry(
            ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
        )
        self.requirement = load_requirement_set(
            ROOT / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
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
        wheelbase = self.steering_geometry.wheelbase
        assert wheelbase is not None
        self.planar_geometry = FourWheelPlanarGeometry(
            cg_to_front_axle_m=0.8,
            cg_to_rear_axle_m=wheelbase - 0.8,
            front_wheel_center_track_m=1.2,
            rear_wheel_center_track_m=1.2,
            authority="synthetic wheel-center geometry for software verification only",
        )
        maximum_input = max(abs(value) for value in self.sampling.inputs)
        self.utilization = tuple(abs(value) / maximum_input for value in self.sampling.inputs)
        self.inside_force = tuple(300.0 * value for value in self.utilization)
        self.outside_force = tuple(2500.0 * value for value in self.utilization)

    def _motion_schedule(self, state_id: str, velocity_center_s_m: float) -> PlanarMotionSchedule:
        samples = []
        maximum_input = max(abs(value) for value in self.sampling.inputs)
        for input_deg in self.sampling.inputs:
            utilization = abs(input_deg) / maximum_input
            if input_deg == 0.0:
                samples.append(PlanarMotionSample(5.0, 0.0, 0.0))
                continue
            turn_sign = 1.0 if input_deg > 0.0 else -1.0
            yaw_rate = turn_sign * 2.0 * utilization
            lateral_velocity = -velocity_center_s_m * yaw_rate
            samples.append(PlanarMotionSample(5.0, lateral_velocity, yaw_rate))
        return PlanarMotionSchedule(
            state_id=state_id,
            samples=tuple(samples),
            authority="synthetic u-v-r schedule for software verification only",
            provenance=(("physical_authority", "none"),),
        )

    def _definition(self, state_id: str, velocity_center_s_m: float) -> MotionAwareForceDemandStateDefinition:
        return MotionAwareForceDemandStateDefinition(
            state_id=state_id,
            motion_schedule=self._motion_schedule(state_id, velocity_center_s_m),
            inside_operating_point=self.inside_point,
            outside_operating_point=self.outside_point,
            inside_lateral_force_magnitude_by_sample=self.inside_force,
            outside_lateral_force_magnitude_by_sample=self.outside_force,
            authority="synthetic motion-aware target verification only",
        )

    def test_same_tire_force_demands_can_change_ackermann_regime_with_velocity_center(self) -> None:
        a1 = self.planar_geometry.cg_to_front_axle_m
        a2 = self.planar_geometry.cg_to_rear_axle_m
        yaw_rate = 2.0
        u = 5.0

        rear_axle_velocity_center = PlanarMotionSample(
            u,
            -(-a2) * yaw_rate,
            yaw_rate,
        )
        front_axle_velocity_center = PlanarMotionSample(
            u,
            -(a1) * yaw_rate,
            yaw_rate,
        )
        rear_result = motion_aware_force_demand_heading_pair(
            rear_axle_velocity_center,
            self.planar_geometry,
            self.branch_set,
            self.inside_point,
            self.outside_point,
            inside_lateral_force_magnitude_n=300.0,
            outside_lateral_force_magnitude_n=2500.0,
            left_pose_reference_heading_rad=0.0,
            right_pose_reference_heading_rad=0.0,
        )
        front_result = motion_aware_force_demand_heading_pair(
            front_axle_velocity_center,
            self.planar_geometry,
            self.branch_set,
            self.inside_point,
            self.outside_point,
            inside_lateral_force_magnitude_n=300.0,
            outside_lateral_force_magnitude_n=2500.0,
            left_pose_reference_heading_rad=0.0,
            right_pose_reference_heading_rad=0.0,
        )

        self.assertEqual("pro_ackermann", rear_result.regime.value)
        self.assertEqual("anti_ackermann", front_result.regime.value)
        self.assertAlmostEqual(2.5, rear_result.left_required_slip_deg)
        self.assertAlmostEqual(9.714285714285714, rear_result.right_required_slip_deg)
        self.assertAlmostEqual(
            rear_result.left_required_slip_deg, front_result.left_required_slip_deg
        )
        self.assertAlmostEqual(
            rear_result.right_required_slip_deg, front_result.right_required_slip_deg
        )
        # S=a1 makes the front wheel-center velocity headings equal under the exact
        # planar kinematics; the unequal required tire slips then directly set anti-Ackermann.
        self.assertAlmostEqual(
            front_result.left_velocity_heading_deg,
            front_result.right_velocity_heading_deg,
            places=12,
        )

    def test_motion_aware_target_uses_velocity_heading_not_ackermann_anchor(self) -> None:
        definition = self._definition(
            "nominal", self.planar_geometry.cg_to_front_axle_m
        )
        motion_target_set = build_motion_aware_force_demand_operating_target_set(
            self.sampling,
            self.pose_set,
            self.planar_geometry,
            self.branch_set,
            (definition,),
            target_set_id="SYNTHETIC-MOTION-AWARE-TARGET",
            version="0.1.0",
            authority="test",
        )
        ackermann_definition = ForceDemandStateDefinition(
            state_id="nominal",
            inside_operating_point=self.inside_point,
            outside_operating_point=self.outside_point,
            inside_lateral_force_magnitude_by_sample=self.inside_force,
            outside_lateral_force_magnitude_by_sample=self.outside_force,
            authority="synthetic comparison only",
        )
        ackermann_target_set = build_force_demand_operating_target_set(
            self.sampling,
            self.pose_set,
            self.branch_set,
            (ackermann_definition,),
            target_set_id="SYNTHETIC-ACKERMANN-ANCHORED-TARGET",
            version="0.1.0",
            wheelbase_m=self.steering_geometry.wheelbase,
            steering_axis_track_m=self.steering_geometry.steering_axis_track,
            authority="test",
        )
        index = self.sampling.inputs.index(102.0)
        motion_target = motion_target_set.state_map["nominal"]
        ackermann_target = ackermann_target_set.state_map["nominal"]
        self.assertGreater(
            abs(motion_target.left_outputs[index] - ackermann_target.left_outputs[index])
            + abs(motion_target.right_outputs[index] - ackermann_target.right_outputs[index]),
            1.0,
        )
        provenance = dict(motion_target.provenance)
        self.assertEqual("false", provenance["ackermann_anchor_used"])
        self.assertEqual(
            "wheel_velocity_heading_plus_required_tire_slip",
            provenance["target_mapping"],
        )

    def test_two_motion_states_produce_different_regime_distributions(self) -> None:
        definitions = (
            self._definition("nominal", -self.planar_geometry.cg_to_rear_axle_m),
            self._definition(
                "symmetric_bump_5mm", self.planar_geometry.cg_to_front_axle_m
            ),
        )
        target_set = build_motion_aware_force_demand_operating_target_set(
            self.sampling,
            self.pose_set,
            self.planar_geometry,
            self.branch_set,
            definitions,
            target_set_id="SYNTHETIC-TWO-MOTION-STATES",
            version="0.1.0",
            authority="BENCH software evidence only",
        )
        rear_center = dict(target_set.state_map["nominal"].provenance)["regime_counts"]
        front_center = dict(target_set.state_map["symmetric_bump_5mm"].provenance)[
            "regime_counts"
        ]
        self.assertIn("pro_ackermann:14", rear_center)
        self.assertIn("anti_ackermann:0", rear_center)
        self.assertIn("anti_ackermann:10", front_center)
        self.assertIn("pro_ackermann:4", front_center)
        self.assertIn("parallel:1", rear_center)
        self.assertIn("parallel:1", front_center)

    def test_motion_aware_target_evaluates_through_existing_mechanism_solver(self) -> None:
        definitions = (
            self._definition("nominal", -self.planar_geometry.cg_to_rear_axle_m),
            self._definition(
                "symmetric_bump_5mm", self.planar_geometry.cg_to_front_axle_m
            ),
        )
        target_set = build_motion_aware_force_demand_operating_target_set(
            self.sampling,
            self.pose_set,
            self.planar_geometry,
            self.branch_set,
            definitions,
            target_set_id="SYNTHETIC-MOTION-AWARE-EVALUATION",
            version="0.1.0",
            authority="software verification only",
        )
        candidate = resolve_candidate(
            self.requirement, candidate_id="MOTION-AWARE-REFERENCE-CANDIDATE"
        )
        evaluation = evaluate_operating_state_candidate(
            self.steering_geometry,
            self.requirement,
            candidate,
            target_set,
            self.pose_set,
        )
        self.assertTrue(evaluation.feasible)
        self.assertIsNotNone(evaluation.total_objective)
        self.assertEqual(2, len(evaluation.objectives))

    def test_center_and_turn_direction_contracts_are_explicit(self) -> None:
        definition = self._definition(
            "nominal", -self.planar_geometry.cg_to_rear_axle_m
        )
        bad_center = list(definition.motion_schedule.samples)
        center = self.sampling.inputs.index(0.0)
        bad_center[center] = PlanarMotionSample(5.0, 0.0, 0.1)
        bad_definition = MotionAwareForceDemandStateDefinition(
            state_id="nominal",
            motion_schedule=PlanarMotionSchedule(
                state_id="nominal",
                samples=tuple(bad_center),
                authority="bad synthetic schedule",
            ),
            inside_operating_point=self.inside_point,
            outside_operating_point=self.outside_point,
            inside_lateral_force_magnitude_by_sample=self.inside_force,
            outside_lateral_force_magnitude_by_sample=self.outside_force,
        )
        with self.assertRaisesRegex(ValueError, "center sample must have zero yaw rate"):
            build_motion_aware_force_demand_operating_target_set(
                self.sampling,
                self.pose_set,
                self.planar_geometry,
                self.branch_set,
                (bad_definition,),
                target_set_id="BAD-CENTER",
                version="0.1.0",
                authority="test",
            )

        with self.assertRaisesRegex(ValueError, "requires nonzero yaw rate"):
            motion_aware_force_demand_heading_pair(
                PlanarMotionSample(5.0, 0.0, 0.0),
                self.planar_geometry,
                self.branch_set,
                self.inside_point,
                self.outside_point,
                inside_lateral_force_magnitude_n=100.0,
                outside_lateral_force_magnitude_n=1000.0,
                left_pose_reference_heading_rad=0.0,
                right_pose_reference_heading_rad=0.0,
            )


if __name__ == "__main__":
    unittest.main()
