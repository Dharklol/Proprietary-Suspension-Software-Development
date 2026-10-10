from dataclasses import replace
import json
import math
from pathlib import Path
import unittest

from pssd_suspension.geometry import Axle, Side, load_optimumk_geometry_snapshot
from pssd_suspension.kinematics import KinematicsStatus, solve_corner_state, UprightReferenceTransform
from pssd_steering.optimization.native_poses import NativePoseFrameMap, build_native_front_pose
from pssd_steering.optimization.poses import PoseDefinitionError
from pssd_steering import load_geometry, solve_corner_position
from pssd_steering.core import AxisLine, rotate_direction_about_axis, rotate_point_about_axis
from pssd_steering.optimization import (
    apply_pose_state, generate_candidate_geometry, load_requirement_set, resolve_candidate,
)

ROOT = Path(__file__).resolve().parents[1]


class NativePoseAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry = load_optimumk_geometry_snapshot(
            ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
        )
        cls.mapping = NativePoseFrameMap("steering_test", (0.7, -0.03, 0.2),
                                        "test_revision", "test_mapping")

    def states(self, q=0.0):
        return tuple(solve_corner_state(
            self.geometry.corner(Axle.FRONT, side), q,
            geometry_id=self.geometry.geometry_id, configuration_id="driver_no_fuel",
            source_authority=self.geometry.authority,
        ) for side in (Side.LEFT, Side.RIGHT))

    def pose(self, states, mapping=None):
        return build_native_front_pose(self.geometry, *states, state_id="test",
                                       frame_map=mapping or self.mapping)

    def test_nominal_identity_and_provenance(self):
        pose = self.pose(self.states())
        self.assertTrue(pose.is_identity_pose)
        self.assertEqual(pose.authority, self.geometry.authority)
        self.assertEqual(json.loads(pose.source_path)["configuration_id"], "driver_no_fuel")

    def test_nonzero_travel_origin_and_direction_parity(self):
        for q in (-0.02, 0.02):
            states = self.states(q)
            pose = self.pose(states)
            for side, state, transform in zip((Side.LEFT, Side.RIGHT), states,
                    (pose.left_transform, pose.right_transform)):
                self.assertTrue(state.ok)
                corner = self.geometry.corner(Axle.FRONT, side)
                points = ((corner.wishbone.lower_upright.position_m, state.lower_upright_m),
                          (corner.wishbone.upper_upright.position_m, state.upper_upright_m))
                offset = self.mapping.suspension_origin_in_steering_m
                for nominal, current in points:
                    actual = transform.apply_point(tuple(a + b for a, b in zip(nominal, offset)))
                    for a, b, o in zip(actual, current, offset):
                        self.assertAlmostEqual(a, b + o, places=9)
                for direction in ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)):
                    self.assertEqual(transform.apply_direction(direction),
                                     state.minimum_twist_transform.apply_direction(direction))

    def test_swapped_rear_failed_and_mismatched_states_rejected(self):
        left, right = self.states()
        cases = ((right, left), (replace(left, axle=Axle.REAR), right),
                 (replace(left, status=KinematicsStatus.FAILURE), right),
                 (replace(left, geometry_id="other"), right),
                 (replace(left, source_authority="other"), right),
                 (left, replace(right, configuration_id="other")),
                 (replace(left, minimum_twist_transform=None), right))
        for states in cases:
            with self.subTest(states=states), self.assertRaises(PoseDefinitionError):
                self.pose(states)

    def test_steering_resolved_role_and_hidden_twist_rejected(self):
        left, right = self.states()
        original = left.minimum_twist_transform
        for bad in (replace(original, source_role="steering_closed"),
                    UprightReferenceTransform(((0., -1., 0.), (1., 0., 0.), (0., 0., 1.)),
                                              original.translation_m)):
            with self.assertRaises(PoseDefinitionError):
                self.pose((replace(left, minimum_twist_transform=bad), right))

        axis = AxisLine(left.lower_upright_m, left.kingpin_direction)
        columns = [rotate_direction_about_axis(e, axis.direction, 0.1)
                   for e in ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))]
        rotation = tuple(tuple(column[i] for column in columns) for i in range(3))
        hidden = UprightReferenceTransform(rotation, rotate_point_about_axis((0., 0., 0.), axis, 0.1))
        # Both joints still agree; only the extra steering DOF is wrong.
        for point in (left.lower_upright_m, left.upper_upright_m):
            for a, b in zip(hidden.apply_point(point), point):
                self.assertAlmostEqual(a, b, places=10)
        with self.assertRaises(PoseDefinitionError):
            self.pose((replace(left, minimum_twist_transform=hidden), right))

    def test_explicit_finite_frame_mapping_required(self):
        for offset in ((float("nan"), 0., 0.), (0., 0.)):
            with self.assertRaises(PoseDefinitionError):
                NativePoseFrameMap("test", offset, "rev", "source")
        with self.assertRaises(PoseDefinitionError):
            NativePoseFrameMap("", (0., 0., 0.), "rev", "source")

    def test_wufr_nominal_frame_and_posed_steering_composition(self):
        baseline = load_geometry(ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml")
        requirements = load_requirement_set(ROOT / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
        generated = generate_candidate_geometry(
            baseline, requirements, resolve_candidate(requirements, candidate_id="NATIVE-REFERENCE")
        )
        # Reviewed WUFR source frames share this front origin. Check the actual
        # nominal axes before using a zero translation for this fixture only.
        for side, steering in ((Side.LEFT, baseline.left), (Side.RIGHT, baseline.right)):
            suspension = self.geometry.corner(Axle.FRONT, side).wishbone
            for a, b in zip(steering.steering_axis.point, suspension.lower_upright.position_m):
                self.assertAlmostEqual(a, b, places=12)
            direction = tuple(u - l for u, l in zip(
                suspension.upper_upright.position_m, suspension.lower_upright.position_m))
            length = math.sqrt(sum(value * value for value in direction))
            for a, b in zip(steering.steering_axis.direction, direction):
                self.assertAlmostEqual(a, b / length, places=12)
        mapping = NativePoseFrameMap("CANONICAL_ISO8855_BODY", (0., 0., 0.),
                                    "WUFR26_nominal_design_v0",
                                    "docs/conventions/wufr26_coordinate_frame_reconciliation.md")
        pairs = (self.states(0.), self.states(-0.02), self.states(0.02),
                 (self.states(0.02)[0], self.states(-0.01)[1]))
        for states in pairs:
            pose = self.pose(states, mapping)
            posed = apply_pose_state(generated, pose)
            self.assertEqual(posed.geometry.rack, generated.geometry.rack)
            for side, original, current, transform in (
                ("left", generated.geometry.left, posed.geometry.left, pose.left_transform),
                ("right", generated.geometry.right, posed.geometry.right, pose.right_transform),
            ):
                self.assertEqual(current.rack_inner_joint_at_center, original.rack_inner_joint_at_center)
                self.assertEqual(current.outer_tie_rod_joint_at_center,
                                 transform.apply_point(original.outer_tie_rod_joint_at_center))
                self.assertEqual(current.tie_rod_length, original.tie_rod_length)
                for rack in (-0.01, 0., 0.01):
                    result = solve_corner_position(posed.geometry, side, rack)
                    self.assertTrue(result.ok)
                    self.assertLess(abs(result.closure_length_residual), 1.e-8)


if __name__ == "__main__":
    unittest.main()
