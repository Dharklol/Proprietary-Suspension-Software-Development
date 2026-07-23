"""Local finite-difference sensitivity for analyzer-composed steering candidates.

Every perturbation is role-resolved, regenerated, and reevaluated through the existing
candidate evaluator. The result is descriptive local sensitivity, not tolerance or
robustness authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from ..core import SteeringGeometry
from .constraints import (
    ConstraintDisposition,
    ScreenedCandidateEvaluation,
    SteeringConstraintSet,
    screen_candidate_evaluation,
)
from .evaluation import evaluate_candidate
from .roles import (
    ParameterRole,
    RequirementSet,
    ResolvedCandidate,
    VariableDefinition,
    resolve_candidate,
)
from .targets import SteeringTarget


class SensitivityConfigurationError(ValueError):
    """Raised when a local sensitivity request is invalid."""


@dataclass(frozen=True)
class SensitivitySettings:
    relative_step_fraction: float = 0.002
    minimum_absolute_step: float = 1.0e-7
    variable_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.relative_step_fraction) or self.relative_step_fraction <= 0.0:
            raise SensitivityConfigurationError(
                "relative_step_fraction must be finite and positive"
            )
        if not math.isfinite(self.minimum_absolute_step) or self.minimum_absolute_step <= 0.0:
            raise SensitivityConfigurationError(
                "minimum_absolute_step must be finite and positive"
            )


@dataclass(frozen=True)
class ConstraintMarginSensitivity:
    constraint_id: str
    derivative_per_unit: float | None
    normalized_derivative: float | None
    unit: str
    message: str


@dataclass(frozen=True)
class VariableSensitivity:
    variable_id: str
    variable_unit: str
    base_value: float
    step: float
    scheme: str
    lower_value: float | None
    upper_value: float | None
    objective_derivative_per_unit: float | None
    normalized_objective_derivative: float | None
    constraint_margin_sensitivities: tuple[ConstraintMarginSensitivity, ...]
    lower_feasible: bool | None
    upper_feasible: bool | None
    message: str


@dataclass(frozen=True)
class LocalSensitivityResult:
    candidate_id: str
    requirement_set_id: str
    target_id: str
    constraint_set_id: str | None
    base_evaluation: ScreenedCandidateEvaluation | None
    variable_results: tuple[VariableSensitivity, ...]
    status: str
    message: str
    provenance: tuple[tuple[str, str], ...]


def _screen(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    target: SteeringTarget,
    constraint_set: SteeringConstraintSet | None,
) -> ScreenedCandidateEvaluation:
    evaluation = evaluate_candidate(baseline, requirement_set, candidate, target)
    if constraint_set is None:
        return ScreenedCandidateEvaluation(
            base_evaluation=evaluation,
            constraint_set_id="none",
            supplemental_constraints=(),
            feasible=evaluation.feasible,
            failure_code=evaluation.failure_code,
            failure_message=evaluation.failure_message,
        )
    return screen_candidate_evaluation(evaluation, constraint_set)


def _variables(
    requirement_set: RequirementSet,
    requested: tuple[str, ...],
) -> tuple[VariableDefinition, ...]:
    if requested:
        if len(set(requested)) != len(requested):
            raise SensitivityConfigurationError("variable_ids contains duplicates")
        variables = tuple(requirement_set.variable(item) for item in requested)
    else:
        variables = tuple(
            item
            for item in requirement_set.variables
            if item.role is ParameterRole.BOUNDED_DESIGN_VARIABLE
        )
    for variable in variables:
        if variable.role is not ParameterRole.BOUNDED_DESIGN_VARIABLE:
            raise SensitivityConfigurationError(
                f"Variable {variable.id!r} is not a bounded design variable"
            )
        if variable.minimum is None or variable.maximum is None:
            raise SensitivityConfigurationError(
                f"Variable {variable.id!r} is missing bounds"
            )
    return variables


def _numeric_constraint_margins(
    screened: ScreenedCandidateEvaluation,
) -> dict[str, tuple[float, str]]:
    values: dict[str, tuple[float, str]] = {}
    for item in screened.base_evaluation.constraints:
        if item.margin is not None:
            values[item.constraint_id] = (item.margin, item.unit)
    for item in screened.supplemental_constraints:
        if item.disposition is not ConstraintDisposition.UNAVAILABLE and item.margin is not None:
            values[item.constraint_id] = (item.margin, item.unit)
    return values


def _derivative(
    lower_value: float | None,
    base_value: float,
    upper_value: float | None,
    step: float,
) -> tuple[float | None, str]:
    if lower_value is not None and upper_value is not None:
        return (upper_value - lower_value) / (2.0 * step), "central"
    if upper_value is not None:
        return (upper_value - base_value) / step, "forward"
    if lower_value is not None:
        return (base_value - lower_value) / step, "backward"
    return None, "unavailable"


def analyze_local_sensitivity(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    target: SteeringTarget,
    *,
    constraint_set: SteeringConstraintSet | None = None,
    settings: SensitivitySettings | None = None,
) -> LocalSensitivityResult:
    """Evaluate finite-difference sensitivities around one feasible candidate."""

    settings = settings or SensitivitySettings()
    variables = _variables(requirement_set, settings.variable_ids)
    base = _screen(baseline, requirement_set, candidate, target, constraint_set)
    provenance = (
        ("evaluator_model_id", "MOD-STEER-0001"),
        ("optimizer_model_id", "MOD-STEER-0002"),
        ("method", "bounded_finite_difference_v0.1.0"),
        ("target_id", target.target_id),
        (
            "constraint_set_id",
            constraint_set.constraint_set_id if constraint_set is not None else "none",
        ),
    )
    if not base.feasible or base.total_objective is None:
        return LocalSensitivityResult(
            candidate_id=candidate.candidate_id,
            requirement_set_id=requirement_set.id,
            target_id=target.target_id,
            constraint_set_id=(
                constraint_set.constraint_set_id if constraint_set is not None else None
            ),
            base_evaluation=base,
            variable_results=(),
            status="base_candidate_infeasible",
            message=base.failure_message,
            provenance=provenance,
        )

    base_values = dict(candidate.values)
    base_objective = base.total_objective
    base_margins = _numeric_constraint_margins(base)
    results: list[VariableSensitivity] = []

    for variable in variables:
        assert variable.minimum is not None
        assert variable.maximum is not None
        span = variable.maximum - variable.minimum
        requested_step = max(
            span * settings.relative_step_fraction,
            settings.minimum_absolute_step,
        )
        lower_room = base_values[variable.id] - variable.minimum
        upper_room = variable.maximum - base_values[variable.id]
        central_step = min(requested_step, lower_room, upper_room)
        lower_screen: ScreenedCandidateEvaluation | None = None
        upper_screen: ScreenedCandidateEvaluation | None = None
        lower_value: float | None = None
        upper_value: float | None = None
        step = requested_step

        if central_step > 0.0:
            step = central_step
            lower_overrides = dict(base_values)
            upper_overrides = dict(base_values)
            lower_overrides[variable.id] -= step
            upper_overrides[variable.id] += step
            lower_candidate = resolve_candidate(
                requirement_set,
                lower_overrides,
                candidate_id=f"{candidate.candidate_id}-SENS-{variable.id}-LOW",
            )
            upper_candidate = resolve_candidate(
                requirement_set,
                upper_overrides,
                candidate_id=f"{candidate.candidate_id}-SENS-{variable.id}-HIGH",
            )
            lower_screen = _screen(
                baseline, requirement_set, lower_candidate, target, constraint_set
            )
            upper_screen = _screen(
                baseline, requirement_set, upper_candidate, target, constraint_set
            )
            if lower_screen.feasible:
                lower_value = lower_screen.total_objective
            if upper_screen.feasible:
                upper_value = upper_screen.total_objective
        elif upper_room > 0.0:
            step = min(requested_step, upper_room)
            upper_overrides = dict(base_values)
            upper_overrides[variable.id] += step
            upper_candidate = resolve_candidate(
                requirement_set,
                upper_overrides,
                candidate_id=f"{candidate.candidate_id}-SENS-{variable.id}-HIGH",
            )
            upper_screen = _screen(
                baseline, requirement_set, upper_candidate, target, constraint_set
            )
            if upper_screen.feasible:
                upper_value = upper_screen.total_objective
        elif lower_room > 0.0:
            step = min(requested_step, lower_room)
            lower_overrides = dict(base_values)
            lower_overrides[variable.id] -= step
            lower_candidate = resolve_candidate(
                requirement_set,
                lower_overrides,
                candidate_id=f"{candidate.candidate_id}-SENS-{variable.id}-LOW",
            )
            lower_screen = _screen(
                baseline, requirement_set, lower_candidate, target, constraint_set
            )
            if lower_screen.feasible:
                lower_value = lower_screen.total_objective
        else:
            results.append(
                VariableSensitivity(
                    variable_id=variable.id,
                    variable_unit=variable.unit,
                    base_value=base_values[variable.id],
                    step=0.0,
                    scheme="unavailable",
                    lower_value=None,
                    upper_value=None,
                    objective_derivative_per_unit=None,
                    normalized_objective_derivative=None,
                    constraint_margin_sensitivities=(),
                    lower_feasible=None,
                    upper_feasible=None,
                    message="No perturbation room remains inside the variable bounds",
                )
            )
            continue

        objective_derivative, scheme = _derivative(
            lower_value, base_objective, upper_value, step
        )
        normalized_objective_derivative = (
            objective_derivative * span
            if objective_derivative is not None
            else None
        )

        lower_margins = (
            _numeric_constraint_margins(lower_screen)
            if lower_screen is not None and lower_screen.feasible
            else {}
        )
        upper_margins = (
            _numeric_constraint_margins(upper_screen)
            if upper_screen is not None and upper_screen.feasible
            else {}
        )
        margin_results: list[ConstraintMarginSensitivity] = []
        for constraint_id, (base_margin, unit) in sorted(base_margins.items()):
            lower_margin = lower_margins.get(constraint_id, (None, unit))[0]
            upper_margin = upper_margins.get(constraint_id, (None, unit))[0]
            derivative, margin_scheme = _derivative(
                lower_margin,
                base_margin,
                upper_margin,
                step,
            )
            margin_results.append(
                ConstraintMarginSensitivity(
                    constraint_id=constraint_id,
                    derivative_per_unit=derivative,
                    normalized_derivative=(
                        derivative * span if derivative is not None else None
                    ),
                    unit=f"{unit}_per_{variable.unit}",
                    message=f"{margin_scheme} finite difference",
                )
            )

        results.append(
            VariableSensitivity(
                variable_id=variable.id,
                variable_unit=variable.unit,
                base_value=base_values[variable.id],
                step=step,
                scheme=scheme,
                lower_value=lower_value,
                upper_value=upper_value,
                objective_derivative_per_unit=objective_derivative,
                normalized_objective_derivative=normalized_objective_derivative,
                constraint_margin_sensitivities=tuple(margin_results),
                lower_feasible=(
                    lower_screen.feasible if lower_screen is not None else None
                ),
                upper_feasible=(
                    upper_screen.feasible if upper_screen is not None else None
                ),
                message=(
                    "Objective derivative available"
                    if objective_derivative is not None
                    else "Perturbed candidates did not provide enough feasible values"
                ),
            )
        )

    return LocalSensitivityResult(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        target_id=target.target_id,
        constraint_set_id=(
            constraint_set.constraint_set_id if constraint_set is not None else None
        ),
        base_evaluation=base,
        variable_results=tuple(results),
        status="complete",
        message=(
            "Local finite-difference sensitivities are descriptive and do not establish "
            "manufacturing tolerance or robustness authority"
        ),
        provenance=provenance,
    )
