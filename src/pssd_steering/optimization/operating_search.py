"""Deterministic inverse design over explicit operating-state steering targets.

This module reuses the nominal optimizer's bounded coordinate-pattern search
implementation.  Only the candidate-evaluation adapter changes: each candidate is
scored by the operating-state target aggregator instead of one nominal target.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core import SteeringGeometry
from .operating_evaluation import (
    OperatingStateCandidateEvaluation,
    evaluate_operating_state_candidate,
)
from .operating_targets import OperatingStateTargetSet
from .poses import SuspensionPoseSet
from .roles import RequirementSet, VariableDefinition, resolve_candidate
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


@dataclass(frozen=True)
class OperatingStateRankedCandidate:
    rank: int
    evaluation: OperatingStateCandidateEvaluation
    ranking_basis: str


@dataclass(frozen=True)
class OperatingStateSearchResult:
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
    ranked_candidates: tuple[OperatingStateRankedCandidate, ...]
    failure_message: str
    provenance: tuple[tuple[str, str], ...]

    @property
    def best(self) -> OperatingStateCandidateEvaluation | None:
        if not self.ranked_candidates:
            return None
        return self.ranked_candidates[0].evaluation


class _OperatingEvaluationCache:
    """Normalized-design cache compatible with the shared nominal search loop."""

    def __init__(
        self,
        baseline: SteeringGeometry,
        requirement_set: RequirementSet,
        target_set: OperatingStateTargetSet,
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
        self.cache: dict[tuple[float, ...], OperatingStateCandidateEvaluation] = {}
        self.order: list[OperatingStateCandidateEvaluation] = []

    @staticmethod
    def _key(normalized: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(round(value, 14) for value in normalized)

    def _denormalize(self, normalized: tuple[float, ...]) -> dict[str, float]:
        values = dict(self.fixed_overrides)
        for coordinate, variable in zip(normalized, self.active_variables):
            if variable.minimum is None or variable.maximum is None:
                raise SearchConfigurationError(
                    f"Active variable {variable.id!r} is missing bounds"
                )
            clipped = min(1.0, max(0.0, float(coordinate)))
            values[variable.id] = variable.minimum + clipped * (
                variable.maximum - variable.minimum
            )
        return values

    def evaluate(self, normalized: tuple[float, ...]) -> OperatingStateCandidateEvaluation:
        key = self._key(normalized)
        if key in self.cache:
            return self.cache[key]
        candidate_id = f"OPERATING-SEARCH-EVAL-{len(self.order) + 1:05d}"
        candidate = resolve_candidate(
            self.requirement_set,
            self._denormalize(normalized),
            candidate_id=candidate_id,
        )
        evaluation = evaluate_operating_state_candidate(
            self.baseline,
            self.requirement_set,
            candidate,
            self.target_set,
            self.pose_set,
        )
        self.cache[key] = evaluation
        self.order.append(evaluation)
        return evaluation


def run_operating_state_inverse_design(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    target_set: OperatingStateTargetSet,
    pose_set: SuspensionPoseSet,
    *,
    settings: SearchSettings | None = None,
    search_id: str = "STEERING-OPERATING-STATE-SEARCH",
) -> OperatingStateSearchResult:
    """Run the existing deterministic pattern-search method on multi-state objectives."""

    if target_set.pose_set_id != pose_set.pose_set_id:
        raise SearchConfigurationError("Operating target set and pose set identities do not match")

    settings = settings or SearchSettings()
    active_variables = _active_variables(requirement_set, settings.active_variable_ids)
    active_ids = tuple(variable.id for variable in active_variables)
    reference = _reference_normalized(active_variables)
    cache = _OperatingEvaluationCache(
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

    feasible = [evaluation for evaluation in cache.order if evaluation.feasible]
    feasible.sort(key=lambda item: (_objective(item), item.candidate_id))
    retained = feasible[: settings.retained_candidate_count]
    ranked = tuple(
        OperatingStateRankedCandidate(
            rank=index,
            evaluation=evaluation,
            ranking_basis=(
                "Ascending sum of explicit per-state normalized wheel-heading objective "
                "contributions among candidates that passed every supplied suspension-state "
                "analyzer sweep and active state constraint"
            ),
        )
        for index, evaluation in enumerate(retained, start=1)
    )
    failure_message = "" if ranked else "No feasible operating-state candidate was found"
    return OperatingStateSearchResult(
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
        active_variable_ids=active_ids,
        evaluated_candidate_count=len(cache.order),
        feasible_candidate_count=len(feasible),
        infeasible_candidate_count=len(cache.order) - len(feasible),
        starts=start_results,
        ranked_candidates=ranked,
        failure_message=failure_message,
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("baseline_geometry_id", baseline.geometry_id),
            ("requirement_set_id", requirement_set.id),
            ("target_set_id", target_set.target_set_id),
            ("pose_set_id", pose_set.pose_set_id),
            ("aggregation_method", target_set.aggregation_method),
            ("seed", str(settings.seed)),
            ("search_core", "shared_with_nominal_search_v0.1.0"),
        ),
    )
