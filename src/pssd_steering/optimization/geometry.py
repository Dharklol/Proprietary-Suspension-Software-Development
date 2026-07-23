"""Parametric steering geometry generation authorized by AUTH-STEER-0002.

The generator performs coordinate transforms and role-resolved parameter
application only. Every generated geometry is expressed through the public
``MOD-STEER-0001`` data contract and preflighted by the existing analyzer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math

from ..core import (
    AxisLine,
    GeometryError,
    PositionResult,
    RackGeometry,
    SteeringGeometry,
    add,
    closure_length_residual,
    distance,
    scale,
    solve_corner_position,
)
from .roles import RequirementSet, ResolvedCandidate, RoleResolutionError

Vec3 = tuple[float, float, float]


class CandidateGeometryError(GeometryError):
    """Raised when a role-resolved candidate cannot form a valid mechanism."""


@dataclass(frozen=True)
class GeneratedSteeringGeometry:
    """Generated geometry plus the analyzer's centered-state preflight results."""

    candidate_id: str
    requirement_set_id: str
    baseline_geometry_id: str
    geometry: SteeringGeometry
    left_tie_rod_length: float
    right_tie_rod_length: float
    left_reference_result: PositionResult
    right_reference_result: PositionResult
    candidate_values: tuple[tuple[str, float], ...]


def reflect_lateral(value: Vec3) -> Vec3:
    """Reflect a body-frame point or free vector across the vehicle center plane."""

    return (value[0], -value[1], value[2])


def _close_scalar(a: float, b: float, tolerance: float) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)


def _close_vec(a: Vec3, b: Vec3, tolerance: float) -> bool:
    return all(_close_scalar(left, right, tolerance) for left, right in zip(a, b))


def _shift_body_xz(point: Vec3, longitudinal: float, vertical: float) -> Vec3:
    return (point[0] + longitudinal, point[1], point[2] + vertical)


def _validate_baseline_reflection(
    baseline: SteeringGeometry, *, tolerance: float = 1.0e-12
) -> None:
    """Verify the exact design-model symmetry required by the first release."""

    rack_axis = baseline.rack.axis
    if not _close_scalar(rack_axis.point[1], 0.0, tolerance):
        raise CandidateGeometryError("Rack-axis origin must lie on the vehicle center plane")
    if not (
        _close_scalar(rack_axis.direction[0], 0.0, tolerance)
        and _close_scalar(rack_axis.direction[2], 0.0, tolerance)
        and rack_axis.direction[1] > 0.0
    ):
        raise CandidateGeometryError(
            "The first symmetric generator requires a lateral +y rack-axis direction"
        )

    reflection_pairs = (
        (
            "steering-axis point",
            baseline.right.steering_axis.point,
            reflect_lateral(baseline.left.steering_axis.point),
        ),
        (
            "steering-axis direction",
            baseline.right.steering_axis.direction,
            reflect_lateral(baseline.left.steering_axis.direction),
        ),
        (
            "rack inner joint",
            baseline.right.rack_inner_joint_at_center,
            reflect_lateral(baseline.left.rack_inner_joint_at_center),
        ),
        (
            "outer tie-rod joint",
            baseline.right.outer_tie_rod_joint_at_center,
            reflect_lateral(baseline.left.outer_tie_rod_joint_at_center),
        ),
    )
    for name, actual, expected in reflection_pairs:
        if not _close_vec(actual, expected, tolerance):
            raise CandidateGeometryError(
                f"Baseline right {name} is not the exact reflection of the left"
            )

    left_forward = baseline.left.wheel_forward_direction_at_center
    right_forward = baseline.right.wheel_forward_direction_at_center
    if (left_forward is None) != (right_forward is None):
        raise CandidateGeometryError("Wheel-forward basis availability must be symmetric")
    if left_forward is not None and right_forward is not None:
        if not _close_vec(right_forward, reflect_lateral(left_forward), tolerance):
            raise CandidateGeometryError("Wheel-forward bases are not exact reflections")

    left_toe = baseline.left.static_toe
    right_toe = baseline.right.static_toe
    if (left_toe is None) != (right_toe is None):
        raise CandidateGeometryError("Static-toe availability must be symmetric")
    if left_toe is not None and right_toe is not None:
        if not _close_scalar(left_toe, right_toe, tolerance):
            raise CandidateGeometryError(
                "Side-local static-toe values must match under exact reflection"
            )

    if "mirror" not in baseline.right.source_role.lower():
        raise CandidateGeometryError(
            "The right baseline source role must identify reviewed reflected geometry"
        )


def _required_value(candidate: ResolvedCandidate, variable_id: str) -> float:
    try:
        return candidate.value(variable_id)
    except RoleResolutionError as exc:
        raise CandidateGeometryError(str(exc)) from exc


def generate_candidate_geometry(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    *,
    symmetry_tolerance: float = 1.0e-12,
    closure_tolerance: float = 1.0e-12,
) -> GeneratedSteeringGeometry:
    """Generate and analyzer-preflight one symmetric nominal-height candidate.

    No optimizer search is performed. Tie-rod lengths are derived from the
    generated reference joint centers. The centered state is solved by the
    existing analyzer so branch or singular reference states fail before a
    later sweep can begin.
    """

    if requirement_set.evaluator_model_id != "MOD-STEER-0001":
        raise CandidateGeometryError(
            "The first generator must target the authoritative MOD-STEER-0001 analyzer"
        )
    if requirement_set.symmetry_mode != "exact_reflection":
        raise CandidateGeometryError("Only exact_reflection symmetry is authorized")
    if requirement_set.independent_sides_enabled:
        raise CandidateGeometryError("Independent left/right variables are not authorized")
    if candidate.requirement_set_id != requirement_set.id:
        raise CandidateGeometryError(
            "Candidate requirement-set identity does not match the loaded requirement set"
        )
    if baseline.geometry_id != requirement_set.baseline_configuration_id:
        raise CandidateGeometryError(
            f"Baseline geometry {baseline.geometry_id!r} does not match "
            f"{requirement_set.baseline_configuration_id!r}"
        )

    _validate_baseline_reflection(baseline, tolerance=symmetry_tolerance)

    rack_longitudinal = _required_value(candidate, "rack_longitudinal_offset")
    rack_vertical = _required_value(candidate, "rack_vertical_offset")
    half_spacing = _required_value(candidate, "rack_inner_joint_half_spacing")
    outer_u = _required_value(candidate, "outer_pickup_local_u_offset")
    outer_v = _required_value(candidate, "outer_pickup_local_v_offset")
    outer_depth = _required_value(candidate, "outer_pickup_local_depth_offset")

    if half_spacing <= 0.0:
        raise CandidateGeometryError("Rack inner-joint half-spacing must be positive")

    shifted_rack_origin = _shift_body_xz(
        baseline.rack.axis.point, rack_longitudinal, rack_vertical
    )
    generated_rack_axis = AxisLine(shifted_rack_origin, baseline.rack.axis.direction)
    left_inner = add(shifted_rack_origin, scale(generated_rack_axis.direction, half_spacing))
    right_inner = reflect_lateral(left_inner)
    if left_inner[1] <= symmetry_tolerance or right_inner[1] >= -symmetry_tolerance:
        raise CandidateGeometryError("Generated rack joints must remain on their named sides")

    frame = requirement_set.outer_pickup_frame
    left_outer = baseline.left.outer_tie_rod_joint_at_center
    left_outer = add(left_outer, scale(frame.u_direction, outer_u))
    left_outer = add(left_outer, scale(frame.v_direction, outer_v))
    left_outer = add(left_outer, scale(frame.depth_direction, outer_depth))
    right_outer = reflect_lateral(left_outer)
    if left_outer[1] <= symmetry_tolerance or right_outer[1] >= -symmetry_tolerance:
        raise CandidateGeometryError("Generated outer joints must remain on their named sides")

    left_length = distance(left_inner, left_outer)
    right_length = distance(right_inner, right_outer)
    if not math.isfinite(left_length) or left_length <= 1.0e-6:
        raise CandidateGeometryError("Generated left tie-rod length is invalid")
    if not _close_scalar(left_length, right_length, symmetry_tolerance):
        raise CandidateGeometryError("Exact reflection did not produce equal tie-rod lengths")

    rack = RackGeometry(
        axis=generated_rack_axis,
        displacement_min=baseline.rack.displacement_min,
        displacement_max=baseline.rack.displacement_max,
        geometric_branch_limit_magnitude=baseline.rack.geometric_branch_limit_magnitude,
        domain_role=baseline.rack.domain_role,
    )
    left = replace(
        baseline.left,
        rack_inner_joint_at_center=left_inner,
        outer_tie_rod_joint_at_center=left_outer,
        tie_rod_length=left_length,
        source_role=f"generated_from:{baseline.left.source_role}",
    )
    right = replace(
        baseline.right,
        rack_inner_joint_at_center=right_inner,
        outer_tie_rod_joint_at_center=right_outer,
        tie_rod_length=right_length,
        source_role="generated_exact_reflection_from_left",
    )

    metadata = dict(baseline.metadata)
    metadata.update(
        {
            "candidate_id": candidate.candidate_id,
            "requirement_set_id": requirement_set.id,
            "baseline_geometry_id": baseline.geometry_id,
            "baseline_geometry_version": baseline.version,
            "candidate_values": json.dumps(dict(candidate.values), sort_keys=True),
            "candidate_units": json.dumps(dict(candidate.units), sort_keys=True),
            "outer_pickup_frame_authority": frame.authority,
            "symmetry": "exact_reflection",
            "tie_rod_length_role": "derived_output",
            "evaluator_model_id": "MOD-STEER-0001",
        }
    )
    geometry = SteeringGeometry(
        geometry_id=f"{requirement_set.id}:{candidate.candidate_id}",
        version=requirement_set.version,
        rack=rack,
        left=left,
        right=right,
        wheelbase=baseline.wheelbase,
        steering_axis_track=baseline.steering_axis_track,
        metadata=metadata,
    )

    for corner in (geometry.left, geometry.right):
        residual = closure_length_residual(
            corner,
            geometry.rack,
            0.0,
            corner.reference_upright_rotation,
        )
        if abs(residual) > closure_tolerance:
            raise CandidateGeometryError(
                f"Generated {corner.side} reference closure residual {residual} m exceeds "
                f"{closure_tolerance} m"
            )

    left_reference = solve_corner_position(geometry, "left", 0.0)
    right_reference = solve_corner_position(geometry, "right", 0.0)
    for result in (left_reference, right_reference):
        if not result.ok:
            code = result.failure_code.value if result.failure_code is not None else "unknown"
            raise CandidateGeometryError(
                f"Analyzer rejected generated {result.side} reference state: {code}: "
                f"{result.message}"
            )

    return GeneratedSteeringGeometry(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        baseline_geometry_id=baseline.geometry_id,
        geometry=geometry,
        left_tie_rod_length=left_length,
        right_tie_rod_length=right_length,
        left_reference_result=left_reference,
        right_reference_result=right_reference,
        candidate_values=candidate.values,
    )
