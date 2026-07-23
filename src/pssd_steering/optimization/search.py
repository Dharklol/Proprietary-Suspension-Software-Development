"""Deterministic constrained search for the nominal steering inverse-design prototype.

The first numerical baseline is a bounded coordinate-pattern search with seeded
multistart. It operates on normalized role-selected variables and delegates every
candidate evaluation to the geometry generator and ``MOD-STEER-0001`` analyzer.
Infeasible candidates never receive an objective score.

Method lineage:
- Hooke and Jeeves (1961), direct search solution of numerical problems;
- Lewis, Torczon, and Trosset (2000), direct-search methods and convergence context.

This implementation is a transparent engineering baseline, not a claim that the
method is globally optimal or suitable for future high-dimensional mixed design.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

from ..core import SteeringGeometry
from .evaluation import CandidateEvaluation, evaluate_candidate
from .roles import (
    ParameterRole,
    RequirementSet,
    VariableDefinition,
    resolve_candidate,
)
from .targets import SteeringTarget


class SearchConfigurationError(ValueError):
    """Raised when a search problem violates the authorized role contract."""


@dataclass(frozen=True)
class SearchSettings:
    """Frozen numerical controls for deterministic bounded pattern search."""

    active_variable_ids: tuple[str, ...] = ()
    start_count: int = 7
    seed: int = 2701
    maximum_iterations_per_start: int = 24
    initial_step_fraction: float = 0.25
    contraction_factor: float = 0.5
    minimum_step_fraction: float = 0.001
    start_radius_fraction: float = 0.35
    improvement_tolerance: float = 1.0e-12
    retained_candidate_count: int = 10

    def __post_init__(self) -> None:
        if self.start_count < 1:
            raise SearchConfigurationError("start_count must be at least one")
        if self.maximum_iterations_per_start < 1:
            raise SearchConfigurationError("maximum_iterations_per_start must be positive")
        for name, value in (
            ("initial_step_fraction", self.initial_step_fraction),
            ("contraction_factor", self.contraction_factor),
            ("minimum_step_fraction", self.minimum_step_fraction),
            ("start_radius_fraction", self.start_radius_fraction),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise SearchConfigurationError(f"{name} must be finite and positive")
        if self.initial_step_fraction > 1.0:
            raise SearchConfigurationError("initial_step_fraction cannot exceed one")
        if not 0.0 < self.contraction_factor < 1.0:
            raise SearchConfigurationError("contraction_factor must lie between zero and one")
        if self.minimum_step_fraction >= self.initial_step_fraction:
            raise SearchConfigurationError(
                "minimum_step_fraction must be smaller than initial_step_fraction"
            )
        if self.start_radius_fraction > 1.0:
            raise SearchConfigurationError("start_radius_fraction cannot exceed one")
        if not math.isfinite(self.improvement_tolerance) or self.improvement_tolerance < 0.0:
            raise SearchConfigurationError("improvement_tolerance must be nonnegative")
        if self.retained_candidate_count < 1:
            raise SearchConfigurationError("retained_candidate_count must be positive")


@dataclass(frozen=True)
class StartResult:
    """Terminal state for one deterministic local-search start."""

    start_index: int
    start_normalized: tuple[float, ...]
    terminal_candidate_id: str | None
    terminal_objective: float | None
    iterations: int
    termination_reason: str


@dataclass(frozen=True)
class RankedCandidate:
    """One retained feasible candidate with transparent rank explanation."""

    rank: int
    evaluation: CandidateEvaluation
    ranking_basis: str


@dataclass(frozen=True)
class SteeringSearchResult:
    """Deterministic search result with multiple retained feasible candidates."""

    search_id: str
    requirement_set_id: str
    target_id: str
    method_id: str
    method_references: tuple[str, ...]
    settings: SearchSettings
    active_variable_ids: tuple[str, ...]
    evaluated_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    starts: tuple[StartResult, ...]
    ranked_candidates: tuple[RankedCandidate, ...]
    failure_message: str
    provenance: tuple[tuple[str, str], ...]

    @property
    def best(self) -> CandidateEvaluation | None:
        if not self.ranked_candidates:
            return None
        return self.ranked_candidates[0].evaluation


class _EvaluationCache:
    def __init__(
        self,
        baseline: SteeringGeometry,
        requirement_set: RequirementSet,
        target: SteeringTarget,
        active_variables: tuple[VariableDefinition, ...],
        fixed_overrides: dict[str, float],
    ) -> None:
        self.baseline = baseline
        self.requirement_set = requirement_set
        self.target = target
        self.active_variables = active_variables
        self.fixed_overrides = fixed_overrides
        self.cache: dict[tuple[float, ...], CandidateEvaluation] = {}
        self.order: list[CandidateEvaluation] = []

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

    def evaluate(self, normalized: tuple[float, ...]) -> CandidateEvaluation:
        key = self._key(normalized)
        if key in self.cache:
            return self.cache[key]
        candidate_id = f"SEARCH-EVAL-{len(self.order) + 1:05d}"
        overrides = self._denormalize(normalized)
        candidate = resolve_candidate(
            self.requirement_set,
            overrides,
            candidate_id=candidate_id,
        )
        evaluation = evaluate_candidate(
            self.baseline,
            self.requirement_set,
            candidate,
            self.target,
        )
        self.cache[key] = evaluation
        self.order.append(evaluation)
        return evaluation


def _active_variables(
    requirement_set: RequirementSet,
    requested_ids: tuple[str, ...],
) -> tuple[VariableDefinition, ...]:
    if requested_ids:
        if len(set(requested_ids)) != len(requested_ids):
            raise SearchConfigurationError("active_variable_ids contains duplicates")
        variables = tuple(requirement_set.variable(item) for item in requested_ids)
    else:
        variables = tuple(
            variable
            for variable in requirement_set.variables
            if variable.role is ParameterRole.BOUNDED_DESIGN_VARIABLE
        )
    if not variables:
        raise SearchConfigurationError("At least one bounded design variable must be active")
    for variable in variables:
        if variable.role is not ParameterRole.BOUNDED_DESIGN_VARIABLE:
            raise SearchConfigurationError(
                f"Active variable {variable.id!r} does not have bounded_design_variable role"
            )
        if variable.minimum is None or variable.maximum is None:
            raise SearchConfigurationError(f"Active variable {variable.id!r} has no bounds")
    return variables


def _reference_normalized(variables: tuple[VariableDefinition, ...]) -> tuple[float, ...]:
    result: list[float] = []
    for variable in variables:
        if variable.minimum is None or variable.maximum is None:
            raise SearchConfigurationError(f"Variable {variable.id!r} has no bounds")
        result.append(
            (variable.reference - variable.minimum) / (variable.maximum - variable.minimum)
        )
    return tuple(result)


def _fixed_overrides(
    requirement_set: RequirementSet,
    active_variables: tuple[VariableDefinition, ...],
) -> dict[str, float]:
    active_ids = {variable.id for variable in active_variables}
    return {
        variable.id: variable.reference
        for variable in requirement_set.variables
        if variable.id not in active_ids
    }


def _initial_starts(
    reference: tuple[float, ...], settings: SearchSettings
) -> tuple[tuple[float, ...], ...]:
    starts: list[tuple[float, ...]] = [reference]
    generator = random.Random(settings.seed)
    for _ in range(1, settings.start_count):
        values = []
        for coordinate in reference:
            perturbation = (
                2.0 * generator.random() - 1.0
            ) * settings.start_radius_fraction
            values.append(min(1.0, max(0.0, coordinate + perturbation)))
        starts.append(tuple(values))
    return tuple(starts)


def _objective(evaluation: CandidateEvaluation) -> float:
    value = evaluation.total_objective
    return value if value is not None else math.inf


def _recover_feasible_start(
    start: tuple[float, ...],
    reference: tuple[float, ...],
    cache: _EvaluationCache,
) -> tuple[tuple[float, ...], CandidateEvaluation]:
    evaluation = cache.evaluate(start)
    if evaluation.feasible:
        return start, evaluation
    fraction = 0.5
    for _ in range(10):
        candidate = tuple(
            ref + fraction * (value - ref) for value, ref in zip(start, reference)
        )
        evaluation = cache.evaluate(candidate)
        if evaluation.feasible:
            return candidate, evaluation
        fraction *= 0.5
    return reference, cache.evaluate(reference)


def _run_local_search(
    start_index: int,
    start: tuple[float, ...],
    reference: tuple[float, ...],
    cache: _EvaluationCache,
    settings: SearchSettings,
) -> StartResult:
    current_point, current = _recover_feasible_start(start, reference, cache)
    if not current.feasible:
        return StartResult(
            start_index=start_index,
            start_normalized=start,
            terminal_candidate_id=None,
            terminal_objective=None,
            iterations=0,
            termination_reason="No feasible point found between the start and reference",
        )

    step = settings.initial_step_fraction
    iterations = 0
    termination = "maximum_iterations_reached"
    while iterations < settings.maximum_iterations_per_start:
        iterations += 1
        best_point = current_point
        best_evaluation = current
        for index in range(len(current_point)):
            for direction in (-1.0, 1.0):
                trial = list(current_point)
                trial[index] = min(1.0, max(0.0, trial[index] + direction * step))
                trial_point = tuple(trial)
                if trial_point == current_point:
                    continue
                evaluation = cache.evaluate(trial_point)
                if not evaluation.feasible:
                    continue
                if _objective(evaluation) + settings.improvement_tolerance < _objective(
                    best_evaluation
                ):
                    best_point = trial_point
                    best_evaluation = evaluation
        if best_point != current_point:
            current_point = best_point
            current = best_evaluation
            continue
        step *= settings.contraction_factor
        if step < settings.minimum_step_fraction:
            termination = "step_fraction_below_minimum"
            break

    return StartResult(
        start_index=start_index,
        start_normalized=start,
        terminal_candidate_id=current.candidate_id,
        terminal_objective=current.total_objective,
        iterations=iterations,
        termination_reason=termination,
    )


def run_nominal_inverse_design(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    target: SteeringTarget,
    *,
    settings: SearchSettings | None = None,
    search_id: str = "STEERING-NOMINAL-SEARCH",
) -> SteeringSearchResult:
    """Run the deterministic nominal-height constrained-search baseline."""

    settings = settings or SearchSettings()
    active_variables = _active_variables(requirement_set, settings.active_variable_ids)
    active_ids = tuple(variable.id for variable in active_variables)
    reference = _reference_normalized(active_variables)
    cache = _EvaluationCache(
        baseline,
        requirement_set,
        target,
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
        RankedCandidate(
            rank=index,
            evaluation=evaluation,
            ranking_basis=(
                "Ascending normalized wheel-heading target error among candidates that "
                "passed geometry preflight, complete analyzer sweep, projection, and "
                "monotonic-response constraints"
            ),
        )
        for index, evaluation in enumerate(retained, start=1)
    )
    infeasible_count = len(cache.order) - len(feasible)
    failure_message = "" if ranked else "No feasible candidate was found in the evaluated set"
    return SteeringSearchResult(
        search_id=search_id,
        requirement_set_id=requirement_set.id,
        target_id=target.target_id,
        method_id="bounded_coordinate_pattern_search_v0.1.0",
        method_references=(
            "Hooke and Jeeves (1961), Direct Search Solution of Numerical and Statistical Problems",
            "Lewis, Torczon, and Trosset (2000), Direct Search Methods: Then and Now",
        ),
        settings=settings,
        active_variable_ids=active_ids,
        evaluated_candidate_count=len(cache.order),
        feasible_candidate_count=len(feasible),
        infeasible_candidate_count=infeasible_count,
        starts=start_results,
        ranked_candidates=ranked,
        failure_message=failure_message,
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("baseline_geometry_id", baseline.geometry_id),
            ("requirement_set_id", requirement_set.id),
            ("target_id", target.target_id),
            ("seed", str(settings.seed)),
        ),
    )
