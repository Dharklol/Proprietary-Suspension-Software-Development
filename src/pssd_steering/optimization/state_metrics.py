"""Explicit scalar operating-state objectives for dynamic toe and steering gain.

The objective layer consumes already-computed ``MOD-STEER-0001`` multi-state
results.  It does not add suspension kinematics or a second steering model.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Mapping

from ..core import GeometryError, SteeringGeometry
from .evaluation import CandidateEvaluationStatus, ConstraintResult, ObjectiveContribution
from .geometry import CandidateGeometryError
from .multistate import MultiStateSteeringEvaluation, PoseStateEvaluation, evaluate_candidate_over_pose_set
from .poses import PoseDefinitionError, SuspensionPoseSet
from .roles import RequirementSet, ResolvedCandidate, RoleResolutionError, VariableDefinition, resolve_candidate
from .search import (
    SearchConfigurationError,
    SearchSettings,
    StartResult,
    _active_variables,
    _fixed_overrides,
    _initial_starts,
    _objective,
    _reference_normalized,
    _run_local_search,
)
from .targets import SteeringTarget, TargetDefinitionError


class StateMetricId(str, Enum):
    CENTER_DYNAMIC_TOE_OUT_CHANGE = "center_dynamic_toe_out_change"
    CENTER_RACK_TO_WHEEL_GAIN = "center_rack_to_wheel_gain"


@dataclass(frozen=True)
class StateMetricTarget:
    state_id: str
    metric_id: StateMetricId
    objective_id: str
    left_target: float
    right_target: float
    output_unit: str
    normalization_scale: float
    objective_weight: float
    canonical_to_target_left_sign: float = 1.0
    canonical_to_target_right_sign: float = 1.0
    authority: str = ""
    source_path: str = ""
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id or not self.objective_id:
            raise TargetDefinitionError("State metric target requires state_id and objective_id")
        expected = (
            "deg"
            if self.metric_id is StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE
            else "deg_per_mm"
        )
        if self.output_unit != expected:
            raise TargetDefinitionError(
                f"{self.metric_id.value} requires output_unit={expected!r}"
            )
        values = (
            self.left_target,
            self.right_target,
            self.normalization_scale,
            self.objective_weight,
        )
        if not all(math.isfinite(value) for value in values):
            raise TargetDefinitionError("State metric target contains nonfinite values")
        if self.normalization_scale <= 0.0 or self.objective_weight <= 0.0:
            raise TargetDefinitionError("State metric normalization and weight must be positive")
        if self.canonical_to_target_left_sign not in {-1.0, 1.0}:
            raise TargetDefinitionError("left sign adapter must be +1 or -1")
        if self.canonical_to_target_right_sign not in {-1.0, 1.0}:
            raise TargetDefinitionError("right sign adapter must be +1 or -1")


@dataclass(frozen=True)
class StateMetricTargetSet:
    target_set_id: str
    version: str
    pose_set_id: str
    sampling_target: SteeringTarget
    targets: tuple[StateMetricTarget, ...]
    aggregation_method: str
    authority: str
    source_path: str
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.target_set_id or not self.pose_set_id:
            raise TargetDefinitionError("State metric target set requires IDs")
        if self.aggregation_method != "sum_weighted_normalized_state_pair_rms":
            raise TargetDefinitionError("Unsupported state metric aggregation method")
        if not self.targets:
            raise TargetDefinitionError("State metric target set requires at least one target")
        keys = [(item.state_id, item.metric_id.value) for item in self.targets]
        if len(keys) != len(set(keys)):
            raise TargetDefinitionError("Duplicate state/metric target")


@dataclass(frozen=True)
class StateMetricCandidateEvaluation:
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


@dataclass(frozen=True)
class StateMetricRankedCandidate:
    rank: int
    evaluation: StateMetricCandidateEvaluation
    ranking_basis: str


@dataclass(frozen=True)
class StateMetricSearchResult:
    search_id: str
    requirement_set_id: str
    target_set_id: str
    pose_set_id: str
    method_id: str
    method_references: tuple[str, ...]
    settings: SearchSettings
    active_variable_ids: tuple[str, ...]
    evaluated_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    starts: tuple[StartResult, ...]
    ranked_candidates: tuple[StateMetricRankedCandidate, ...]
    failure_message: str
    provenance: tuple[tuple[str, str], ...]

    @property
    def best(self) -> StateMetricCandidateEvaluation | None:
        return self.ranked_candidates[0].evaluation if self.ranked_candidates else None


def _constraint(state_id: str, passed: bool, message: str) -> ConstraintResult:
    return ConstraintResult(
        constraint_id=f"pose_state_complete_analyzer_sweep:{state_id}",
        passed=passed,
        value=None,
        lower_limit=None,
        upper_limit=None,
        margin=0.0 if passed else None,
        unit="",
        state=state_id,
        authority="MOD-STEER-0001 through reviewed suspension-pose provider contract",
        message=message,
    )


def _center_gain_deg_per_mm(
    state: PoseStateEvaluation, rack_displacements_m: tuple[float, ...], side: str
) -> float:
    try:
        center = rack_displacements_m.index(0.0)
    except ValueError as exc:
        raise TargetDefinitionError("Steering-gain objective requires an exact rack-center sample") from exc
    if center <= 0 or center >= len(rack_displacements_m) - 1:
        raise TargetDefinitionError("Steering-gain objective requires rack samples on both sides of zero")
    x0 = rack_displacements_m[center - 1]
    x1 = rack_displacements_m[center + 1]
    if x1 <= x0:
        raise TargetDefinitionError("Rack sampling must increase through the center sample")
    values = (
        state.left_incremental_from_pose_deg
        if side == "left"
        else state.right_incremental_from_pose_deg
    )
    return (values[center + 1] - values[center - 1]) / ((x1 - x0) * 1000.0)


def state_metric_pair(
    state: PoseStateEvaluation,
    rack_displacements_m: tuple[float, ...],
    metric_id: StateMetricId,
) -> tuple[float, float]:
    if not state.feasible:
        raise TargetDefinitionError(f"Pose {state.state_id!r} is not feasible")
    if metric_id is StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE:
        left = state.center_left_side_local_toe_out_change_deg
        right = state.center_right_side_local_toe_out_change_deg
        if left is None or right is None:
            raise TargetDefinitionError(f"Pose {state.state_id!r} is missing dynamic-toe outputs")
        return left, right
    return (
        _center_gain_deg_per_mm(state, rack_displacements_m, "left"),
        _center_gain_deg_per_mm(state, rack_displacements_m, "right"),
    )


def evaluate_state_metric_candidate(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    target_set: StateMetricTargetSet,
    pose_set: SuspensionPoseSet,
) -> StateMetricCandidateEvaluation:
    if target_set.pose_set_id != pose_set.pose_set_id:
        raise ValueError("State metric target set and suspension pose set do not match")
    constraints: list[ConstraintResult] = []
    try:
        multistate = evaluate_candidate_over_pose_set(
            baseline, requirement_set, candidate, target_set.sampling_target, pose_set
        )
    except (CandidateGeometryError, RoleResolutionError, PoseDefinitionError, GeometryError, ValueError) as exc:
        return StateMetricCandidateEvaluation(
            candidate.candidate_id, requirement_set.id, target_set.target_set_id, pose_set.pose_set_id,
            CandidateEvaluationStatus.INFEASIBLE, candidate.values, None, (), (), "state_metric_preflight",
            str(exc), (("evaluator_model_id", "MOD-STEER-0001"), ("optimizer_model_id", "MOD-STEER-0002"))
        )
    for state in multistate.states:
        constraints.append(_constraint(state.state_id, state.feasible, state.failure_message))
    failed = [state for state in multistate.states if not state.feasible]
    if failed:
        first = failed[0]
        return StateMetricCandidateEvaluation(
            candidate.candidate_id, requirement_set.id, target_set.target_set_id, pose_set.pose_set_id,
            CandidateEvaluationStatus.INFEASIBLE, candidate.values, multistate, tuple(constraints), (),
            first.failure_code or "operating_state_infeasible",
            f"Pose {first.state_id}: {first.failure_message}",
            (("evaluator_model_id", "MOD-STEER-0001"), ("optimizer_model_id", "MOD-STEER-0002"))
        )
    objectives: list[ObjectiveContribution] = []
    for target in target_set.targets:
        state = multistate.state_map.get(target.state_id)
        if state is None:
            raise TargetDefinitionError(f"Metric target references unknown pose {target.state_id!r}")
        left, right = state_metric_pair(
            state, target_set.sampling_target.rack_displacements, target.metric_id
        )
        left *= target.canonical_to_target_left_sign
        right *= target.canonical_to_target_right_sign
        left_residual = left - target.left_target
        right_residual = right - target.right_target
        raw = math.sqrt(0.5 * (left_residual * left_residual + right_residual * right_residual))
        normalized = raw / target.normalization_scale
        objectives.append(
            ObjectiveContribution(
                objective_id=target.objective_id,
                raw_value=raw,
                raw_unit=f"{target.output_unit}_pair_rms",
                normalization_scale=target.normalization_scale,
                normalized_value=normalized,
                weight=target.objective_weight,
                weighted_contribution=normalized * target.objective_weight,
                domain=f"pose={target.state_id}; metric={target.metric_id.value}; rack-center",
                message=(
                    f"left actual={left:.9g}, target={target.left_target:.9g}; "
                    f"right actual={right:.9g}, target={target.right_target:.9g}; "
                    f"authority={target.authority}"
                ),
            )
        )
    return StateMetricCandidateEvaluation(
        candidate.candidate_id, requirement_set.id, target_set.target_set_id, pose_set.pose_set_id,
        CandidateEvaluationStatus.FEASIBLE, candidate.values, multistate, tuple(constraints),
        tuple(objectives), None, "",
        (
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("target_set_id", target_set.target_set_id),
            ("aggregation_method", target_set.aggregation_method),
        ),
    )


def build_analyzer_state_metric_target_set(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    source_candidate_values: Mapping[str, float],
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
    *,
    target_set_id: str,
    version: str,
    state_metric_weights: Mapping[tuple[str, StateMetricId], float],
    normalization_scales: Mapping[tuple[str, StateMetricId], float] | None = None,
    authority: str = "software_verification_only",
    source_path: str = "",
) -> StateMetricTargetSet:
    candidate = resolve_candidate(
        requirement_set,
        {key: float(value) for key, value in source_candidate_values.items()},
        candidate_id=f"{target_set_id}:SOURCE",
    )
    evaluated = evaluate_candidate_over_pose_set(
        baseline, requirement_set, candidate, sampling_target, pose_set
    )
    if not evaluated.feasible:
        raise TargetDefinitionError("Analyzer-generated state-metric source candidate is infeasible")
    scales = dict(normalization_scales or {})
    targets: list[StateMetricTarget] = []
    for (state_id, metric_id), weight in state_metric_weights.items():
        state = evaluated.state_map.get(state_id)
        if state is None:
            raise TargetDefinitionError(f"Unknown pose state {state_id!r}")
        left, right = state_metric_pair(state, sampling_target.rack_displacements, metric_id)
        default_scale = 0.1 if metric_id is StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE else 0.02
        targets.append(
            StateMetricTarget(
                state_id=state_id,
                metric_id=metric_id,
                objective_id=f"{metric_id.value}:{state_id}",
                left_target=left,
                right_target=right,
                output_unit="deg" if metric_id is StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE else "deg_per_mm",
                normalization_scale=float(scales.get((state_id, metric_id), default_scale)),
                objective_weight=float(weight),
                authority=authority,
                source_path=source_path,
                provenance=(("source_candidate_id", candidate.candidate_id),),
            )
        )
    return StateMetricTargetSet(
        target_set_id=target_set_id,
        version=version,
        pose_set_id=pose_set.pose_set_id,
        sampling_target=sampling_target,
        targets=tuple(targets),
        aggregation_method="sum_weighted_normalized_state_pair_rms",
        authority=authority,
        source_path=source_path,
        provenance=(
            ("source_candidate_id", candidate.candidate_id),
            ("pose_set_id", pose_set.pose_set_id),
            ("sampling_target_id", sampling_target.target_id),
        ),
    )


def load_explicit_state_metric_target_set(
    path: str | Path,
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
) -> StateMetricTargetSet:
    source = Path(path)
    with source.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type")) != "explicit_state_metric_targets":
        raise TargetDefinitionError("Invalid state metric target source_type")
    if str(document.get("pose_set_id")) != pose_set.pose_set_id:
        raise TargetDefinitionError("State metric target pose_set_id does not match")
    if str(document.get("sampling_target_id")) != sampling_target.target_id:
        raise TargetDefinitionError("State metric sampling_target_id does not match")
    available = set(pose_set.state_map)
    targets: list[StateMetricTarget] = []
    for table in document.get("targets", []):
        state_id = str(table.get("state_id", ""))
        if state_id not in available:
            raise TargetDefinitionError(f"Unknown pose state {state_id!r}")
        metric_id = StateMetricId(str(table.get("metric_id", "")))
        targets.append(
            StateMetricTarget(
                state_id=state_id,
                metric_id=metric_id,
                objective_id=str(table.get("objective_id", f"{metric_id.value}:{state_id}")),
                left_target=float(table["left_target"]),
                right_target=float(table["right_target"]),
                output_unit=str(table["output_unit"]),
                normalization_scale=float(table["normalization_scale"]),
                objective_weight=float(table["objective_weight"]),
                canonical_to_target_left_sign=float(table.get("canonical_to_target_left_sign", 1.0)),
                canonical_to_target_right_sign=float(table.get("canonical_to_target_right_sign", 1.0)),
                authority=str(table.get("authority", document.get("authority", ""))),
                source_path=str(source),
            )
        )
    return StateMetricTargetSet(
        target_set_id=str(document.get("target_set_id", "")),
        version=str(document.get("version", "0")),
        pose_set_id=pose_set.pose_set_id,
        sampling_target=sampling_target,
        targets=tuple(targets),
        aggregation_method=str(document.get("aggregation_method", "")),
        authority=str(document.get("authority", "")),
        source_path=str(source),
    )


class _StateMetricEvaluationCache:
    def __init__(
        self,
        baseline: SteeringGeometry,
        requirement_set: RequirementSet,
        target_set: StateMetricTargetSet,
        pose_set: SuspensionPoseSet,
        active_variables: tuple[VariableDefinition, ...],
        fixed_overrides: dict[str, float],
    ) -> None:
        self.baseline = baseline
        self.requirement_set = requirement_set
        self.target_set = target_set
        self.pose_set = pose_set
        self.active_variables = active_variables
        self.fixed_overrides = fixed_overrides
        self.cache: dict[tuple[float, ...], StateMetricCandidateEvaluation] = {}
        self.order: list[StateMetricCandidateEvaluation] = []

    @staticmethod
    def _key(normalized: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(round(value, 14) for value in normalized)

    def _denormalize(self, normalized: tuple[float, ...]) -> dict[str, float]:
        values = dict(self.fixed_overrides)
        for coordinate, variable in zip(normalized, self.active_variables):
            if variable.minimum is None or variable.maximum is None:
                raise SearchConfigurationError(f"Active variable {variable.id!r} is missing bounds")
            clipped = min(1.0, max(0.0, float(coordinate)))
            values[variable.id] = variable.minimum + clipped * (variable.maximum - variable.minimum)
        return values

    def evaluate(self, normalized: tuple[float, ...]) -> StateMetricCandidateEvaluation:
        key = self._key(normalized)
        if key in self.cache:
            return self.cache[key]
        candidate = resolve_candidate(
            self.requirement_set,
            self._denormalize(normalized),
            candidate_id=f"STATE-METRIC-SEARCH-EVAL-{len(self.order) + 1:05d}",
        )
        evaluation = evaluate_state_metric_candidate(
            self.baseline, self.requirement_set, candidate, self.target_set, self.pose_set
        )
        self.cache[key] = evaluation
        self.order.append(evaluation)
        return evaluation


def run_state_metric_inverse_design(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    target_set: StateMetricTargetSet,
    pose_set: SuspensionPoseSet,
    *,
    settings: SearchSettings | None = None,
    search_id: str = "STEERING-STATE-METRIC-SEARCH",
) -> StateMetricSearchResult:
    if target_set.pose_set_id != pose_set.pose_set_id:
        raise SearchConfigurationError("State metric target set and pose set identities do not match")
    settings = settings or SearchSettings()
    active_variables = _active_variables(requirement_set, settings.active_variable_ids)
    reference = _reference_normalized(active_variables)
    cache = _StateMetricEvaluationCache(
        baseline,
        requirement_set,
        target_set,
        pose_set,
        active_variables,
        _fixed_overrides(requirement_set, active_variables),
    )
    starts = _initial_starts(reference, settings)
    start_results = tuple(
        _run_local_search(index, start, reference, cache, settings)
        for index, start in enumerate(starts)
    )
    feasible = [item for item in cache.order if item.feasible]
    feasible.sort(key=lambda item: (_objective(item), item.candidate_id))
    retained = feasible[: settings.retained_candidate_count]
    ranked = tuple(
        StateMetricRankedCandidate(
            rank=index,
            evaluation=evaluation,
            ranking_basis=(
                "Ascending sum of explicit normalized dynamic-toe and/or centered "
                "rack-to-wheel-gain objective contributions after all supplied poses pass"
            ),
        )
        for index, evaluation in enumerate(retained, start=1)
    )
    return StateMetricSearchResult(
        search_id=search_id,
        requirement_set_id=requirement_set.id,
        target_set_id=target_set.target_set_id,
        pose_set_id=pose_set.pose_set_id,
        method_id="bounded_coordinate_pattern_search_v0.1.0",
        method_references=(
            "Hooke and Jeeves (1961), Direct Search Solution of Numerical and Statistical Problems",
            "Lewis, Torczon, and Trosset (2000), Direct Search Methods: Then and Now",
        ),
        settings=settings,
        active_variable_ids=tuple(item.id for item in active_variables),
        evaluated_candidate_count=len(cache.order),
        feasible_candidate_count=len(feasible),
        infeasible_candidate_count=len(cache.order) - len(feasible),
        starts=start_results,
        ranked_candidates=ranked,
        failure_message="" if ranked else "No feasible state-metric candidate was found",
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("target_set_id", target_set.target_set_id),
            ("pose_set_id", pose_set.pose_set_id),
            ("aggregation_method", target_set.aggregation_method),
            ("search_core", "shared_with_nominal_search_v0.1.0"),
        ),
    )
