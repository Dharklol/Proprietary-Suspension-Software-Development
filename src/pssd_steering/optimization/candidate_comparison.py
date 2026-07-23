"""Constraint-screened and diversity-aware steering candidate comparison.

The comparison layer preserves the optimizer's objective ordering while making design
separation, geometry deltas, constraint margins, unavailable evidence, and ranking
reasons explicit. It does not claim Pareto completeness or global optimality.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .constraints import (
    ConstraintDisposition,
    ScreenedCandidateEvaluation,
    SteeringConstraintSet,
    screen_candidate_evaluation,
)
from .roles import RequirementSet
from .search import SteeringSearchResult


class CandidateComparisonError(ValueError):
    """Raised when a candidate comparison request is invalid."""


@dataclass(frozen=True)
class CandidateComparisonSettings:
    maximum_candidates: int = 8
    minimum_normalized_design_distance: float = 0.01

    def __post_init__(self) -> None:
        if self.maximum_candidates < 1:
            raise CandidateComparisonError("maximum_candidates must be positive")
        if (
            not math.isfinite(self.minimum_normalized_design_distance)
            or self.minimum_normalized_design_distance < 0.0
        ):
            raise CandidateComparisonError(
                "minimum_normalized_design_distance must be finite and nonnegative"
            )


@dataclass(frozen=True)
class ConstraintMarginSummary:
    constraint_id: str
    disposition: str
    margin: float | None
    unit: str
    authority: str


@dataclass(frozen=True)
class CandidateComparisonRow:
    comparison_rank: int
    source_rank: int
    candidate_id: str
    total_objective: float
    objective_delta_from_best: float
    normalized_design_distance_from_best: float
    minimum_distance_from_previously_selected: float
    candidate_values: tuple[tuple[str, float], ...]
    normalized_candidate_values: tuple[tuple[str, float], ...]
    tie_rod_length_m: float | None
    tie_rod_length_delta_from_best_m: float | None
    rack_axis_origin_m: tuple[float, float, float] | None
    outer_pickup_left_m: tuple[float, float, float] | None
    constraint_margins: tuple[ConstraintMarginSummary, ...]
    unavailable_constraint_ids: tuple[str, ...]
    ranking_explanation: str


@dataclass(frozen=True)
class CandidateComparisonResult:
    search_id: str
    requirement_set_id: str
    target_id: str
    constraint_set_id: str
    screened_candidate_count: int
    screened_feasible_count: int
    screened_infeasible_count: int
    selected_candidates: tuple[CandidateComparisonRow, ...]
    excluded_near_duplicate_count: int
    authority_boundary: str
    provenance: tuple[tuple[str, str], ...]


def _normalized_values(
    requirement_set: RequirementSet,
    values: tuple[tuple[str, float], ...],
) -> tuple[tuple[str, float], ...]:
    result: list[tuple[str, float]] = []
    value_map = dict(values)
    for definition in requirement_set.variables:
        if definition.minimum is None or definition.maximum is None:
            continue
        span = definition.maximum - definition.minimum
        result.append(
            (
                definition.id,
                (value_map[definition.id] - definition.minimum) / span,
            )
        )
    return tuple(result)


def _distance(
    left: tuple[tuple[str, float], ...],
    right: tuple[tuple[str, float], ...],
) -> float:
    left_map = dict(left)
    right_map = dict(right)
    ids = tuple(sorted(set(left_map) & set(right_map)))
    if not ids:
        return 0.0
    return math.sqrt(
        sum((left_map[item] - right_map[item]) ** 2 for item in ids) / len(ids)
    )


def _constraint_summaries(
    screened: ScreenedCandidateEvaluation,
) -> tuple[ConstraintMarginSummary, ...]:
    summaries: list[ConstraintMarginSummary] = []
    for item in screened.base_evaluation.constraints:
        summaries.append(
            ConstraintMarginSummary(
                constraint_id=item.constraint_id,
                disposition="passed" if item.passed else "failed",
                margin=item.margin,
                unit=item.unit,
                authority=item.authority,
            )
        )
    for item in screened.supplemental_constraints:
        summaries.append(
            ConstraintMarginSummary(
                constraint_id=item.constraint_id,
                disposition=item.disposition.value,
                margin=item.margin,
                unit=item.unit,
                authority=item.authority,
            )
        )
    return tuple(summaries)


def build_candidate_comparison(
    search_result: SteeringSearchResult,
    requirement_set: RequirementSet,
    constraint_set: SteeringConstraintSet,
    *,
    settings: CandidateComparisonSettings | None = None,
) -> CandidateComparisonResult:
    """Screen retained search candidates and select visibly distinct alternatives."""

    settings = settings or CandidateComparisonSettings()
    screened: list[tuple[int, ScreenedCandidateEvaluation]] = [
        (
            item.rank,
            screen_candidate_evaluation(item.evaluation, constraint_set),
        )
        for item in search_result.ranked_candidates
    ]
    feasible = [item for item in screened if item[1].feasible]
    feasible.sort(
        key=lambda item: (
            item[1].total_objective
            if item[1].total_objective is not None
            else math.inf,
            item[1].candidate_id,
        )
    )
    selected: list[tuple[int, ScreenedCandidateEvaluation, tuple[tuple[str, float], ...], float]] = []
    excluded_near_duplicates = 0

    for source_rank, candidate in feasible:
        normalized = _normalized_values(
            requirement_set, candidate.base_evaluation.candidate_values
        )
        if not selected:
            minimum_distance = math.inf
        else:
            minimum_distance = min(
                _distance(normalized, prior_normalized)
                for _, _, prior_normalized, _ in selected
            )
        if selected and minimum_distance < settings.minimum_normalized_design_distance:
            excluded_near_duplicates += 1
            continue
        selected.append((source_rank, candidate, normalized, minimum_distance))
        if len(selected) >= settings.maximum_candidates:
            break

    rows: list[CandidateComparisonRow] = []
    if selected:
        best_objective = selected[0][1].total_objective
        assert best_objective is not None
        best_normalized = selected[0][2]
        best_generated = selected[0][1].base_evaluation.generated
        best_tie_rod = (
            best_generated.left_tie_rod_length
            if best_generated is not None
            else None
        )
        for index, (source_rank, screened_candidate, normalized, minimum_distance) in enumerate(
            selected, start=1
        ):
            evaluation = screened_candidate.base_evaluation
            objective = screened_candidate.total_objective
            assert objective is not None
            generated = evaluation.generated
            tie_rod = generated.left_tie_rod_length if generated is not None else None
            geometry = generated.geometry if generated is not None else None
            unavailable = tuple(
                item.constraint_id
                for item in screened_candidate.supplemental_constraints
                if item.disposition is ConstraintDisposition.UNAVAILABLE
            )
            rows.append(
                CandidateComparisonRow(
                    comparison_rank=index,
                    source_rank=source_rank,
                    candidate_id=evaluation.candidate_id,
                    total_objective=objective,
                    objective_delta_from_best=objective - best_objective,
                    normalized_design_distance_from_best=_distance(
                        normalized, best_normalized
                    ),
                    minimum_distance_from_previously_selected=(
                        0.0 if index == 1 else minimum_distance
                    ),
                    candidate_values=evaluation.candidate_values,
                    normalized_candidate_values=normalized,
                    tie_rod_length_m=tie_rod,
                    tie_rod_length_delta_from_best_m=(
                        tie_rod - best_tie_rod
                        if tie_rod is not None and best_tie_rod is not None
                        else None
                    ),
                    rack_axis_origin_m=(
                        geometry.rack.axis.point if geometry is not None else None
                    ),
                    outer_pickup_left_m=(
                        geometry.left.outer_tie_rod_joint_at_center
                        if geometry is not None
                        else None
                    ),
                    constraint_margins=_constraint_summaries(screened_candidate),
                    unavailable_constraint_ids=unavailable,
                    ranking_explanation=(
                        "Lowest objective among constraint-screened retained candidates"
                        if index == 1
                        else "Next objective-ranked candidate exceeding the declared normalized design-distance threshold"
                    ),
                )
            )

    return CandidateComparisonResult(
        search_id=search_result.search_id,
        requirement_set_id=requirement_set.id,
        target_id=search_result.target_id,
        constraint_set_id=constraint_set.constraint_set_id,
        screened_candidate_count=len(screened),
        screened_feasible_count=len(feasible),
        screened_infeasible_count=len(screened) - len(feasible),
        selected_candidates=tuple(rows),
        excluded_near_duplicate_count=excluded_near_duplicates,
        authority_boundary=(
            "Constraint-screened development comparison only. The source search was not "
            "driven by unavailable hardware constraints, and this result is not Pareto, "
            "global-optimality, packaging, manufacturing, or production authority."
        ),
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("search_id", search_result.search_id),
            ("constraint_set_path", constraint_set.source_path),
            (
                "selection_method",
                "objective_order_with_normalized_design_distance_filter_v0.1.0",
            ),
        ),
    )
