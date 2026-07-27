"""Provider-neutral reduced-coordinate conservative quasi-static equilibrium.

Authorized by ``AUTH-VEH-0004``.  This module deliberately contains no WUFR
mass defaults and no legacy load-transfer/crossweight equations.  It composes
explicit provider outputs through the reviewed virtual-work coordinate contract:

    z_w = z_w(q_b)
    R_b = Q_body_ext + J_wb.T @ Q_susp_w

and, after the reduced body state converges, recovers active-contact road-normal
reactions from explicit wheel-coordinate equilibrium:

    Q_susp_i + Q_wheel_ext_i + c_i * lambda_i = 0.

The first implementation is quasi-static only.  Damping, transient inertia,
tire constitutive laws, aero/brake/powertrain models, alternate contact modes,
linkage loads, and installed/as-built claims remain outside this module.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
import math


Vector = tuple[float, ...]
Matrix = tuple[Vector, ...]


class QuasiStaticStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class QuasiStaticFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    COORDINATE_CONTRACT_MISMATCH = "coordinate_contract_mismatch"
    COMPATIBILITY_PROVIDER_FAILURE = "compatibility_provider_failure"
    SUSPENSION_PROVIDER_FAILURE = "suspension_provider_failure"
    BODY_EXTERNAL_PROVIDER_FAILURE = "body_external_provider_failure"
    MISSING_WHEEL_EXTERNAL_FORCE_AUTHORITY = "missing_wheel_external_force_authority"
    MISSING_MASS_FORCE_AUTHORITY = "missing_mass_force_authority"
    MISSING_CONTACT_COEFFICIENT = "missing_contact_coefficient"
    SINGULAR_OR_ILL_CONDITIONED_TANGENT = "singular_or_ill_conditioned_tangent"
    COORDINATE_BOUND_EXCEEDED = "coordinate_bound_exceeded"
    LINE_SEARCH_FAILURE = "line_search_failure"
    NONCONVERGENCE = "nonconvergence"
    NEGATIVE_NORMAL_REACTION = "negative_normal_reaction"
    CONTACT_MODE_INVALID = "contact_mode_invalid"
    ENERGY_GRADIENT_UNAVAILABLE = "energy_gradient_unavailable"
    ENERGY_GRADIENT_DISAGREEMENT = "energy_gradient_disagreement"


@dataclass(frozen=True)
class CompatibilityState:
    status: QuasiStaticStatus
    wheel_coordinates: Vector = ()
    J_wb: Matrix = ()
    wheel_coordinate_order: tuple[str, ...] = ()
    wheel_coordinate_units: tuple[str, ...] = ()
    source_id: str = ""
    configuration_id: str = ""
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class SuspensionGeneralizedForceState:
    status: QuasiStaticStatus
    generalized_wheel_force: Vector = ()
    stored_energy_J: float | None = None
    coordinate_order: tuple[str, ...] = ()
    coordinate_units: tuple[str, ...] = ()
    source_id: str = ""
    configuration_id: str = ""
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class BodyExternalGeneralizedForceState:
    status: QuasiStaticStatus
    generalized_force: Vector = ()
    potential_energy_J: float | None = None
    coordinate_order: tuple[str, ...] = ()
    coordinate_units: tuple[str, ...] = ()
    source_id: str = ""
    configuration_id: str = ""
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


CompatibilityProvider = Callable[[Vector], CompatibilityState]
SuspensionProvider = Callable[[Vector], SuspensionGeneralizedForceState]
BodyExternalProvider = Callable[[Vector], BodyExternalGeneralizedForceState]


@dataclass(frozen=True)
class QuasiStaticEvaluation:
    status: QuasiStaticStatus
    q_body: Vector
    body_coordinate_order: tuple[str, ...]
    body_coordinate_units: tuple[str, ...]
    compatibility: CompatibilityState | None = None
    suspension: SuspensionGeneralizedForceState | None = None
    body_external: BodyExternalGeneralizedForceState | None = None
    residual: Vector = ()
    scaled_residual: Vector = ()
    scaled_residual_norm: float | None = None
    total_potential_energy_J: float | None = None
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class QuasiStaticSolverConfig:
    coordinate_scales: Vector
    residual_scales: Vector
    lower_bounds: tuple[float | None, ...] = ()
    upper_bounds: tuple[float | None, ...] = ()
    residual_absolute_tolerance: float = 1.0e-10
    residual_relative_tolerance: float = 1.0e-10
    max_iterations: int = 30
    finite_difference_relative_step: float = 1.0e-5
    finite_difference_min_step: float = 1.0e-8
    line_search_reduction: float = 0.5
    line_search_max_trials: int = 14
    minimum_reciprocal_pivot_ratio: float = 1.0e-11
    pivot_absolute_tolerance: float = 1.0e-14

    def __post_init__(self) -> None:
        if not self.coordinate_scales or len(self.coordinate_scales) != len(self.residual_scales):
            raise ValueError("Coordinate and residual scales must be nonempty and have equal length")
        if not all(math.isfinite(value) and value > 0.0 for value in self.coordinate_scales):
            raise ValueError("Coordinate scales must be finite and positive")
        if not all(math.isfinite(value) and value > 0.0 for value in self.residual_scales):
            raise ValueError("Residual scales must be finite and positive")
        if self.lower_bounds and len(self.lower_bounds) != len(self.coordinate_scales):
            raise ValueError("Lower-bound length must match coordinate scale length")
        if self.upper_bounds and len(self.upper_bounds) != len(self.coordinate_scales):
            raise ValueError("Upper-bound length must match coordinate scale length")
        for bounds in (self.lower_bounds, self.upper_bounds):
            for value in bounds:
                if value is not None and not math.isfinite(value):
                    raise ValueError("Finite coordinate bounds are required when supplied")
        if self.lower_bounds and self.upper_bounds:
            for lower, upper in zip(self.lower_bounds, self.upper_bounds):
                if lower is not None and upper is not None and lower >= upper:
                    raise ValueError("Each finite lower coordinate bound must be below its upper bound")
        numeric_positive = (
            self.residual_absolute_tolerance,
            self.residual_relative_tolerance,
            self.finite_difference_relative_step,
            self.finite_difference_min_step,
            self.minimum_reciprocal_pivot_ratio,
            self.pivot_absolute_tolerance,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in numeric_positive):
            raise ValueError("Solver tolerances/steps must be finite and positive")
        if not (0.0 < self.line_search_reduction < 1.0):
            raise ValueError("Line-search reduction must lie strictly between zero and one")
        if self.max_iterations <= 0 or self.line_search_max_trials <= 0:
            raise ValueError("Iteration limits must be positive")


@dataclass(frozen=True)
class QuasiStaticSolveResult:
    status: QuasiStaticStatus
    q_body: Vector
    body_coordinate_order: tuple[str, ...]
    body_coordinate_units: tuple[str, ...]
    wheel_coordinates: Vector = ()
    wheel_coordinate_order: tuple[str, ...] = ()
    wheel_coordinate_units: tuple[str, ...] = ()
    residual: Vector = ()
    scaled_residual: Vector = ()
    scaled_residual_norm: float | None = None
    iterations: int = 0
    initial_scaled_residual_norm: float | None = None
    convergence_threshold: float | None = None
    tangent_methods: tuple[str, ...] = ()
    tangent_steps: Vector = ()
    reciprocal_pivot_ratio: float | None = None
    line_search_scale: float | None = None
    suspension_stored_energy_J: float | None = None
    total_potential_energy_J: float | None = None
    compatibility_source_id: str = ""
    suspension_source_id: str = ""
    body_external_source_id: str = ""
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class ContactRecoveryResult:
    status: QuasiStaticStatus
    coordinate_order: tuple[str, ...]
    coordinate_units: tuple[str, ...]
    suspension_generalized_force: Vector = ()
    wheel_external_generalized_force: Vector = ()
    contact_coefficients: Vector = ()
    normal_reaction_N: Vector = ()
    wheel_equilibrium_residual: Vector = ()
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class EnergyGradientCheckResult:
    status: QuasiStaticStatus
    q_body: Vector
    expected_generalized_force: Vector = ()
    finite_difference_generalized_force: tuple[Vector, ...] = ()
    relative_step_multipliers: Vector = ()
    maximum_absolute_residual: float | None = None
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class _TangentResult:
    status: QuasiStaticStatus
    matrix: Matrix = ()
    methods: tuple[str, ...] = ()
    steps: Vector = ()
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


@dataclass(frozen=True)
class _LinearSolveResult:
    status: QuasiStaticStatus
    solution: Vector = ()
    reciprocal_pivot_ratio: float | None = None
    failure_code: QuasiStaticFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is QuasiStaticStatus.SUCCESS


def _finite_vector(values: Sequence[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _scaled_inf_norm(values: Sequence[float], scales: Sequence[float]) -> float:
    return max(abs(float(value) / float(scale)) for value, scale in zip(values, scales))


def _bounds(config: QuasiStaticSolverConfig) -> tuple[tuple[float | None, ...], tuple[float | None, ...]]:
    n = len(config.coordinate_scales)
    lower = config.lower_bounds or (None,) * n
    upper = config.upper_bounds or (None,) * n
    return lower, upper


def _inside_bounds(q_body: Sequence[float], config: QuasiStaticSolverConfig) -> bool:
    lower, upper = _bounds(config)
    for value, lo, hi in zip(q_body, lower, upper):
        if lo is not None and value < lo:
            return False
        if hi is not None and value > hi:
            return False
    return True


def _failure_evaluation(
    q_body: Vector,
    coordinate_order: tuple[str, ...],
    coordinate_units: tuple[str, ...],
    code: QuasiStaticFailureCode,
    message: str,
    *,
    compatibility: CompatibilityState | None = None,
    suspension: SuspensionGeneralizedForceState | None = None,
    body_external: BodyExternalGeneralizedForceState | None = None,
) -> QuasiStaticEvaluation:
    return QuasiStaticEvaluation(
        status=QuasiStaticStatus.FAILURE,
        q_body=q_body,
        body_coordinate_order=coordinate_order,
        body_coordinate_units=coordinate_units,
        compatibility=compatibility,
        suspension=suspension,
        body_external=body_external,
        failure_code=code,
        message=message,
    )


def evaluate_quasi_static_residual(
    q_body: Sequence[float],
    *,
    body_coordinate_order: Sequence[str],
    body_coordinate_units: Sequence[str],
    compatibility_provider: CompatibilityProvider,
    suspension_provider: SuspensionProvider,
    body_external_provider: BodyExternalProvider,
    residual_scales: Sequence[float],
) -> QuasiStaticEvaluation:
    """Evaluate ``R_b=Q_body_ext+J_wb^T Q_susp_w`` at one body state."""
    q = tuple(float(value) for value in q_body)
    order = tuple(body_coordinate_order)
    units = tuple(body_coordinate_units)
    scales = tuple(float(value) for value in residual_scales)
    n_body = len(q)
    if (
        n_body == 0
        or len(order) != n_body
        or len(units) != n_body
        or len(scales) != n_body
        or not _finite_vector(q)
        or not _finite_vector(scales)
        or any(value <= 0.0 for value in scales)
    ):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            "Body coordinates, order, units, and positive residual scales must have equal nonzero length",
        )

    try:
        compatibility = compatibility_provider(q)
    except Exception as exc:  # provider boundary: preserve structured kernel failure
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
            f"Compatibility provider raised {type(exc).__name__}: {exc}",
        )
    if not compatibility.ok:
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
            compatibility.message or "Compatibility provider failed",
            compatibility=compatibility,
        )

    z_w = tuple(float(value) for value in compatibility.wheel_coordinates)
    n_wheel = len(z_w)
    if (
        n_wheel == 0
        or len(compatibility.wheel_coordinate_order) != n_wheel
        or len(compatibility.wheel_coordinate_units) != n_wheel
        or len(compatibility.J_wb) != n_wheel
        or not _finite_vector(z_w)
        or not compatibility.source_id
    ):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            "Compatibility output has invalid wheel-coordinate identity, dimensions, or provenance",
            compatibility=compatibility,
        )
    for row in compatibility.J_wb:
        if len(row) != n_body or not _finite_vector(row):
            return _failure_evaluation(
                q,
                order,
                units,
                QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
                "Compatibility Jacobian must have shape (n_wheel,n_body) with finite entries",
                compatibility=compatibility,
            )

    try:
        suspension = suspension_provider(z_w)
    except Exception as exc:
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.SUSPENSION_PROVIDER_FAILURE,
            f"Suspension provider raised {type(exc).__name__}: {exc}",
            compatibility=compatibility,
        )
    if not suspension.ok:
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.SUSPENSION_PROVIDER_FAILURE,
            suspension.message or "Suspension provider failed",
            compatibility=compatibility,
            suspension=suspension,
        )
    q_susp = tuple(float(value) for value in suspension.generalized_wheel_force)
    if (
        len(q_susp) != n_wheel
        or tuple(suspension.coordinate_order) != tuple(compatibility.wheel_coordinate_order)
        or tuple(suspension.coordinate_units) != tuple(compatibility.wheel_coordinate_units)
        or not _finite_vector(q_susp)
        or not suspension.source_id
    ):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            "Suspension generalized force must match the compatibility wheel-coordinate order/units",
            compatibility=compatibility,
            suspension=suspension,
        )
    if suspension.stored_energy_J is not None and not math.isfinite(suspension.stored_energy_J):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.SUSPENSION_PROVIDER_FAILURE,
            "Suspension stored energy must be finite when supplied",
            compatibility=compatibility,
            suspension=suspension,
        )

    try:
        body_external = body_external_provider(q)
    except Exception as exc:
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.BODY_EXTERNAL_PROVIDER_FAILURE,
            f"Body external-force provider raised {type(exc).__name__}: {exc}",
            compatibility=compatibility,
            suspension=suspension,
        )
    if not body_external.ok:
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.BODY_EXTERNAL_PROVIDER_FAILURE,
            body_external.message or "Body external-force provider failed",
            compatibility=compatibility,
            suspension=suspension,
            body_external=body_external,
        )
    q_body_external = tuple(float(value) for value in body_external.generalized_force)
    if (
        len(q_body_external) != n_body
        or tuple(body_external.coordinate_order) != order
        or tuple(body_external.coordinate_units) != units
        or not _finite_vector(q_body_external)
        or not body_external.source_id
    ):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            "Body external generalized force must match the body coordinate order/units",
            compatibility=compatibility,
            suspension=suspension,
            body_external=body_external,
        )
    if body_external.potential_energy_J is not None and not math.isfinite(body_external.potential_energy_J):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.BODY_EXTERNAL_PROVIDER_FAILURE,
            "Body external potential energy must be finite when supplied",
            compatibility=compatibility,
            suspension=suspension,
            body_external=body_external,
        )

    mapped_suspension = []
    for j in range(n_body):
        mapped_suspension.append(
            sum(float(compatibility.J_wb[i][j]) * q_susp[i] for i in range(n_wheel))
        )
    residual = tuple(q_body_external[j] + mapped_suspension[j] for j in range(n_body))
    if not _finite_vector(residual):
        return _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.NONFINITE_INPUT,
            "Assembled quasi-static residual is nonfinite",
            compatibility=compatibility,
            suspension=suspension,
            body_external=body_external,
        )
    scaled = tuple(residual[i] / scales[i] for i in range(n_body))
    norm = max(abs(value) for value in scaled)
    total_potential = None
    if suspension.stored_energy_J is not None and body_external.potential_energy_J is not None:
        total_potential = suspension.stored_energy_J + body_external.potential_energy_J
    return QuasiStaticEvaluation(
        status=QuasiStaticStatus.SUCCESS,
        q_body=q,
        body_coordinate_order=order,
        body_coordinate_units=units,
        compatibility=compatibility,
        suspension=suspension,
        body_external=body_external,
        residual=residual,
        scaled_residual=scaled,
        scaled_residual_norm=norm,
        total_potential_energy_J=total_potential,
    )


def _numerical_scaled_tangent(
    q_body: Vector,
    *,
    body_coordinate_order: tuple[str, ...],
    body_coordinate_units: tuple[str, ...],
    compatibility_provider: CompatibilityProvider,
    suspension_provider: SuspensionProvider,
    body_external_provider: BodyExternalProvider,
    config: QuasiStaticSolverConfig,
) -> _TangentResult:
    n = len(q_body)
    lower, upper = _bounds(config)
    columns: list[Vector] = []
    methods: list[str] = []
    actual_steps: list[float] = []

    center = evaluate_quasi_static_residual(
        q_body,
        body_coordinate_order=body_coordinate_order,
        body_coordinate_units=body_coordinate_units,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        residual_scales=config.residual_scales,
    )
    if not center.ok:
        return _TangentResult(
            QuasiStaticStatus.FAILURE,
            failure_code=center.failure_code,
            message=center.message,
        )

    for j in range(n):
        requested = max(
            config.finite_difference_relative_step * config.coordinate_scales[j],
            config.finite_difference_min_step,
        )
        minus_allowed = lower[j] is None or q_body[j] - requested >= lower[j]
        plus_allowed = upper[j] is None or q_body[j] + requested <= upper[j]
        minus_eval: QuasiStaticEvaluation | None = None
        plus_eval: QuasiStaticEvaluation | None = None
        if minus_allowed:
            q_minus = list(q_body)
            q_minus[j] -= requested
            minus_eval = evaluate_quasi_static_residual(
                q_minus,
                body_coordinate_order=body_coordinate_order,
                body_coordinate_units=body_coordinate_units,
                compatibility_provider=compatibility_provider,
                suspension_provider=suspension_provider,
                body_external_provider=body_external_provider,
                residual_scales=config.residual_scales,
            )
            if not minus_eval.ok:
                return _TangentResult(
                    QuasiStaticStatus.FAILURE,
                    methods=tuple(methods),
                    steps=tuple(actual_steps),
                    failure_code=(
                        minus_eval.failure_code
                        or QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE
                    ),
                    message=(
                        f"Finite-difference minus perturbation failed for body coordinate {j}: "
                        f"{minus_eval.message}"
                    ),
                )
        if plus_allowed:
            q_plus = list(q_body)
            q_plus[j] += requested
            plus_eval = evaluate_quasi_static_residual(
                q_plus,
                body_coordinate_order=body_coordinate_order,
                body_coordinate_units=body_coordinate_units,
                compatibility_provider=compatibility_provider,
                suspension_provider=suspension_provider,
                body_external_provider=body_external_provider,
                residual_scales=config.residual_scales,
            )
            if not plus_eval.ok:
                return _TangentResult(
                    QuasiStaticStatus.FAILURE,
                    methods=tuple(methods),
                    steps=tuple(actual_steps),
                    failure_code=(
                        plus_eval.failure_code
                        or QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE
                    ),
                    message=(
                        f"Finite-difference plus perturbation failed for body coordinate {j}: "
                        f"{plus_eval.message}"
                    ),
                )

        if minus_allowed and plus_allowed:
            assert minus_eval is not None and plus_eval is not None
            denominator_normalized = 2.0 * requested / config.coordinate_scales[j]
            column = tuple(
                (plus_eval.scaled_residual[i] - minus_eval.scaled_residual[i])
                / denominator_normalized
                for i in range(n)
            )
            method = "centered_scaled_residual"
            actual = requested
        elif not minus_allowed and plus_allowed:
            assert plus_eval is not None
            denominator_normalized = requested / config.coordinate_scales[j]
            column = tuple(
                (plus_eval.scaled_residual[i] - center.scaled_residual[i])
                / denominator_normalized
                for i in range(n)
            )
            method = "forward_one_sided_scaled_residual"
            actual = requested
        elif minus_allowed and not plus_allowed:
            assert minus_eval is not None
            denominator_normalized = requested / config.coordinate_scales[j]
            column = tuple(
                (center.scaled_residual[i] - minus_eval.scaled_residual[i])
                / denominator_normalized
                for i in range(n)
            )
            method = "backward_one_sided_scaled_residual"
            actual = requested
        else:
            return _TangentResult(
                QuasiStaticStatus.FAILURE,
                methods=tuple(methods),
                steps=tuple(actual_steps),
                failure_code=QuasiStaticFailureCode.COORDINATE_BOUND_EXCEEDED,
                message=f"No valid finite-difference perturbation is available for body coordinate {j}",
            )
        if not _finite_vector(column):
            return _TangentResult(
                QuasiStaticStatus.FAILURE,
                methods=tuple(methods),
                steps=tuple(actual_steps),
                failure_code=QuasiStaticFailureCode.NONFINITE_INPUT,
                message="Numerical quasi-static tangent contains a nonfinite column",
            )
        columns.append(column)
        methods.append(method)
        actual_steps.append(actual)

    rows = tuple(tuple(columns[j][i] for j in range(n)) for i in range(n))
    return _TangentResult(
        QuasiStaticStatus.SUCCESS,
        matrix=rows,
        methods=tuple(methods),
        steps=tuple(actual_steps),
    )


def _solve_linear_system(matrix: Matrix, rhs: Vector, config: QuasiStaticSolverConfig) -> _LinearSolveResult:
    n = len(rhs)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return _LinearSolveResult(
            QuasiStaticStatus.FAILURE,
            failure_code=QuasiStaticFailureCode.SINGULAR_OR_ILL_CONDITIONED_TANGENT,
            message="Quasi-static tangent must be square and match the residual dimension",
        )
    if not _finite_vector(rhs) or any(not _finite_vector(row) for row in matrix):
        return _LinearSolveResult(
            QuasiStaticStatus.FAILURE,
            failure_code=QuasiStaticFailureCode.NONFINITE_INPUT,
            message="Linearized quasi-static system contains nonfinite entries",
        )

    a = [list(row) for row in matrix]
    b = list(rhs)
    pivots: list[float] = []
    for k in range(n):
        pivot_row = max(range(k, n), key=lambda row: abs(a[row][k]))
        pivot = abs(a[pivot_row][k])
        if pivot <= config.pivot_absolute_tolerance:
            return _LinearSolveResult(
                QuasiStaticStatus.FAILURE,
                reciprocal_pivot_ratio=0.0,
                failure_code=QuasiStaticFailureCode.SINGULAR_OR_ILL_CONDITIONED_TANGENT,
                message=f"Scaled quasi-static tangent is singular at pivot {k}",
            )
        if pivot_row != k:
            a[k], a[pivot_row] = a[pivot_row], a[k]
            b[k], b[pivot_row] = b[pivot_row], b[k]
        pivots.append(abs(a[k][k]))
        for row in range(k + 1, n):
            factor = a[row][k] / a[k][k]
            a[row][k] = 0.0
            for column in range(k + 1, n):
                a[row][column] -= factor * a[k][column]
            b[row] -= factor * b[k]

    reciprocal_ratio = min(pivots) / max(pivots)
    if reciprocal_ratio < config.minimum_reciprocal_pivot_ratio:
        return _LinearSolveResult(
            QuasiStaticStatus.FAILURE,
            reciprocal_pivot_ratio=reciprocal_ratio,
            failure_code=QuasiStaticFailureCode.SINGULAR_OR_ILL_CONDITIONED_TANGENT,
            message=(
                "Scaled quasi-static tangent failed the reciprocal pivot-ratio threshold: "
                f"{reciprocal_ratio:.6g} < {config.minimum_reciprocal_pivot_ratio:.6g}"
            ),
        )

    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        remaining = sum(a[row][column] * x[column] for column in range(row + 1, n))
        pivot = a[row][row]
        if abs(pivot) <= config.pivot_absolute_tolerance:
            return _LinearSolveResult(
                QuasiStaticStatus.FAILURE,
                reciprocal_pivot_ratio=reciprocal_ratio,
                failure_code=QuasiStaticFailureCode.SINGULAR_OR_ILL_CONDITIONED_TANGENT,
                message="Back-substitution encountered a singular tangent pivot",
            )
        x[row] = (b[row] - remaining) / pivot
    if not _finite_vector(x):
        return _LinearSolveResult(
            QuasiStaticStatus.FAILURE,
            reciprocal_pivot_ratio=reciprocal_ratio,
            failure_code=QuasiStaticFailureCode.NONFINITE_INPUT,
            message="Quasi-static Newton step is nonfinite",
        )
    return _LinearSolveResult(
        QuasiStaticStatus.SUCCESS,
        solution=tuple(x),
        reciprocal_pivot_ratio=reciprocal_ratio,
    )


def _solve_result_from_evaluation(
    evaluation: QuasiStaticEvaluation,
    *,
    status: QuasiStaticStatus,
    iterations: int,
    initial_norm: float | None,
    threshold: float | None,
    tangent: _TangentResult | None = None,
    reciprocal_pivot_ratio: float | None = None,
    line_search_scale: float | None = None,
    failure_code: QuasiStaticFailureCode | None = None,
    message: str = "",
) -> QuasiStaticSolveResult:
    compatibility = evaluation.compatibility
    suspension = evaluation.suspension
    body_external = evaluation.body_external
    return QuasiStaticSolveResult(
        status=status,
        q_body=evaluation.q_body,
        body_coordinate_order=evaluation.body_coordinate_order,
        body_coordinate_units=evaluation.body_coordinate_units,
        wheel_coordinates=compatibility.wheel_coordinates if compatibility else (),
        wheel_coordinate_order=compatibility.wheel_coordinate_order if compatibility else (),
        wheel_coordinate_units=compatibility.wheel_coordinate_units if compatibility else (),
        residual=evaluation.residual,
        scaled_residual=evaluation.scaled_residual,
        scaled_residual_norm=evaluation.scaled_residual_norm,
        iterations=iterations,
        initial_scaled_residual_norm=initial_norm,
        convergence_threshold=threshold,
        tangent_methods=tangent.methods if tangent else (),
        tangent_steps=tangent.steps if tangent else (),
        reciprocal_pivot_ratio=reciprocal_pivot_ratio,
        line_search_scale=line_search_scale,
        suspension_stored_energy_J=(suspension.stored_energy_J if suspension else None),
        total_potential_energy_J=evaluation.total_potential_energy_J,
        compatibility_source_id=compatibility.source_id if compatibility else "",
        suspension_source_id=suspension.source_id if suspension else "",
        body_external_source_id=body_external.source_id if body_external else "",
        failure_code=failure_code,
        message=message,
    )


def solve_quasi_static_equilibrium(
    initial_q_body: Sequence[float],
    *,
    body_coordinate_order: Sequence[str],
    body_coordinate_units: Sequence[str],
    compatibility_provider: CompatibilityProvider,
    suspension_provider: SuspensionProvider,
    body_external_provider: BodyExternalProvider,
    config: QuasiStaticSolverConfig,
) -> QuasiStaticSolveResult:
    """Solve the AUTH-VEH-0004 reduced quasi-static residual with damped Newton."""
    q = tuple(float(value) for value in initial_q_body)
    order = tuple(body_coordinate_order)
    units = tuple(body_coordinate_units)
    n = len(config.coordinate_scales)
    if (
        len(q) != n
        or len(order) != n
        or len(units) != n
        or not _finite_vector(q)
    ):
        evaluation = _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            "Initial body coordinates/order/units must match the solver scale dimension",
        )
        return _solve_result_from_evaluation(
            evaluation,
            status=QuasiStaticStatus.FAILURE,
            iterations=0,
            initial_norm=None,
            threshold=None,
            failure_code=evaluation.failure_code,
            message=evaluation.message,
        )
    if not _inside_bounds(q, config):
        evaluation = _failure_evaluation(
            q,
            order,
            units,
            QuasiStaticFailureCode.COORDINATE_BOUND_EXCEEDED,
            "Initial body state lies outside the declared coordinate bounds",
        )
        return _solve_result_from_evaluation(
            evaluation,
            status=QuasiStaticStatus.FAILURE,
            iterations=0,
            initial_norm=None,
            threshold=None,
            failure_code=evaluation.failure_code,
            message=evaluation.message,
        )

    evaluation = evaluate_quasi_static_residual(
        q,
        body_coordinate_order=order,
        body_coordinate_units=units,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        residual_scales=config.residual_scales,
    )
    if not evaluation.ok or evaluation.scaled_residual_norm is None:
        return _solve_result_from_evaluation(
            evaluation,
            status=QuasiStaticStatus.FAILURE,
            iterations=0,
            initial_norm=None,
            threshold=None,
            failure_code=evaluation.failure_code,
            message=evaluation.message,
        )

    initial_norm = evaluation.scaled_residual_norm
    threshold = config.residual_absolute_tolerance + config.residual_relative_tolerance * initial_norm
    if evaluation.scaled_residual_norm <= threshold:
        return _solve_result_from_evaluation(
            evaluation,
            status=QuasiStaticStatus.SUCCESS,
            iterations=0,
            initial_norm=initial_norm,
            threshold=threshold,
            message="Initial state satisfies the quasi-static residual tolerance",
        )

    last_tangent: _TangentResult | None = None
    last_pivot_ratio: float | None = None
    last_line_scale: float | None = None
    for iteration in range(1, config.max_iterations + 1):
        tangent = _numerical_scaled_tangent(
            evaluation.q_body,
            body_coordinate_order=order,
            body_coordinate_units=units,
            compatibility_provider=compatibility_provider,
            suspension_provider=suspension_provider,
            body_external_provider=body_external_provider,
            config=config,
        )
        last_tangent = tangent
        if not tangent.ok:
            return _solve_result_from_evaluation(
                evaluation,
                status=QuasiStaticStatus.FAILURE,
                iterations=iteration - 1,
                initial_norm=initial_norm,
                threshold=threshold,
                tangent=tangent,
                failure_code=tangent.failure_code,
                message=tangent.message,
            )

        linear = _solve_linear_system(
            tangent.matrix,
            tuple(-value for value in evaluation.scaled_residual),
            config,
        )
        last_pivot_ratio = linear.reciprocal_pivot_ratio
        if not linear.ok:
            return _solve_result_from_evaluation(
                evaluation,
                status=QuasiStaticStatus.FAILURE,
                iterations=iteration - 1,
                initial_norm=initial_norm,
                threshold=threshold,
                tangent=tangent,
                reciprocal_pivot_ratio=linear.reciprocal_pivot_ratio,
                failure_code=linear.failure_code,
                message=linear.message,
            )

        dimensional_step = tuple(
            linear.solution[i] * config.coordinate_scales[i] for i in range(n)
        )
        accepted: QuasiStaticEvaluation | None = None
        scale = 1.0
        for _ in range(config.line_search_max_trials):
            candidate_q = tuple(
                evaluation.q_body[i] + scale * dimensional_step[i] for i in range(n)
            )
            if _inside_bounds(candidate_q, config):
                candidate = evaluate_quasi_static_residual(
                    candidate_q,
                    body_coordinate_order=order,
                    body_coordinate_units=units,
                    compatibility_provider=compatibility_provider,
                    suspension_provider=suspension_provider,
                    body_external_provider=body_external_provider,
                    residual_scales=config.residual_scales,
                )
                if (
                    candidate.ok
                    and candidate.scaled_residual_norm is not None
                    and candidate.scaled_residual_norm < evaluation.scaled_residual_norm
                ):
                    accepted = candidate
                    break
            scale *= config.line_search_reduction
        last_line_scale = scale if accepted is not None else None
        if accepted is None:
            return _solve_result_from_evaluation(
                evaluation,
                status=QuasiStaticStatus.FAILURE,
                iterations=iteration - 1,
                initial_norm=initial_norm,
                threshold=threshold,
                tangent=tangent,
                reciprocal_pivot_ratio=linear.reciprocal_pivot_ratio,
                failure_code=QuasiStaticFailureCode.LINE_SEARCH_FAILURE,
                message="No bounded residual-reducing quasi-static Newton step was found",
            )

        evaluation = accepted
        if evaluation.scaled_residual_norm is not None and evaluation.scaled_residual_norm <= threshold:
            return _solve_result_from_evaluation(
                evaluation,
                status=QuasiStaticStatus.SUCCESS,
                iterations=iteration,
                initial_norm=initial_norm,
                threshold=threshold,
                tangent=tangent,
                reciprocal_pivot_ratio=linear.reciprocal_pivot_ratio,
                line_search_scale=scale,
                message="Quasi-static equilibrium converged",
            )

    return _solve_result_from_evaluation(
        evaluation,
        status=QuasiStaticStatus.FAILURE,
        iterations=config.max_iterations,
        initial_norm=initial_norm,
        threshold=threshold,
        tangent=last_tangent,
        reciprocal_pivot_ratio=last_pivot_ratio,
        line_search_scale=last_line_scale,
        failure_code=QuasiStaticFailureCode.NONCONVERGENCE,
        message="Quasi-static equilibrium did not converge within the declared iteration limit",
    )


def recover_active_contact_normal_reactions(
    suspension_state: SuspensionGeneralizedForceState,
    *,
    wheel_external_generalized_force: Sequence[float] | None,
    contact_coefficients: Sequence[float] | None,
) -> ContactRecoveryResult:
    """Recover ``lambda`` from explicit wheel-coordinate force equilibrium.

    ``wheel_external_generalized_force`` is intentionally required for a physical
    reaction result.  Passing ``None`` returns missing authority rather than
    assuming zero unsprung gravity or another hidden wheel-side load.
    """
    order = tuple(suspension_state.coordinate_order)
    units = tuple(suspension_state.coordinate_units)
    if not suspension_state.ok:
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=suspension_state.generalized_wheel_force,
            failure_code=QuasiStaticFailureCode.SUSPENSION_PROVIDER_FAILURE,
            message=suspension_state.message or "Suspension state is unavailable for contact recovery",
        )
    q_susp = tuple(float(value) for value in suspension_state.generalized_wheel_force)
    n = len(q_susp)
    if n == 0 or len(order) != n or len(units) != n or not _finite_vector(q_susp):
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            failure_code=QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            message="Suspension wheel generalized-force contract is invalid",
        )
    if wheel_external_generalized_force is None:
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            failure_code=QuasiStaticFailureCode.MISSING_WHEEL_EXTERNAL_FORCE_AUTHORITY,
            message=(
                "Wheel external generalized forces are required for physical road-reaction recovery; "
                "no zero/default wheel-side force was assumed"
            ),
        )
    q_external = tuple(float(value) for value in wheel_external_generalized_force)
    if len(q_external) != n or not _finite_vector(q_external):
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            wheel_external_generalized_force=q_external,
            failure_code=QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
            message="Wheel external generalized force must match the suspension wheel dimension",
        )
    if contact_coefficients is None:
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            wheel_external_generalized_force=q_external,
            failure_code=QuasiStaticFailureCode.MISSING_CONTACT_COEFFICIENT,
            message="Explicit signed contact coefficients are required for road-reaction recovery",
        )
    coefficients = tuple(float(value) for value in contact_coefficients)
    if (
        len(coefficients) != n
        or not _finite_vector(coefficients)
        or any(value == 0.0 for value in coefficients)
    ):
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            wheel_external_generalized_force=q_external,
            contact_coefficients=coefficients,
            failure_code=QuasiStaticFailureCode.MISSING_CONTACT_COEFFICIENT,
            message="Contact coefficients must be finite, nonzero, and match the wheel dimension",
        )

    reactions = tuple(
        -(q_susp[i] + q_external[i]) / coefficients[i] for i in range(n)
    )
    residuals = tuple(
        q_susp[i] + q_external[i] + coefficients[i] * reactions[i] for i in range(n)
    )
    if not _finite_vector(reactions) or not _finite_vector(residuals):
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            wheel_external_generalized_force=q_external,
            contact_coefficients=coefficients,
            normal_reaction_N=reactions,
            wheel_equilibrium_residual=residuals,
            failure_code=QuasiStaticFailureCode.NONFINITE_INPUT,
            message="Recovered contact reaction is nonfinite",
        )
    if any(value < 0.0 for value in reactions):
        return ContactRecoveryResult(
            QuasiStaticStatus.FAILURE,
            order,
            units,
            suspension_generalized_force=q_susp,
            wheel_external_generalized_force=q_external,
            contact_coefficients=coefficients,
            normal_reaction_N=reactions,
            wheel_equilibrium_residual=residuals,
            failure_code=QuasiStaticFailureCode.NEGATIVE_NORMAL_REACTION,
            message="Negative road-normal reaction invalidates the all-four-active contact mode; value was not clipped",
        )
    return ContactRecoveryResult(
        QuasiStaticStatus.SUCCESS,
        order,
        units,
        suspension_generalized_force=q_susp,
        wheel_external_generalized_force=q_external,
        contact_coefficients=coefficients,
        normal_reaction_N=reactions,
        wheel_equilibrium_residual=residuals,
    )


def check_total_potential_gradient(
    q_body: Sequence[float],
    *,
    body_coordinate_order: Sequence[str],
    body_coordinate_units: Sequence[str],
    compatibility_provider: CompatibilityProvider,
    suspension_provider: SuspensionProvider,
    body_external_provider: BodyExternalProvider,
    config: QuasiStaticSolverConfig,
    relative_step_multipliers: Sequence[float] = (1.0e-5, 5.0e-6),
    absolute_tolerance: float | None = None,
) -> EnergyGradientCheckResult:
    """Independently verify ``R_b=-dPi/dq`` at two or more declared steps."""
    q = tuple(float(value) for value in q_body)
    order = tuple(body_coordinate_order)
    units = tuple(body_coordinate_units)
    multipliers = tuple(float(value) for value in relative_step_multipliers)
    if (
        len(q) != len(config.coordinate_scales)
        or not _finite_vector(q)
        or len(multipliers) < 2
        or not _finite_vector(multipliers)
        or any(value <= 0.0 for value in multipliers)
    ):
        return EnergyGradientCheckResult(
            QuasiStaticStatus.FAILURE,
            q,
            relative_step_multipliers=multipliers,
            failure_code=QuasiStaticFailureCode.NONFINITE_INPUT,
            message="Energy-gradient check requires matching finite coordinates and at least two positive steps",
        )
    center = evaluate_quasi_static_residual(
        q,
        body_coordinate_order=order,
        body_coordinate_units=units,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        residual_scales=config.residual_scales,
    )
    if not center.ok or center.total_potential_energy_J is None:
        return EnergyGradientCheckResult(
            QuasiStaticStatus.FAILURE,
            q,
            expected_generalized_force=center.residual,
            relative_step_multipliers=multipliers,
            failure_code=QuasiStaticFailureCode.ENERGY_GRADIENT_UNAVAILABLE,
            message=center.message or "Both suspension and body external potential energies are required",
        )

    lower, upper = _bounds(config)
    finite_difference_sets: list[Vector] = []
    max_residual = 0.0
    for multiplier in multipliers:
        gradient_force: list[float] = []
        for j in range(len(q)):
            step = max(multiplier * config.coordinate_scales[j], config.finite_difference_min_step)
            q_minus = list(q)
            q_plus = list(q)
            q_minus[j] -= step
            q_plus[j] += step
            if (
                (lower[j] is not None and q_minus[j] < lower[j])
                or (upper[j] is not None and q_plus[j] > upper[j])
            ):
                return EnergyGradientCheckResult(
                    QuasiStaticStatus.FAILURE,
                    q,
                    expected_generalized_force=center.residual,
                    finite_difference_generalized_force=tuple(finite_difference_sets),
                    relative_step_multipliers=multipliers,
                    failure_code=QuasiStaticFailureCode.COORDINATE_BOUND_EXCEEDED,
                    message="Centered energy-gradient perturbation leaves the declared coordinate bounds",
                )
            minus = evaluate_quasi_static_residual(
                q_minus,
                body_coordinate_order=order,
                body_coordinate_units=units,
                compatibility_provider=compatibility_provider,
                suspension_provider=suspension_provider,
                body_external_provider=body_external_provider,
                residual_scales=config.residual_scales,
            )
            plus = evaluate_quasi_static_residual(
                q_plus,
                body_coordinate_order=order,
                body_coordinate_units=units,
                compatibility_provider=compatibility_provider,
                suspension_provider=suspension_provider,
                body_external_provider=body_external_provider,
                residual_scales=config.residual_scales,
            )
            if (
                not minus.ok
                or not plus.ok
                or minus.total_potential_energy_J is None
                or plus.total_potential_energy_J is None
            ):
                failure = minus if not minus.ok else plus
                return EnergyGradientCheckResult(
                    QuasiStaticStatus.FAILURE,
                    q,
                    expected_generalized_force=center.residual,
                    finite_difference_generalized_force=tuple(finite_difference_sets),
                    relative_step_multipliers=multipliers,
                    failure_code=QuasiStaticFailureCode.ENERGY_GRADIENT_UNAVAILABLE,
                    message=failure.message or "Potential-energy perturbation is unavailable",
                )
            generalized_force = -(
                plus.total_potential_energy_J - minus.total_potential_energy_J
            ) / (2.0 * step)
            gradient_force.append(generalized_force)
        fd = tuple(gradient_force)
        finite_difference_sets.append(fd)
        max_residual = max(
            max_residual,
            max(abs(fd[i] - center.residual[i]) for i in range(len(q))),
        )

    if absolute_tolerance is not None:
        if not math.isfinite(absolute_tolerance) or absolute_tolerance <= 0.0:
            return EnergyGradientCheckResult(
                QuasiStaticStatus.FAILURE,
                q,
                expected_generalized_force=center.residual,
                finite_difference_generalized_force=tuple(finite_difference_sets),
                relative_step_multipliers=multipliers,
                maximum_absolute_residual=max_residual,
                failure_code=QuasiStaticFailureCode.NONFINITE_INPUT,
                message="Energy-gradient absolute tolerance must be finite and positive",
            )
        if max_residual > absolute_tolerance:
            return EnergyGradientCheckResult(
                QuasiStaticStatus.FAILURE,
                q,
                expected_generalized_force=center.residual,
                finite_difference_generalized_force=tuple(finite_difference_sets),
                relative_step_multipliers=multipliers,
                maximum_absolute_residual=max_residual,
                failure_code=QuasiStaticFailureCode.ENERGY_GRADIENT_DISAGREEMENT,
                message=(
                    "Finite-difference potential gradient disagrees with assembled generalized force: "
                    f"{max_residual:.6g} > {absolute_tolerance:.6g}"
                ),
            )

    return EnergyGradientCheckResult(
        QuasiStaticStatus.SUCCESS,
        q,
        expected_generalized_force=center.residual,
        finite_difference_generalized_force=tuple(finite_difference_sets),
        relative_step_multipliers=multipliers,
        maximum_absolute_residual=max_residual,
    )
