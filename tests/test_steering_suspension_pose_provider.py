from __future__ import annotations

from pathlib import Path
import unittest

from pssd_steering import load_geometry, solve_sweep
from pssd_steering.optimization import (
    PoseDefinitionError,
    RigidTransform,
    SteeringPoseState,
    SuspensionPoseSet,
    apply_pose_state,
    evaluate_candidate_over_pose_set,
    generate_candidate_geometry,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
TARGET_PATH = ROOT / "benchmarks" / "steering" / "WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
POSE_SET_PATH = ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_POSE_SET_V0.toml"


class SteeringSuspensionPoseProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)
        cls.target = load_historical_fit_target(TARGET_PATH)
        cls.pose_set = load_pose_set(POSE_SET_PATH)
        cls.candidate = resolve_candidate(cls.requirement, candidate_id="POSE-REFERENCE")
        cls.generated = generate_candidate_geometry(cls.baseline, cls.requirement, cls.candidate)

    def test_pose_set_contract_is_nonphysical_and_steering_dof_excluded(self) -> None:
        self.assertEqual("nominal", self.pose_set.nominal_state_id)
        self.assertEqual(3, len(self.pose_set.states))
        self.assertIn("Software verification", self.pose_set.authority)
        for state in self.pose_set.states:
            self.assertIn("excludes_tie_rod_steering_rotation", state.steering_dof_rule)

    def test_pose_with_wrong_steering_dof_rule_is_rejected(self) -> None:
        with self.assertRaises(PoseDefinitionError):
            SteeringPoseState(
                state_id="bad",
                left_transform=RigidTransform.identity(),
                right_transform=RigidTransform.identity(),
                steering_dof_rule="source_already_contains_bump_steer",
            )

    def test_identity_pose_preserves_mechanism_and_center_solution(self) -> None:
        posed = apply_pose_state(self.generated, self.pose_set.state("nominal"))
        self.assertEqual(self.generated.geometry.rack, posed.geometry.rack)
        self.assertEqual(
            self.generated.geometry.left.rack_inner_joint_at_center,
            posed.geometry.left.rack_inner_joint_at_center,
        )
        self.assertEqual(
            self.generated.geometry.right.rack_inner_joint_at_center,
            posed.geometry.right.rack_inner_joint_at_center,
        )
        self.assertEqual(
            self.generated.geometry.left.outer_tie_rod_joint_at_center,
            posed.geometry.left.outer_tie_rod_joint_at_center,
        )
        self.assertEqual(
            self.generated.geometry.left.steering_axis,
            posed.geometry.left.steering_axis,
        )
        self.assertAlmostEqual(0.0, posed.left_center_result.upright_rotation or 0.0, places=10)
        self.assertAlmostEqual(0.0, posed.right_center_result.upright_rotation or 0.0, places=10)
        self.assertEqual(
            self.generated.geometry.steering_axis_track,
            posed.geometry.steering_axis_track,
        )

    def test_bump_pose_moves_upright_bound_geometry_but_not_rack(self) -> None:
        posed = apply_pose_state(self.generated, self.pose_set.state("symmetric_bump_5mm"))
        nominal = self.generated.geometry
        self.assertEqual(nominal.left.rack_inner_joint_at_center, posed.geometry.left.rack_inner_joint_at_center)
        self.assertEqual(nominal.right.rack_inner_joint_at_center, posed.geometry.right.rack_inner_joint_at_center)
        self.assertAlmostEqual(
            nominal.left.outer_tie_rod_joint_at_center[2] + 0.005,
            posed.geometry.left.outer_tie_rod_joint_at_center[2],
            places=12,
        )
        self.assertAlmostEqual(
            nominal.left.steering_axis.point[2] + 0.005,
            posed.geometry.left.steering_axis.point[2],
            places=12,
        )
        self.assertAlmostEqual(nominal.left.tie_rod_length, posed.geometry.left.tie_rod_length, places=14)
        self.assertGreater(abs(posed.left_center_result.upright_rotation or 0.0), 1.0e-8)
        self.assertGreater(abs(posed.right_center_result.upright_rotation or 0.0), 1.0e-8)
        self.assertIsNone(posed.geometry.steering_axis_track)

    def test_operating_pose_can_be_asymmetric_with_symmetric_design_geometry(self) -> None:
        posed = apply_pose_state(self.generated, self.pose_set.state("opposed_travel_5mm"))
        nominal = self.generated.geometry
        self.assertAlmostEqual(
            nominal.left.outer_tie_rod_joint_at_center[2] + 0.005,
            posed.geometry.left.outer_tie_rod_joint_at_center[2],
            places=12,
        )
        self.assertAlmostEqual(
            nominal.right.outer_tie_rod_joint_at_center[2] - 0.005,
            posed.geometry.right.outer_tie_rod_joint_at_center[2],
            places=12,
        )

    def test_valid_pose_can_produce_infeasible_steering_state_without_becoming_invalid_pose(self) -> None:
        far_transform = RigidTransform(
            rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            translation_m=(0.0, 0.0, 1.0),
            source_role="deliberate_infeasible_state",
        )
        far_state = SteeringPoseState(
            state_id="far_vertical_translation",
            left_transform=far_transform,
            right_transform=far_transform,
            authority="Deliberate mechanism-infeasibility benchmark only",
        )
        posed = apply_pose_state(self.generated, far_state)
        self.assertFalse(posed.left_center_result.ok)
        self.assertFalse(posed.right_center_result.ok)

        pose_set = SuspensionPoseSet(
            pose_set_id="POSE-INFEASIBILITY-TEST",
            version="0.1.0",
            nominal_state_id="nominal",
            states=(self.pose_set.state("nominal"), far_state),
            source_path="synthetic test",
            authority="software verification only",
        )
        result = evaluate_candidate_over_pose_set(
            self.baseline,
            self.requirement,
            self.candidate,
            self.target,
            pose_set,
        )
        self.assertFalse(result.feasible)
        failed = result.state_map["far_vertical_translation"]
        self.assertFalse(failed.feasible)
        self.assertIsNotNone(failed.failure_code)
        self.assertEqual((), failed.left_total_heading_deg)
        self.assertEqual((), failed.right_total_heading_deg)

    def test_identity_pose_sweep_matches_direct_analyzer_upright_rotations(self) -> None:
        posed = apply_pose_state(self.generated, self.pose_set.state("nominal"))
        direct = solve_sweep(self.generated.geometry, self.target.rack_displacements)
        via_pose = solve_sweep(posed.geometry, self.target.rack_displacements)
        for side in ("left", "right"):
            self.assertEqual([item.ok for item in direct[side]], [item.ok for item in via_pose[side]])
            for expected, actual in zip(direct[side], via_pose[side]):
                self.assertAlmostEqual(expected.upright_rotation or 0.0, actual.upright_rotation or 0.0, places=12)

    def test_multistate_evaluation_reports_dynamic_toe_from_analyzer(self) -> None:
        result = evaluate_candidate_over_pose_set(
            self.baseline,
            self.requirement,
            self.candidate,
            self.target,
            self.pose_set,
        )
        self.assertTrue(result.feasible)
        self.assertEqual(3, len(result.states))
        nominal = result.state_map["nominal"]
        bump = result.state_map["symmetric_bump_5mm"]
        opposed = result.state_map["opposed_travel_5mm"]
        self.assertAlmostEqual(0.0, nominal.center_left_side_local_toe_out_change_deg or 0.0, places=12)
        self.assertAlmostEqual(0.0, nominal.center_right_side_local_toe_out_change_deg or 0.0, places=12)
        self.assertGreater(abs(bump.center_left_side_local_toe_out_change_deg or 0.0), 1.0e-6)
        self.assertAlmostEqual(
            bump.center_left_side_local_toe_out_change_deg or 0.0,
            bump.center_right_side_local_toe_out_change_deg or 0.0,
            places=8,
        )
        self.assertNotAlmostEqual(
            opposed.center_left_side_local_toe_out_change_deg or 0.0,
            opposed.center_right_side_local_toe_out_change_deg or 0.0,
            places=6,
        )
        for state in result.states:
            self.assertIsNotNone(state.minimum_singularity_ratio)
            self.assertEqual(len(self.target.rack_displacements), len(state.left_total_heading_deg))
            self.assertEqual(len(self.target.rack_displacements), len(state.right_total_heading_deg))


if __name__ == "__main__":
    unittest.main()
