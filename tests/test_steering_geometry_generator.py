from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from pssd_steering import load_geometry, solve_corner_position
from pssd_steering.core import add, distance
from pssd_steering.optimization import (
    CandidateGeometryError,
    ParameterRole,
    RoleResolutionError,
    generate_candidate_geometry,
    load_requirement_set,
    reflect_lateral,
    resolve_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
SOURCE_PATH = ROOT / "configurations" / "steering" / "WUFR26_DESIGN_NOMINAL_V0.toml"
REQUIREMENT_PATH = (
    ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
)


class SteeringGeometryGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_geometry(SOURCE_PATH)
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)

    def assertVecAlmostEqual(self, left, right, places: int = 14) -> None:  # noqa: N802
        for actual, expected in zip(left, right):
            self.assertAlmostEqual(actual, expected, places=places)

    def assertNumericallySameGeometry(self, left, right) -> None:  # noqa: N802
        self.assertVecAlmostEqual(left.rack.axis.point, right.rack.axis.point)
        self.assertVecAlmostEqual(left.rack.axis.direction, right.rack.axis.direction)
        self.assertAlmostEqual(left.rack.displacement_min, right.rack.displacement_min, places=14)
        self.assertAlmostEqual(left.rack.displacement_max, right.rack.displacement_max, places=14)
        self.assertEqual(left.wheelbase, right.wheelbase)
        self.assertEqual(left.steering_axis_track, right.steering_axis_track)
        for left_corner, right_corner in ((left.left, right.left), (left.right, right.right)):
            self.assertVecAlmostEqual(left_corner.steering_axis.point, right_corner.steering_axis.point)
            self.assertVecAlmostEqual(
                left_corner.steering_axis.direction, right_corner.steering_axis.direction
            )
            self.assertVecAlmostEqual(
                left_corner.rack_inner_joint_at_center,
                right_corner.rack_inner_joint_at_center,
            )
            self.assertVecAlmostEqual(
                left_corner.outer_tie_rod_joint_at_center,
                right_corner.outer_tie_rod_joint_at_center,
            )
            self.assertAlmostEqual(left_corner.tie_rod_length, right_corner.tie_rod_length, places=14)
            self.assertEqual(left_corner.static_toe, right_corner.static_toe)

    def test_inherited_wufr27_baseline_is_numerically_identical_to_source(self) -> None:
        self.assertEqual("WUFR27_STEERING_BASELINE_V0", self.baseline.geometry_id)
        self.assertEqual("WUFR26_DESIGN_NOMINAL_V0", self.source.geometry_id)
        self.assertNumericallySameGeometry(self.baseline, self.source)
        self.assertEqual(
            "WUFR26_DESIGN_NOMINAL_V0", self.baseline.metadata["inherited_geometry_id"]
        )

    def test_requirement_set_has_role_selectable_variables_and_explicit_frame(self) -> None:
        self.assertEqual("MOD-STEER-0001", self.requirement.evaluator_model_id)
        self.assertEqual("exact_reflection", self.requirement.symmetry_mode)
        self.assertFalse(self.requirement.independent_sides_enabled)
        self.assertEqual(6, len(self.requirement.variables))
        depth = self.requirement.variable("outer_pickup_local_depth_offset")
        self.assertEqual(ParameterRole.BOUNDED_DESIGN_VARIABLE, depth.role)
        self.assertEqual(-0.005, depth.minimum)
        self.assertEqual(0.005, depth.maximum)
        frame = self.requirement.outer_pickup_frame
        self.assertEqual((1.0, 0.0, 0.0), frame.u_direction)
        self.assertEqual((0.0, 0.0, 1.0), frame.v_direction)
        self.assertEqual((0.0, -1.0, 0.0), frame.depth_direction)

    def test_zero_offset_candidate_reconstructs_baseline_numerically(self) -> None:
        candidate = resolve_candidate(self.requirement, candidate_id="ZERO-OFFSET")
        generated = generate_candidate_geometry(self.baseline, self.requirement, candidate)
        self.assertNumericallySameGeometry(generated.geometry, self.baseline)
        self.assertTrue(generated.left_reference_result.ok)
        self.assertTrue(generated.right_reference_result.ok)
        self.assertAlmostEqual(
            generated.left_tie_rod_length,
            distance(
                generated.geometry.left.rack_inner_joint_at_center,
                generated.geometry.left.outer_tie_rod_joint_at_center,
            ),
            places=14,
        )
        self.assertAlmostEqual(
            generated.right_tie_rod_length,
            distance(
                generated.geometry.right.rack_inner_joint_at_center,
                generated.geometry.right.outer_tie_rod_joint_at_center,
            ),
            places=14,
        )
        self.assertIn("candidate_values", generated.geometry.metadata)
        self.assertEqual("MOD-STEER-0001", generated.geometry.metadata["evaluator_model_id"])

    def test_candidate_offsets_apply_in_declared_frames_and_reflect_exactly(self) -> None:
        overrides = {
            "rack_longitudinal_offset": 0.010,
            "rack_vertical_offset": -0.020,
            "rack_inner_joint_half_spacing": 0.250,
            "outer_pickup_local_u_offset": 0.012,
            "outer_pickup_local_v_offset": -0.009,
            "outer_pickup_local_depth_offset": 0.004,
        }
        candidate = resolve_candidate(
            self.requirement, overrides, candidate_id="OFFSET-CANDIDATE"
        )
        generated = generate_candidate_geometry(self.baseline, self.requirement, candidate)
        geometry = generated.geometry
        self.assertVecAlmostEqual(
            geometry.rack.axis.point,
            (
                self.baseline.rack.axis.point[0] + 0.010,
                0.0,
                self.baseline.rack.axis.point[2] - 0.020,
            ),
        )
        self.assertAlmostEqual(0.250, geometry.left.rack_inner_joint_at_center[1], places=14)
        self.assertAlmostEqual(-0.250, geometry.right.rack_inner_joint_at_center[1], places=14)
        expected_left_outer = (
            self.baseline.left.outer_tie_rod_joint_at_center[0] + 0.012,
            self.baseline.left.outer_tie_rod_joint_at_center[1] - 0.004,
            self.baseline.left.outer_tie_rod_joint_at_center[2] - 0.009,
        )
        self.assertVecAlmostEqual(
            geometry.left.outer_tie_rod_joint_at_center, expected_left_outer
        )
        self.assertVecAlmostEqual(
            geometry.right.outer_tie_rod_joint_at_center,
            reflect_lateral(expected_left_outer),
        )
        self.assertAlmostEqual(
            generated.left_tie_rod_length, generated.right_tie_rod_length, places=14
        )

    def test_outer_pickup_depth_is_strictly_bounded(self) -> None:
        with self.assertRaises(RoleResolutionError):
            resolve_candidate(
                self.requirement,
                {"outer_pickup_local_depth_offset": 0.005001},
                candidate_id="BAD-DEPTH",
            )

    def test_role_can_change_from_variable_to_fixed_without_generator_change(self) -> None:
        variables = []
        for variable in self.requirement.variables:
            if variable.id == "outer_pickup_local_depth_offset":
                variables.append(replace(variable, role=ParameterRole.FIXED_PARAMETER))
            else:
                variables.append(variable)
        fixed_requirement = replace(self.requirement, variables=tuple(variables))
        fixed_candidate = resolve_candidate(fixed_requirement, candidate_id="FIXED-DEPTH")
        generated = generate_candidate_geometry(
            self.baseline, fixed_requirement, fixed_candidate
        )
        self.assertTrue(generated.left_reference_result.ok)
        with self.assertRaises(RoleResolutionError):
            resolve_candidate(
                fixed_requirement,
                {"outer_pickup_local_depth_offset": 0.001},
                candidate_id="ILLEGAL-FIXED-OVERRIDE",
            )

    def test_tie_rod_length_cannot_be_supplied_independently(self) -> None:
        with self.assertRaisesRegex(RoleResolutionError, "derived output"):
            resolve_candidate(
                self.requirement,
                {"left_tie_rod_length": 0.300},
                candidate_id="DOUBLE-SPECIFIED-LENGTH",
            )

    def test_unknown_candidate_parameter_is_rejected(self) -> None:
        with self.assertRaisesRegex(RoleResolutionError, "Unknown candidate override"):
            resolve_candidate(
                self.requirement,
                {"invented_hardpoint": 1.0},
                candidate_id="UNKNOWN-PARAMETER",
            )

    def test_asymmetric_baseline_fails_before_analyzer_sweep(self) -> None:
        bad_right = replace(
            self.baseline.right,
            outer_tie_rod_joint_at_center=add(
                self.baseline.right.outer_tie_rod_joint_at_center, (0.001, 0.0, 0.0)
            ),
        )
        bad_baseline = replace(self.baseline, right=bad_right)
        candidate = resolve_candidate(self.requirement, candidate_id="BAD-BASELINE")
        with self.assertRaisesRegex(CandidateGeometryError, "not the exact reflection"):
            generate_candidate_geometry(bad_baseline, self.requirement, candidate)

    def test_reference_preflight_calls_existing_analyzer_for_each_side(self) -> None:
        candidate = resolve_candidate(self.requirement, candidate_id="ANALYZER-COMPOSITION")
        with patch(
            "pssd_steering.optimization.geometry.solve_corner_position",
            wraps=solve_corner_position,
        ) as analyzer_call:
            generated = generate_candidate_geometry(
                self.baseline, self.requirement, candidate
            )
        self.assertEqual(2, analyzer_call.call_count)
        self.assertTrue(generated.left_reference_result.ok)
        self.assertTrue(generated.right_reference_result.ok)

    def test_generated_reference_rotations_remain_centered(self) -> None:
        candidate = resolve_candidate(self.requirement, candidate_id="REFERENCE-ROTATION")
        generated = generate_candidate_geometry(self.baseline, self.requirement, candidate)
        self.assertTrue(
            math.isclose(
                generated.left_reference_result.upright_rotation or 0.0,
                self.baseline.left.reference_upright_rotation,
                abs_tol=1.0e-12,
            )
        )
        self.assertTrue(
            math.isclose(
                generated.right_reference_result.upright_rotation or 0.0,
                self.baseline.right.reference_upright_rotation,
                abs_tol=1.0e-12,
            )
        )


if __name__ == "__main__":
    unittest.main()
