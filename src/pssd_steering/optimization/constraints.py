"""Constraint-provider contracts for steering design studies.

This layer screens analyzer-composed candidate evaluations against named constraints.
It does not add steering kinematics. Missing hardware or packaging evidence remains
explicitly unavailable rather than being silently treated as a pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib

from .evaluation import CandidateEvaluation


class ConstraintDefinitionError(ValueError):
    """Raised when a constraint-provider definition is invalid."""


class ConstraintAvailability(str, Enum):
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"


class ConstraintDisposition(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ConstraintDefinition:
    constraint_id: str
    evaluator: str
    availability: ConstraintAvailability
    unit: str
    authority: str
    state: str
    blocking: bool
    lower_limit: float | None = None
    upper_limit: float | None = None
    variable_id: str | None = None
    unavailable_reason: str = ""

    def __post_init__(self) -> None:
        if not self.constraint_id:
            raise ConstraintDefinitionError("constraint_id is required")
        if not self.evaluator:
            raise ConstraintDefinitionError(
                f"Constraint {self.constraint_id!r} requires an evaluator"
            )
        if not self.unit:
            raise ConstraintDefinitionError(
                f"Constraint {self.constraint_id!r} requires an explicit unit"
            )
        for name, value in (
            ("lower_limit", self.lower_limit),
            ("upper_limit", self.upper_limit),
        ):
            if value is not None and not math.isfinite(value):
                raise ConstraintDefinitionError(
                    f"Constraint {self.constraint_id!r} {name} must be finite"
                )
        if (
            self.lower_limit is not None
            and self.upper_limit is not None
            and self.lower_limit > self.upper_limit
        ):
            raise ConstraintDefinitionError(
                f"Constraint {self.constraint_id!r} has inverted limits"
            )
        if self.availability is ConstraintAvailability.ACTIVE:
            if self.evaluator not in {
                "tie_rod_joint_center_length",
                "minimum_singularity_ratio",
                "candidate_scalar",
            }:
                raise ConstraintDefinitionError(
                    f"Constraint {self.constraint_id!r} uses unsupported active evaluator "
                    f"{self.evaluator!r}"
                )
            if self.lower_limit is None and self.upper_limit is None:
                raise ConstraintDefinitionError(
                    f"Active constraint {self.constraint_id!r} requires a limit"
                )
            if self.evaluator == "candidate_scalar" and not self.variable_id:
                raise ConstraintDefinitionError(
                    f"Constraint {self.constraint_id!r} requires variable_id"
                )
        else:
            if self.blocking:
                raise ConstraintDefinitionError(
                    f"Unavailable constraint {self.constraint_id!r} cannot be blocking"
                )
            if not self.unavailable_reason:
                raise ConstraintDefinitionError(
                    f"Unavailable constraint {self.constraint_id!r} requires a reason"
                )


@dataclass(frozen=True)
class SteeringConstraintSet:
    constraint_set_id: str
    version: str
    status: str
    authority: str
    constraints: tuple[ConstraintDefinition, ...]
    source_path: str

    @property
    def constraint_map(self) -> dict[str, ConstraintDefinition]:
        return {item.constraint_id: item for item in self.constraints}


@dataclass(frozen=True)
class SupplementalConstraintResult:
    constraint_id: str
    disposition: ConstraintDisposition
    value: float | None
    lower_limit: float | None
    upper_limit: float | None
    margin: float | None
    unit: str
    state: str
    authority: str
    blocking: bool
    message: str

    @property
    def passed(self) -> bool:
        return self.disposition is ConstraintDisposition.PASSED

    @property
    def available(self) -> bool:
        return self.disposition is not ConstraintDisposition.UNAVAILABLE


@dataclass(frozen=True)
class ScreenedCandidateEvaluation:
    base_evaluation: CandidateEvaluation
    constraint_set_id: str
    supplemental_constraints: tuple[SupplementalConstraintResult, ...]
    feasible: bool
    failure_code: str | None
    failure_message: str

    @property
    def candidate_id(self) -> str:
        return self.base_evaluation.candidate_id

    @property
    def total_objective(self) -> float | None:
        return self.base_evaluation.total_objective if self.feasible else None

    @property
    def unavailable_constraint_ids(self) -> tuple[str, ...]:
        return tuple(
            item.constraint_id
            for item in self.supplemental_constraints
            if item.disposition is ConstraintDisposition.UNAVAILABLE
        )


def load_constraint_set(path: str | Path) -> SteeringConstraintSet:
    """Load a named constraint set without promoting unavailable evidence."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)

    constraint_set_id = str(document.get("constraint_set_id", ""))
    if not constraint_set_id:
        raise ConstraintDefinitionError("constraint_set_id is required")

    definitions: list[ConstraintDefinition] = []
    seen: set[str] = set()
    for table in document.get("constraints", []):
        constraint_id = str(table.get("id", ""))
        if constraint_id in seen:
            raise ConstraintDefinitionError(
                f"Duplicate constraint id {constraint_id!r}"
            )
        seen.add(constraint_id)
        try:
            availability = ConstraintAvailability(str(table.get("availability")))
        except ValueError as exc:
            raise ConstraintDefinitionError(
                f"Constraint {constraint_id!r} has invalid availability"
            ) from exc
        definitions.append(
            ConstraintDefinition(
                constraint_id=constraint_id,
                evaluator=str(table.get("evaluator", "")),
                availability=availability,
                unit=str(table.get("unit", "")),
                authority=str(table.get("authority", "")),
                state=str(table.get("state", "all")),
                blocking=bool(table.get("blocking", False)),
                lower_limit=(
                    float(table["lower_limit"]) if "lower_limit" in table else None
                ),
                upper_limit=(
                    float(table["upper_limit"]) if "upper_limit" in table else None
                ),
                variable_id=(
                    str(table["variable_id"]) if "variable_id" in table else None
                ),
                unavailable_reason=str(table.get("unavailable_reason", "")),
            )
        )

    return SteeringConstraintSet(
        constraint_set_id=constraint_set_id,
        version=str(document.get("version", "0")),
        status=str(document.get("status", "")),
        authority=str(document.get("authority", "")),
        constraints=tuple(definitions),
        source_path=str(source_path),
    )


def _minimum_margin(
    value: float,
    lower: float | None,
    upper: float | None,
) -> float:
    margins: list[float] = []
    if lower is not None:
        margins.append(value - lower)
    if upper is not None:
        margins.append(upper - value)
    if not margins:
        raise ConstraintDefinitionError("At least one limit is required")
    return min(margins)


def _evaluate_value(
    definition: ConstraintDefinition,
    evaluation: CandidateEvaluation,
) -> float:
    generated = evaluation.generated
    if generated is None:
        raise ConstraintDefinitionError("Generated geometry is unavailable")
    if definition.evaluator == "tie_rod_joint_center_length":
        return min(generated.left_tie_rod_length, generated.right_tie_rod_length)
    if definition.evaluator == "minimum_singularity_ratio":
        values = [
            state.singularity_ratio_to_reference
            for _, states in evaluation.analyzer_results
            for state in states
            if state.singularity_ratio_to_reference is not None
        ]
        if not values:
            raise ConstraintDefinitionError("Analyzer singularity diagnostics are unavailable")
        return min(values)
    if definition.evaluator == "candidate_scalar":
        if definition.variable_id is None:
            raise ConstraintDefinitionError("candidate_scalar requires variable_id")
        try:
            return dict(evaluation.candidate_values)[definition.variable_id]
        except KeyError as exc:
            raise ConstraintDefinitionError(
                f"Candidate is missing {definition.variable_id!r}"
            ) from exc
    raise ConstraintDefinitionError(
        f"Unsupported evaluator {definition.evaluator!r}"
    )


def evaluate_constraint_set(
    constraint_set: SteeringConstraintSet,
    evaluation: CandidateEvaluation,
) -> tuple[SupplementalConstraintResult, ...]:
    """Evaluate every active or unavailable provider constraint."""

    results: list[SupplementalConstraintResult] = []
    for definition in constraint_set.constraints:
        if definition.availability is ConstraintAvailability.UNAVAILABLE:
            results.append(
                SupplementalConstraintResult(
                    constraint_id=definition.constraint_id,
                    disposition=ConstraintDisposition.UNAVAILABLE,
                    value=None,
                    lower_limit=definition.lower_limit,
                    upper_limit=definition.upper_limit,
                    margin=None,
                    unit=definition.unit,
                    state=definition.state,
                    authority=definition.authority,
                    blocking=False,
                    message=definition.unavailable_reason,
                )
            )
            continue
        try:
            value = _evaluate_value(definition, evaluation)
            margin = _minimum_margin(
                value, definition.lower_limit, definition.upper_limit
            )
            passed = margin >= 0.0
            results.append(
                SupplementalConstraintResult(
                    constraint_id=definition.constraint_id,
                    disposition=(
                        ConstraintDisposition.PASSED
                        if passed
                        else ConstraintDisposition.FAILED
                    ),
                    value=value,
                    lower_limit=definition.lower_limit,
                    upper_limit=definition.upper_limit,
                    margin=margin,
                    unit=definition.unit,
                    state=definition.state,
                    authority=definition.authority,
                    blocking=definition.blocking,
                    message=(
                        "Constraint satisfied"
                        if passed
                        else "Constraint violated"
                    ),
                )
            )
        except ConstraintDefinitionError as exc:
            results.append(
                SupplementalConstraintResult(
                    constraint_id=definition.constraint_id,
                    disposition=ConstraintDisposition.UNAVAILABLE,
                    value=None,
                    lower_limit=definition.lower_limit,
                    upper_limit=definition.upper_limit,
                    margin=None,
                    unit=definition.unit,
                    state=definition.state,
                    authority=definition.authority,
                    blocking=False,
                    message=f"Evaluation unavailable: {exc}",
                )
            )
    return tuple(results)


def screen_candidate_evaluation(
    evaluation: CandidateEvaluation,
    constraint_set: SteeringConstraintSet,
) -> ScreenedCandidateEvaluation:
    """Apply supplemental constraints without changing the base analyzer result."""

    if not evaluation.feasible:
        return ScreenedCandidateEvaluation(
            base_evaluation=evaluation,
            constraint_set_id=constraint_set.constraint_set_id,
            supplemental_constraints=evaluate_constraint_set(
                constraint_set, evaluation
            ),
            feasible=False,
            failure_code=evaluation.failure_code,
            failure_message=evaluation.failure_message,
        )

    results = evaluate_constraint_set(constraint_set, evaluation)
    failed = next(
        (
            item
            for item in results
            if item.blocking and item.disposition is ConstraintDisposition.FAILED
        ),
        None,
    )
    return ScreenedCandidateEvaluation(
        base_evaluation=evaluation,
        constraint_set_id=constraint_set.constraint_set_id,
        supplemental_constraints=results,
        feasible=failed is None,
        failure_code=failed.constraint_id if failed is not None else None,
        failure_message=failed.message if failed is not None else "",
    )
