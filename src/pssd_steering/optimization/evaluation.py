"""Analyzer-composed candidate evaluation for nominal steering inverse design.

This module adds no mechanism equations. It generates a candidate, evaluates the
complete target sweep through ``MOD-STEER-0001``, projects wheel headings through
the existing projection functions, keeps hard infeasibility separate from target
error, and reports traceable objective and constraint records.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from ..core import GeometryError, PositionResult, SteeringGeometry, solve_sweep
from ..projection import projected_wheel_heading, reference_from_static_alignment
from .geometry import CandidateGeometryError, GeneratedSteeringGeometry, generate_candidate_geometry
from .roles import RequirementSet, ResolvedCandidate, RoleResolutionError
from .targets import SteeringTarget


class CandidateEvaluationStatus(str, Enum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"


@dataclass(frozen=True)
class ConstraintResult:
    """One explicit hard-constraint disposition."""

    constraint_id: str
    passed: bool
    value: float | None
    lower_limit: float | None
    upper_limit: float | None
    margin: float | None
    unit: str
    state: str
    authority: str
    message: str


@dataclass(frozen=True)
class ObjectiveContribution:
    """One raw and normalized objective contribution."""

    objective_id: str
    raw_value: float
    raw_unit: str
    normalization_scale: float
    normalized_value: float
    weight: float
    weighted_contribution: float
    domain: str
    message: str


@dataclass(frozen=True)
class CandidateEvaluation:
    """Complete result for one generated candidate and target sweep."""

    candidate_id: str
    requirement_set_id: str
    target_id: str
    status: CandidateEvaluationStatus
    candidate_values: tuple[tuple[str, float], ...]
    generated: GeneratedSteeringGeometry | None
    analyzer_results: tuple[tuple[str, tuple[PositionResult, ...]], ...]
    target_inputs: tuple[float, ...]
    left_outputs: tuple[float, ...]
    right_outputs: tuple[float, ...]
    constraints: tuple[ConstraintResult, ...]
    objectives: tuple[ObjectiveContribution, ...]
    failure_code: str | None
    failure_message: str
    provenance: tuple[tuple[str, str], ...]

    @property
    def feasible(self) -> bool:
        return self.status is CandidateEvaluationStatus.FEASIBLE

    @property
    def total_objective(self) -> float | None:
        if not self.feasible or not self.objectives:
            return None
        return sum(item.weighted_contribution for item in self.objectives)

    @property
    def constraint_map(self) -> dict[str, ConstraintResult]:
        return {item.constraint_id: item for item in self.constraints}


def _constraint(
    constraint_id: str,
    passed: bool,
    *,
    value: float | None = None,
    lower: float | None = None,
    upper: float | None = None,
    margin: float | None = None,
    unit: str = "",
    state: str = "all",
    authority: str,
    message: str,
) -> ConstraintResult:
    return ConstraintResult(
        constraint_id=constraint_id,
        passed=passed,
        value=value,
        lower_limit=lower,
        upper_limit=upper,
        margin=margin,
        unit=unit,
        state=state,
        authority=authority,
        message=message,
    )


def _infeasible(
    candidate: ResolvedCandidate,
    requirement_set: RequirementSet,
    target: SteeringTarget,
    *,
    generated: GeneratedSteeringGeometry | None,
    analyzer_results: dict[str, list[PositionResult]] | None,
    constraints: list[ConstraintResult],
    failure_code: str,
    failure_message: str,
) -> CandidateEvaluation:
    result_items: tuple[tuple[str, tuple[PositionResult, ...]], ...] = ()
    if analyzer_results is not None:
        result_items = tuple(
            (side, tuple(analyzer_results.get(side, []))) for side in ("left", "right")
        )
    return CandidateEvaluation(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        target_id=target.target_id,
        status=CandidateEvaluationStatus.INFEASIBLE,
        candidate_values=candidate.values,
        generated=generated,
        analyzer_results=result_items,
        target_inputs=target.inputs,
        left_outputs=(),
        right_outputs=(),
        constraints=tuple(constraints),
        objectives=(),
        failure_code=failure_code,
        failure_message=failure_message,
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("target_source_type", target.source_type),
            ("target_source_path", target.source_path),
        ),
    )


def _weighted_rms(residuals: tuple[float, ...], weights: tuple[float, ...]) -> float:
    total_weight = sum(weights)
    return math.sqrt(sum(weight * value * value for weight, value in zip(weights, residuals)) / total_weight)


def evaluate_candidate(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    target: SteeringTarget,
) -> CandidateEvaluation:
    """Generate and fully evaluate one candidate without assigning infeasible scores."""

    constraints: list[ConstraintResult] = []
    try:
        generated = generate_candidate_geometry(baseline, requirement_set, candidate)
    except (CandidateGeometryError, RoleResolutionError, GeometryError, ValueError) as exc:
        constraints.append(
            _constraint(
                "candidate_geometry_preflight",
                False,
                authority="AUTH-STEER-0002 geometry-generator gate",
                message=str(exc),
            )
        )
        return _infeasible(
            candidate,
            requirement_set,
            target,
            generated=None,
            analyzer_results=None,
            constraints=constraints,
            failure_code="candidate_geometry_preflight",
            failure_message=str(exc),
        )

    geometry = generated.geometry
    target_min = min(target.rack_displacements)
    target_max = max(target.rack_displacements)
    domain_margin = min(
        target_min - geometry.rack.displacement_min,
        geometry.rack.displacement_max - target_max,
    )
    domain_passed = domain_margin >= 0.0
    constraints.append(
        _constraint(
            "rack_input_domain",
            domain_passed,
            value=max(abs(target_min), abs(target_max)),
            lower=geometry.rack.displacement_min,
            upper=geometry.rack.displacement_max,
            margin=domain_margin,
            unit="m",
            authority="Named baseline rack operational domain and target-provider no-extrapolation rule",
            message=(
                "All target rack states lie inside the declared analyzer domain"
                if domain_passed
                else "Target requires rack extrapolation, which is prohibited"
            ),
        )
    )
    if not domain_passed:
        return _infeasible(
            candidate,
            requirement_set,
            target,
            generated=generated,
            analyzer_results=None,
            constraints=constraints,
            failure_code="rack_input_domain",
            failure_message="Target rack states lie outside the declared operational domain",
        )

    solved = solve_sweep(geometry, target.rack_displacements)
    failed_states: list[PositionResult] = []
    for side in ("left", "right"):
        failed_states.extend(state for state in solved[side] if not state.ok)
    if failed_states:
        first = failed_states[0]
        code = first.failure_code.value if first.failure_code is not None else "unknown"
        constraints.append(
            _constraint(
                "complete_analyzer_sweep",
                False,
                value=first.rack_displacement,
                unit="m",
                state=f"{first.side}@{first.rack_displacement:.17g}m",
                authority="MOD-STEER-0001 branch-preserving rigid solver",
                message=f"{code}: {first.message}",
            )
        )
        return _infeasible(
            candidate,
            requirement_set,
            target,
            generated=generated,
            analyzer_results=solved,
            constraints=constraints,
            failure_code=code,
            failure_message=first.message,
        )

    minimum_singularity_ratio = min(
        state.singularity_ratio_to_reference
        for side in ("left", "right")
        for state in solved[side]
        if state.singularity_ratio_to_reference is not None
    )
    constraints.append(
        _constraint(
            "complete_analyzer_sweep",
            True,
            value=float(len(target.inputs) * 2),
            lower=float(len(target.inputs) * 2),
            margin=0.0,
            unit="states",
            authority="MOD-STEER-0001 branch-preserving rigid solver",
            message="Both sides solved at every target state without alternate-root substitution",
        )
    )
    constraints.append(
        _constraint(
            "minimum_singularity_ratio",
            True,
            value=minimum_singularity_ratio,
            lower=0.0,
            margin=minimum_singularity_ratio,
            unit="ratio",
            authority="MOD-STEER-0001 closure-Jacobian diagnostic",
            message="Analyzer accepted every state above its failure threshold",
        )
    )

    outputs: dict[str, tuple[float, ...]] = {}
    for side in ("left", "right"):
        corner = geometry.left if side == "left" else geometry.right
        reference = reference_from_static_alignment(
            side,
            toe_out=math.radians(target.static_toe_out_deg),
            camber=math.radians(target.static_camber_deg),
            source_role=f"{target.target_id} target-provider alignment",
        )
        values: list[float] = []
        try:
            for state in solved[side]:
                if state.upright_rotation is None:
                    raise GeometryError("Successful analyzer state is missing upright rotation")
                _, incremental = projected_wheel_heading(
                    corner, reference, state.upright_rotation
                )
                values.append(
                    target.canonical_to_target_output_sign * math.degrees(incremental)
                )
        except (GeometryError, ValueError) as exc:
            constraints.append(
                _constraint(
                    f"{side}_projected_heading",
                    False,
                    authority="MOD-STEER-0001 wheel-plane projection contract",
                    message=str(exc),
                )
            )
            return _infeasible(
                candidate,
                requirement_set,
                target,
                generated=generated,
                analyzer_results=solved,
                constraints=constraints,
                failure_code="projected_heading_unavailable",
                failure_message=str(exc),
            )
        outputs[side] = tuple(values)

    if target.require_monotonic_response:
        monotonic_specs = (
            ("left", target.left_monotonic_sign),
            ("right", target.right_monotonic_sign),
        )
        for side, expected_sign in monotonic_specs:
            signed_steps = tuple(
                expected_sign * (upper - lower)
                for lower, upper in zip(outputs[side], outputs[side][1:])
            )
            minimum_step = min(signed_steps)
            passed = minimum_step >= -target.monotonic_tolerance_deg
            constraints.append(
                _constraint(
                    f"{side}_monotonic_response",
                    passed,
                    value=minimum_step,
                    lower=-target.monotonic_tolerance_deg,
                    margin=minimum_step + target.monotonic_tolerance_deg,
                    unit="deg_per_sample",
                    authority="STEERING_INVERSE_DESIGN_DEV_V0 monotonic-response constraint",
                    message=(
                        "Response follows the target direction across the sweep"
                        if passed
                        else "Response reverses direction inside the target sweep"
                    ),
                )
            )
            if not passed:
                return _infeasible(
                    candidate,
                    requirement_set,
                    target,
                    generated=generated,
                    analyzer_results=solved,
                    constraints=constraints,
                    failure_code=f"{side}_nonmonotonic_response",
                    failure_message="Wheel response reverses direction inside the target domain",
                )

    left_residuals = tuple(
        actual - requested for actual, requested in zip(outputs["left"], target.left_outputs)
    )
    right_residuals = tuple(
        actual - requested for actual, requested in zip(outputs["right"], target.right_outputs)
    )
    combined_squared = tuple(
        0.5 * (left * left + right * right)
        for left, right in zip(left_residuals, right_residuals)
    )
    total_weight = sum(target.weights)
    raw_rms = math.sqrt(
        sum(weight * value for weight, value in zip(target.weights, combined_squared))
        / total_weight
    )
    normalized = raw_rms / target.normalization_scale_deg
    objective = ObjectiveContribution(
        objective_id="wheel_heading_target_error",
        raw_value=raw_rms,
        raw_unit="deg_rms",
        normalization_scale=target.normalization_scale_deg,
        normalized_value=normalized,
        weight=target.objective_weight,
        weighted_contribution=normalized * target.objective_weight,
        domain=(
            f"{len(target.inputs)} target states; left/right incremental projected heading"
        ),
        message=(
            f"left RMS={_weighted_rms(left_residuals, target.weights):.9g} deg, "
            f"right RMS={_weighted_rms(right_residuals, target.weights):.9g} deg, "
            f"max abs={max(abs(value) for value in left_residuals + right_residuals):.9g} deg"
        ),
    )

    return CandidateEvaluation(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        target_id=target.target_id,
        status=CandidateEvaluationStatus.FEASIBLE,
        candidate_values=candidate.values,
        generated=generated,
        analyzer_results=tuple(
            (side, tuple(solved[side])) for side in ("left", "right")
        ),
        target_inputs=target.inputs,
        left_outputs=outputs["left"],
        right_outputs=outputs["right"],
        constraints=tuple(constraints),
        objectives=(objective,),
        failure_code=None,
        failure_message="",
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("target_source_type", target.source_type),
            ("target_source_path", target.source_path),
            ("target_authority", target.authority),
        ),
    )
