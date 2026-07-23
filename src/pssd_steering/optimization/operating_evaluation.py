"""Aggregate explicit suspension-state steering targets for one candidate.

The evaluator composes the existing multi-state pose evaluation and introduces no
new steering or suspension equations.  It only compares analyzer-produced wheel
headings against explicit per-state targets and sums their normalized objective
contributions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from ..core import GeometryError, SteeringGeometry
from .evaluation import CandidateEvaluationStatus, ConstraintResult, ObjectiveContribution
from .geometry import CandidateGeometryError
from .multistate import MultiStateSteeringEvaluation, evaluate_candidate_over_pose_set
from .operating_targets import OperatingStateTargetSet, OperatingTargetRole
from .poses import PoseDefinitionError, SuspensionPoseSet
from .roles import RequirementSet, ResolvedCandidate, RoleResolutionError


@dataclass(frozen=True)
class OperatingStateCandidateEvaluation:
    """Complete multi-state candidate result used by the operating-state search."""

    candidate_id: str
    requirement_set_id: str
    target_set_id: str
    pose_set_id: str
    status: CandidateEvaluationStatus
    candidate_values: tuple[tuple[str, float], ...]
    multistate: MultiStateSteeringEvaluation | None
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


def _weighted_rms(residuals: tuple[float, ...], weights: tuple[float, ...]) -> float:
    total = sum(weights)
    return math.sqrt(sum(weight * value * value for weight, value in zip(weights, residuals)) / total)


def _infeasible(
    candidate: ResolvedCandidate,
    requirement_set: RequirementSet,
    target_set: OperatingStateTargetSet,
    pose_set: SuspensionPoseSet,
    *,
    multistate: MultiStateSteeringEvaluation | None,
    constraints: list[ConstraintResult],
    failure_code: str,
    failure_message: str,
) -> OperatingStateCandidateEvaluation:
    return OperatingStateCandidateEvaluation(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        target_set_id=target_set.target_set_id,
        pose_set_id=pose_set.pose_set_id,
        status=CandidateEvaluationStatus.INFEASIBLE,
        candidate_values=candidate.values,
        multistate=multistate,
        constraints=tuple(constraints),
        objectives=(),
        failure_code=failure_code,
        failure_message=failure_message,
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("target_set_id", target_set.target_set_id),
            ("pose_set_id", pose_set.pose_set_id),
        ),
    )


def evaluate_operating_state_candidate(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    target_set: OperatingStateTargetSet,
    pose_set: SuspensionPoseSet,
) -> OperatingStateCandidateEvaluation:
    """Evaluate and score one candidate over explicitly targeted suspension states."""

    if target_set.pose_set_id != pose_set.pose_set_id:
        raise ValueError("Operating target set and suspension pose set do not match")

    constraints: list[ConstraintResult] = []
    try:
        multistate = evaluate_candidate_over_pose_set(
            baseline,
            requirement_set,
            candidate,
            target_set.sampling_target,
            pose_set,
        )
    except (CandidateGeometryError, RoleResolutionError, PoseDefinitionError, GeometryError, ValueError) as exc:
        constraints.append(
            _constraint(
                "operating_state_preflight",
                False,
                authority="AUTH-STEER-0002 analyzer-composed multi-state preflight",
                message=str(exc),
            )
        )
        return _infeasible(
            candidate,
            requirement_set,
            target_set,
            pose_set,
            multistate=None,
            constraints=constraints,
            failure_code="operating_state_preflight",
            failure_message=str(exc),
        )

    for state in multistate.states:
        constraints.append(
            _constraint(
                f"pose_state_complete_analyzer_sweep:{state.state_id}",
                state.feasible,
                value=(float(len(target_set.sampling_target.rack_displacements) * 2) if state.feasible else None),
                lower=float(len(target_set.sampling_target.rack_displacements) * 2),
                margin=(0.0 if state.feasible else None),
                unit="states",
                state=state.state_id,
                authority="MOD-STEER-0001 through the reviewed suspension-pose provider contract",
                message=(
                    "Both steering corners solved across the complete rack domain"
                    if state.feasible
                    else f"{state.failure_code}: {state.failure_message}"
                ),
            )
        )
    failed = [state for state in multistate.states if not state.feasible]
    if failed:
        first = failed[0]
        return _infeasible(
            candidate,
            requirement_set,
            target_set,
            pose_set,
            multistate=multistate,
            constraints=constraints,
            failure_code=first.failure_code or "operating_state_infeasible",
            failure_message=f"Pose {first.state_id}: {first.failure_message}",
        )

    objectives: list[ObjectiveContribution] = []
    state_map = multistate.state_map
    for target in target_set.state_targets:
        if target.role is OperatingTargetRole.REPORT_ONLY:
            continue
        actual_state = state_map[target.state_id]
        left_actual = tuple(
            target.canonical_to_target_output_sign * value
            for value in actual_state.left_incremental_from_pose_deg
        )
        right_actual = tuple(
            target.canonical_to_target_output_sign * value
            for value in actual_state.right_incremental_from_pose_deg
        )

        if target.require_monotonic_response:
            for side, values, expected_sign in (
                ("left", left_actual, target.left_monotonic_sign),
                ("right", right_actual, target.right_monotonic_sign),
            ):
                signed_steps = tuple(
                    expected_sign * (upper - lower)
                    for lower, upper in zip(values, values[1:])
                )
                minimum_step = min(signed_steps)
                passed = minimum_step >= -target.monotonic_tolerance_deg
                constraints.append(
                    _constraint(
                        f"pose_state_monotonic_response:{target.state_id}:{side}",
                        passed,
                        value=minimum_step,
                        lower=-target.monotonic_tolerance_deg,
                        margin=minimum_step + target.monotonic_tolerance_deg,
                        unit="deg_per_sample",
                        state=target.state_id,
                        authority="Explicit operating-state target constraint",
                        message=(
                            "Response follows the target direction across the state sweep"
                            if passed
                            else "Response reverses direction inside the state target sweep"
                        ),
                    )
                )
                if not passed:
                    return _infeasible(
                        candidate,
                        requirement_set,
                        target_set,
                        pose_set,
                        multistate=multistate,
                        constraints=constraints,
                        failure_code=f"{target.state_id}_{side}_nonmonotonic_response",
                        failure_message=f"Wheel response reverses direction at pose {target.state_id}",
                    )

        left_residuals = tuple(
            actual - requested for actual, requested in zip(left_actual, target.left_outputs)
        )
        right_residuals = tuple(
            actual - requested for actual, requested in zip(right_actual, target.right_outputs)
        )
        combined_squared = tuple(
            0.5 * (left * left + right * right)
            for left, right in zip(left_residuals, right_residuals)
        )
        total_weight = sum(target.sample_weights)
        raw_rms = math.sqrt(
            sum(weight * value for weight, value in zip(target.sample_weights, combined_squared))
            / total_weight
        )
        normalized = raw_rms / target.normalization_scale_deg
        objectives.append(
            ObjectiveContribution(
                objective_id=target.objective_id,
                raw_value=raw_rms,
                raw_unit="deg_rms",
                normalization_scale=target.normalization_scale_deg,
                normalized_value=normalized,
                weight=target.objective_weight,
                weighted_contribution=normalized * target.objective_weight,
                domain=(
                    f"pose={target.state_id}; {len(target.sample_weights)} rack samples; "
                    "left/right incremental projected heading from the supplied zero-steer pose"
                ),
                message=(
                    f"left RMS={_weighted_rms(left_residuals, target.sample_weights):.9g} deg, "
                    f"right RMS={_weighted_rms(right_residuals, target.sample_weights):.9g} deg, "
                    f"max abs={max(abs(value) for value in left_residuals + right_residuals):.9g} deg; "
                    f"state authority={target.authority}"
                ),
            )
        )

    if not objectives:
        return _infeasible(
            candidate,
            requirement_set,
            target_set,
            pose_set,
            multistate=multistate,
            constraints=constraints,
            failure_code="no_operating_state_objectives",
            failure_message="Operating target set produced no active objective terms",
        )

    return OperatingStateCandidateEvaluation(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        target_set_id=target_set.target_set_id,
        pose_set_id=pose_set.pose_set_id,
        status=CandidateEvaluationStatus.FEASIBLE,
        candidate_values=candidate.values,
        multistate=multistate,
        constraints=tuple(constraints),
        objectives=tuple(objectives),
        failure_code=None,
        failure_message="",
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("target_set_id", target_set.target_set_id),
            ("target_set_source_path", target_set.source_path),
            ("target_set_authority", target_set.authority),
            ("aggregation_method", target_set.aggregation_method),
            ("pose_set_id", pose_set.pose_set_id),
        ),
    )
