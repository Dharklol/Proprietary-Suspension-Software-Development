"""Conservative suspension spring force, energy, and generalized-force provider.

Implements AUTH-SUSP-0004 / EQ-SUSP-0013 through EQ-SUSP-0015.

The module is intentionally limited to conservative spring behavior. It does not
evaluate damper force, anti-roll-bar force, tire force, vehicle equilibrium,
installed travel/stops, linkage loads, stress, or production limits.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Iterable, Sequence

from .actuation import ActuationStateResult


class SuspensionSpringError(ValueError):
    """Raised for malformed spring definitions, not ordinary unavailable states."""


class SpringStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class SpringFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    MISSING_SPRING_PARAMETER_AUTHORITY = "missing_spring_parameter_authority"
    MISSING_REFERENCE_LENGTH = "missing_reference_length"
    SPRING_UNSEATED = "spring_unseated"
    CONSTITUTIVE_DOMAIN_EXCEEDED = "constitutive_domain_exceeded"
    INVALID_ENERGY_LAW = "invalid_energy_law"
    UPSTREAM_ACTUATION_FAILURE = "upstream_actuation_failure"
    JACOBIAN_UNAVAILABLE = "jacobian_unavailable"


class SpringLawKind(str, Enum):
    LINEAR = "linear"
    AFFINE_TANGENT = "affine_tangent"
    PIECEWISE_LINEAR_FORCE = "piecewise_linear_force"


@dataclass(frozen=True)
class SpringDefinition:
    spring_id: str
    kind: SpringLawKind
    free_length_m: float
    source_id: str
    configuration_id: str
    assumption_ids: tuple[str, ...] = ()
    installed_as_built_authority: bool = False
    linear_rate_N_per_m: float | None = None
    tangent_rate_intercept_N_per_m: float | None = None
    tangent_rate_gradient_N_per_m2: float | None = None
    domain_min_m: float = 0.0
    domain_max_m: float | None = None
    force_points: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.spring_id or not self.source_id or not self.configuration_id:
            raise SuspensionSpringError("Spring identity, source identity, and configuration identity are required")
        if not math.isfinite(self.free_length_m) or self.free_length_m <= 0.0:
            raise SuspensionSpringError("Spring free length must be finite and positive")
        if not math.isfinite(self.domain_min_m) or self.domain_min_m != 0.0:
            raise SuspensionSpringError("First spring provider requires constitutive domain to start at x_s=0")
        if self.domain_max_m is not None:
            if not math.isfinite(self.domain_max_m) or self.domain_max_m <= self.domain_min_m:
                raise SuspensionSpringError("Spring constitutive upper domain must exceed the lower domain")

        if self.kind is SpringLawKind.LINEAR:
            if self.linear_rate_N_per_m is None or not math.isfinite(self.linear_rate_N_per_m) or self.linear_rate_N_per_m <= 0.0:
                raise SuspensionSpringError("Linear spring requires a finite positive rate")
        elif self.kind is SpringLawKind.AFFINE_TANGENT:
            if (
                self.tangent_rate_intercept_N_per_m is None
                or self.tangent_rate_gradient_N_per_m2 is None
                or not math.isfinite(self.tangent_rate_intercept_N_per_m)
                or not math.isfinite(self.tangent_rate_gradient_N_per_m2)
                or self.tangent_rate_intercept_N_per_m <= 0.0
            ):
                raise SuspensionSpringError("Affine-tangent spring requires finite tangent-rate intercept and gradient")
            if self.domain_max_m is None:
                raise SuspensionSpringError("Affine-tangent spring requires an explicit upper constitutive domain")
            k_end = self.tangent_rate_intercept_N_per_m + self.tangent_rate_gradient_N_per_m2 * self.domain_max_m
            if not math.isfinite(k_end) or k_end <= 0.0:
                raise SuspensionSpringError("Affine-tangent spring rate must remain positive over its domain")
        elif self.kind is SpringLawKind.PIECEWISE_LINEAR_FORCE:
            if len(self.force_points) < 2:
                raise SuspensionSpringError("Piecewise-linear force law requires at least two points")
            last_x = -math.inf
            for x_m, force_N in self.force_points:
                if not math.isfinite(x_m) or not math.isfinite(force_N):
                    raise SuspensionSpringError("Piecewise-linear spring points must be finite")
                if x_m <= last_x:
                    raise SuspensionSpringError("Piecewise-linear spring compression coordinates must be strictly increasing")
                if x_m < 0.0 or force_N < 0.0:
                    raise SuspensionSpringError("Piecewise-linear spring points must have nonnegative compression and force")
                last_x = x_m
            if self.force_points[0] != (0.0, 0.0):
                raise SuspensionSpringError("First piecewise-linear force point must be the zero-load seated reference (0, 0)")
            if self.domain_min_m != self.force_points[0][0]:
                raise SuspensionSpringError("Piecewise-linear lower domain must match first force point")
            if self.domain_max_m is not None and not math.isclose(
                self.domain_max_m, self.force_points[-1][0], rel_tol=0.0, abs_tol=1.0e-15
            ):
                raise SuspensionSpringError("Piecewise-linear upper domain must match last force point when supplied")
        else:  # pragma: no cover - Enum construction prevents this in ordinary use.
            raise SuspensionSpringError(f"Unsupported spring law kind: {self.kind}")


@dataclass(frozen=True)
class SpringReference:
    reference_id: str
    configuration_id: str
    reference_coilover_length_m: float
    preload_compression_m: float = 0.0
    assumption_ids: tuple[str, ...] = ()
    installed_as_built_authority: bool = False

    def __post_init__(self) -> None:
        if not self.reference_id or not self.configuration_id:
            raise SuspensionSpringError("Spring reference identity and configuration identity are required")
        if not math.isfinite(self.reference_coilover_length_m) or self.reference_coilover_length_m <= 0.0:
            raise SuspensionSpringError("Reference coilover length must be finite and positive")
        if not math.isfinite(self.preload_compression_m) or self.preload_compression_m < 0.0:
            raise SuspensionSpringError("Intentional preload compression must be finite and nonnegative")


@dataclass(frozen=True)
class SpringCompressionResult:
    status: SpringStatus
    x_s_m: float | None = None
    seat_separation_m: float | None = None
    current_coilover_length_m: float | None = None
    reference_coilover_length_m: float | None = None
    preload_compression_m: float | None = None
    source_id: str = ""
    configuration_id: str = ""
    assumption_ids: tuple[str, ...] = ()
    failure_code: SpringFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SpringStatus.SUCCESS


@dataclass(frozen=True)
class SpringConstitutiveResult:
    status: SpringStatus
    x_s_m: float | None = None
    force_N: float | None = None
    stored_energy_J: float | None = None
    tangent_stiffness_N_per_m: float | None = None
    segment_index: int | None = None
    spring_id: str = ""
    source_id: str = ""
    configuration_id: str = ""
    assumption_ids: tuple[str, ...] = ()
    installed_as_built_authority: bool = False
    failure_code: SpringFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SpringStatus.SUCCESS


@dataclass(frozen=True)
class SpringGeneralizedForceResult:
    status: SpringStatus
    coordinate_order: tuple[str, ...] = ()
    coordinate_units: tuple[str, ...] = ()
    dL_dq: tuple[float, ...] = ()
    generalized_force: tuple[float, ...] = ()
    force_N: float | None = None
    failure_code: SpringFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SpringStatus.SUCCESS


@dataclass(frozen=True)
class SpringStateResult:
    status: SpringStatus
    spring_id: str
    source_id: str
    configuration_id: str
    assumption_ids: tuple[str, ...] = ()
    x_s_m: float | None = None
    seat_separation_m: float | None = None
    current_coilover_length_m: float | None = None
    force_N: float | None = None
    stored_energy_J: float | None = None
    tangent_stiffness_N_per_m: float | None = None
    segment_index: int | None = None
    coordinate_order: tuple[str, ...] = ()
    coordinate_units: tuple[str, ...] = ()
    dL_dq: tuple[float, ...] = ()
    generalized_force: tuple[float, ...] = ()
    generalized_force_available: bool = False
    installed_as_built_authority: bool = False
    failure_code: SpringFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SpringStatus.SUCCESS


@dataclass(frozen=True)
class SpringEnergyCheckResult:
    status: SpringStatus
    expected_generalized_force: float | None = None
    finite_difference_generalized_force: tuple[float, ...] = ()
    step_sizes: tuple[float, ...] = ()
    absolute_residuals: tuple[float, ...] = ()
    failure_code: SpringFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is SpringStatus.SUCCESS


@dataclass(frozen=True)
class WufrSpringPackage:
    configuration_id: str
    source_record_id: str
    front: SpringDefinition
    rear: SpringDefinition
    reference: SpringReference
    front_nominal_coilover_length_m: float
    rear_nominal_coilover_length_m: float
    front_nominal_force_N: float
    rear_nominal_force_N: float
    rear_nominal_tangent_rate_N_per_m: float
    shockpot_reported_raw: str
    installed_as_built_authority: bool = False


def compression_from_seat_length(
    *,
    free_length_m: float,
    seat_separation_m: float,
    source_id: str = "",
    configuration_id: str = "",
    assumption_ids: Sequence[str] = (),
) -> SpringCompressionResult:
    """EQ-SUSP-0013 from physical spring-seat separation: x_s=L_free-L_seat."""
    if not math.isfinite(free_length_m) or not math.isfinite(seat_separation_m):
        return SpringCompressionResult(
            status=SpringStatus.FAILURE,
            source_id=source_id,
            configuration_id=configuration_id,
            assumption_ids=tuple(assumption_ids),
            failure_code=SpringFailureCode.NONFINITE_INPUT,
            message="Spring free length and seat separation must be finite",
        )
    if free_length_m <= 0.0 or seat_separation_m < 0.0:
        return SpringCompressionResult(
            status=SpringStatus.FAILURE,
            source_id=source_id,
            configuration_id=configuration_id,
            assumption_ids=tuple(assumption_ids),
            failure_code=SpringFailureCode.MISSING_SPRING_PARAMETER_AUTHORITY,
            message="Spring free length must be positive and seat separation must be nonnegative",
        )
    x_s = free_length_m - seat_separation_m
    if x_s < 0.0:
        return SpringCompressionResult(
            status=SpringStatus.FAILURE,
            x_s_m=x_s,
            seat_separation_m=seat_separation_m,
            source_id=source_id,
            configuration_id=configuration_id,
            assumption_ids=tuple(assumption_ids),
            failure_code=SpringFailureCode.SPRING_UNSEATED,
            message="Requested seated-spring state would require spring tension; compression was not clipped",
        )
    return SpringCompressionResult(
        status=SpringStatus.SUCCESS,
        x_s_m=x_s,
        seat_separation_m=seat_separation_m,
        source_id=source_id,
        configuration_id=configuration_id,
        assumption_ids=tuple(assumption_ids),
    )


def compression_from_coilover_reference(
    *,
    current_coilover_length_m: float,
    reference: SpringReference,
    free_length_m: float | None = None,
) -> SpringCompressionResult:
    """EQ-SUSP-0013 equivalent direct-coilover mapping.

    x_s = x_pre + L_ref - L_d. For the reviewed WUFR zero-preload reference,
    x_pre=0 and L_ref=0.1857 m.
    """
    if not math.isfinite(current_coilover_length_m):
        return SpringCompressionResult(
            status=SpringStatus.FAILURE,
            current_coilover_length_m=current_coilover_length_m,
            reference_coilover_length_m=reference.reference_coilover_length_m,
            preload_compression_m=reference.preload_compression_m,
            configuration_id=reference.configuration_id,
            assumption_ids=reference.assumption_ids,
            failure_code=SpringFailureCode.NONFINITE_INPUT,
            message="Current coilover length must be finite",
        )
    if current_coilover_length_m <= 0.0:
        return SpringCompressionResult(
            status=SpringStatus.FAILURE,
            current_coilover_length_m=current_coilover_length_m,
            reference_coilover_length_m=reference.reference_coilover_length_m,
            preload_compression_m=reference.preload_compression_m,
            configuration_id=reference.configuration_id,
            assumption_ids=reference.assumption_ids,
            failure_code=SpringFailureCode.MISSING_REFERENCE_LENGTH,
            message="Current coilover length must be positive",
        )

    x_s = reference.preload_compression_m + reference.reference_coilover_length_m - current_coilover_length_m
    seat_separation = None
    if free_length_m is not None:
        if not math.isfinite(free_length_m) or free_length_m <= 0.0:
            return SpringCompressionResult(
                status=SpringStatus.FAILURE,
                x_s_m=x_s,
                current_coilover_length_m=current_coilover_length_m,
                reference_coilover_length_m=reference.reference_coilover_length_m,
                preload_compression_m=reference.preload_compression_m,
                configuration_id=reference.configuration_id,
                assumption_ids=reference.assumption_ids,
                failure_code=SpringFailureCode.MISSING_SPRING_PARAMETER_AUTHORITY,
                message="Spring free length must be finite and positive when seat separation is requested",
            )
        seat_separation = free_length_m - x_s

    if x_s < 0.0:
        return SpringCompressionResult(
            status=SpringStatus.FAILURE,
            x_s_m=x_s,
            seat_separation_m=seat_separation,
            current_coilover_length_m=current_coilover_length_m,
            reference_coilover_length_m=reference.reference_coilover_length_m,
            preload_compression_m=reference.preload_compression_m,
            configuration_id=reference.configuration_id,
            assumption_ids=reference.assumption_ids,
            failure_code=SpringFailureCode.SPRING_UNSEATED,
            message="Requested seated-spring state would require spring tension; compression was not clipped",
        )
    return SpringCompressionResult(
        status=SpringStatus.SUCCESS,
        x_s_m=x_s,
        seat_separation_m=seat_separation,
        current_coilover_length_m=current_coilover_length_m,
        reference_coilover_length_m=reference.reference_coilover_length_m,
        preload_compression_m=reference.preload_compression_m,
        configuration_id=reference.configuration_id,
        assumption_ids=reference.assumption_ids,
    )


def _domain_failure(definition: SpringDefinition, x_s_m: float, message: str) -> SpringConstitutiveResult:
    return SpringConstitutiveResult(
        status=SpringStatus.FAILURE,
        x_s_m=x_s_m,
        spring_id=definition.spring_id,
        source_id=definition.source_id,
        configuration_id=definition.configuration_id,
        assumption_ids=definition.assumption_ids,
        installed_as_built_authority=definition.installed_as_built_authority,
        failure_code=SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED,
        message=message,
    )


def evaluate_spring_law(definition: SpringDefinition, x_s_m: float) -> SpringConstitutiveResult:
    """EQ-SUSP-0014 conservative force, stored energy, and tangent stiffness."""
    provenance = dict(
        spring_id=definition.spring_id,
        source_id=definition.source_id,
        configuration_id=definition.configuration_id,
        assumption_ids=definition.assumption_ids,
        installed_as_built_authority=definition.installed_as_built_authority,
    )
    if not math.isfinite(x_s_m):
        return SpringConstitutiveResult(
            status=SpringStatus.FAILURE,
            x_s_m=x_s_m,
            failure_code=SpringFailureCode.NONFINITE_INPUT,
            message="Spring compression must be finite",
            **provenance,
        )
    if x_s_m < 0.0:
        return SpringConstitutiveResult(
            status=SpringStatus.FAILURE,
            x_s_m=x_s_m,
            failure_code=SpringFailureCode.SPRING_UNSEATED,
            message="Negative compression is outside the seated-spring mode and was not clipped",
            **provenance,
        )
    if x_s_m < definition.domain_min_m:
        return _domain_failure(definition, x_s_m, "Spring compression is below the reviewed constitutive domain")
    if definition.domain_max_m is not None and x_s_m > definition.domain_max_m:
        return _domain_failure(definition, x_s_m, "Spring compression exceeds the reviewed constitutive domain")

    if definition.kind is SpringLawKind.LINEAR:
        k = float(definition.linear_rate_N_per_m)
        force = k * x_s_m
        energy = 0.5 * k * x_s_m * x_s_m
        tangent = k
        segment = None

    elif definition.kind is SpringLawKind.AFFINE_TANGENT:
        k0 = float(definition.tangent_rate_intercept_N_per_m)
        gradient = float(definition.tangent_rate_gradient_N_per_m2)
        force = k0 * x_s_m + 0.5 * gradient * x_s_m * x_s_m
        energy = 0.5 * k0 * x_s_m * x_s_m + (gradient / 6.0) * x_s_m**3
        tangent = k0 + gradient * x_s_m
        segment = None

    elif definition.kind is SpringLawKind.PIECEWISE_LINEAR_FORCE:
        points = definition.force_points
        x_values = tuple(point[0] for point in points)
        if x_s_m > points[-1][0]:
            return _domain_failure(definition, x_s_m, "Spring compression exceeds the force-table domain")
        index = min(max(bisect_right(x_values, x_s_m) - 1, 0), len(points) - 2)
        x0, f0 = points[index]
        x1, f1 = points[index + 1]
        tangent = (f1 - f0) / (x1 - x0)
        force = f0 + tangent * (x_s_m - x0)

        energy = 0.0
        for j in range(index):
            xa, fa = points[j]
            xb, fb = points[j + 1]
            energy += 0.5 * (fa + fb) * (xb - xa)
        energy += 0.5 * (f0 + force) * (x_s_m - x0)
        segment = index
    else:  # pragma: no cover
        return SpringConstitutiveResult(
            status=SpringStatus.FAILURE,
            x_s_m=x_s_m,
            failure_code=SpringFailureCode.MISSING_SPRING_PARAMETER_AUTHORITY,
            message="Unsupported spring constitutive kind",
            **provenance,
        )

    if not all(math.isfinite(value) for value in (force, energy, tangent)) or force < 0.0 or energy < 0.0 or tangent <= 0.0:
        return SpringConstitutiveResult(
            status=SpringStatus.FAILURE,
            x_s_m=x_s_m,
            failure_code=SpringFailureCode.INVALID_ENERGY_LAW,
            message="Constitutive evaluation produced a nonphysical/nonfinite conservative spring state",
            **provenance,
        )
    return SpringConstitutiveResult(
        status=SpringStatus.SUCCESS,
        x_s_m=x_s_m,
        force_N=force,
        stored_energy_J=energy,
        tangent_stiffness_N_per_m=tangent,
        segment_index=segment,
        **provenance,
    )


def generalized_spring_force(
    force_N: float,
    dL_dq: float | Iterable[float],
    *,
    coordinate_order: Sequence[str] = (),
    coordinate_units: Sequence[str] = (),
) -> SpringGeneralizedForceResult:
    """EQ-SUSP-0015 map spring force by Q_s=F_s*dL_d/dq."""
    derivatives = (float(dL_dq),) if isinstance(dL_dq, (int, float)) else tuple(float(value) for value in dL_dq)
    order = tuple(coordinate_order)
    units = tuple(coordinate_units)
    if not math.isfinite(force_N) or force_N < 0.0 or not derivatives or not all(math.isfinite(value) for value in derivatives):
        return SpringGeneralizedForceResult(
            status=SpringStatus.FAILURE,
            coordinate_order=order,
            coordinate_units=units,
            dL_dq=derivatives,
            force_N=force_N,
            failure_code=SpringFailureCode.JACOBIAN_UNAVAILABLE,
            message="Spring force and dL_d/dq must be finite, with at least one derivative component",
        )
    if order and len(order) != len(derivatives):
        return SpringGeneralizedForceResult(
            status=SpringStatus.FAILURE,
            coordinate_order=order,
            coordinate_units=units,
            dL_dq=derivatives,
            force_N=force_N,
            failure_code=SpringFailureCode.JACOBIAN_UNAVAILABLE,
            message="Coordinate order length must match dL_d/dq length",
        )
    if units and len(units) != len(derivatives):
        return SpringGeneralizedForceResult(
            status=SpringStatus.FAILURE,
            coordinate_order=order,
            coordinate_units=units,
            dL_dq=derivatives,
            force_N=force_N,
            failure_code=SpringFailureCode.JACOBIAN_UNAVAILABLE,
            message="Coordinate units length must match dL_d/dq length",
        )
    generalized = tuple(force_N * value for value in derivatives)
    return SpringGeneralizedForceResult(
        status=SpringStatus.SUCCESS,
        coordinate_order=order,
        coordinate_units=units,
        dL_dq=derivatives,
        generalized_force=generalized,
        force_N=force_N,
    )


def check_spring_energy_gradient(
    definition: SpringDefinition,
    x_s_m: float,
    dL_dq: float,
    *,
    step_sizes: Sequence[float] = (1.0e-6, 5.0e-7),
) -> SpringEnergyCheckResult:
    """Independent local finite-difference check of EQ-SUSP-0015.

    The check holds the supplied local ``dL_d/dq`` constant only for the tiny
    verification perturbation. Since ``x_s = constant - L_d``,
    ``x(q+h)=x_s-dL_dq*h`` and ``Q=-dU/dq``.
    """
    if (
        not math.isfinite(x_s_m)
        or not math.isfinite(dL_dq)
        or not step_sizes
        or not all(math.isfinite(step) and step > 0.0 for step in step_sizes)
    ):
        return SpringEnergyCheckResult(
            status=SpringStatus.FAILURE,
            failure_code=SpringFailureCode.NONFINITE_INPUT,
            message="Energy-check state, derivative, and step sizes must be finite with positive steps",
        )
    center = evaluate_spring_law(definition, x_s_m)
    if not center.ok or center.force_N is None:
        return SpringEnergyCheckResult(
            status=SpringStatus.FAILURE,
            failure_code=center.failure_code,
            message=center.message or "Center spring state is unavailable for energy check",
        )
    expected = center.force_N * dL_dq
    finite_difference: list[float] = []
    residuals: list[float] = []
    for step in step_sizes:
        x_plus = x_s_m - dL_dq * step
        x_minus = x_s_m + dL_dq * step
        plus = evaluate_spring_law(definition, x_plus)
        minus = evaluate_spring_law(definition, x_minus)
        if not plus.ok or not minus.ok or plus.stored_energy_J is None or minus.stored_energy_J is None:
            failure = plus if not plus.ok else minus
            return SpringEnergyCheckResult(
                status=SpringStatus.FAILURE,
                expected_generalized_force=expected,
                finite_difference_generalized_force=tuple(finite_difference),
                step_sizes=tuple(step_sizes),
                absolute_residuals=tuple(residuals),
                failure_code=failure.failure_code or SpringFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED,
                message=failure.message or "Energy-check perturbation left the reviewed spring domain",
            )
        q_fd = -(plus.stored_energy_J - minus.stored_energy_J) / (2.0 * step)
        finite_difference.append(q_fd)
        residuals.append(abs(q_fd - expected))
    return SpringEnergyCheckResult(
        status=SpringStatus.SUCCESS,
        expected_generalized_force=expected,
        finite_difference_generalized_force=tuple(finite_difference),
        step_sizes=tuple(float(step) for step in step_sizes),
        absolute_residuals=tuple(residuals),
    )


def evaluate_spring_from_coilover(
    definition: SpringDefinition,
    reference: SpringReference,
    current_coilover_length_m: float,
    *,
    dL_dq: float | Iterable[float] | None = None,
    coordinate_order: Sequence[str] = (),
    coordinate_units: Sequence[str] = (),
) -> SpringStateResult:
    """Compose EQ-SUSP-0013/0014/0015 from a current direct-coilover length."""
    if definition.configuration_id != reference.configuration_id:
        return SpringStateResult(
            status=SpringStatus.FAILURE,
            spring_id=definition.spring_id,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=definition.assumption_ids,
            installed_as_built_authority=definition.installed_as_built_authority,
            failure_code=SpringFailureCode.MISSING_REFERENCE_LENGTH,
            message="Spring definition and reference configuration identities do not match",
        )

    assumptions = tuple(dict.fromkeys((*definition.assumption_ids, *reference.assumption_ids)))
    compression = compression_from_coilover_reference(
        current_coilover_length_m=current_coilover_length_m,
        reference=reference,
        free_length_m=definition.free_length_m,
    )
    if not compression.ok or compression.x_s_m is None:
        return SpringStateResult(
            status=SpringStatus.FAILURE,
            spring_id=definition.spring_id,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=assumptions,
            x_s_m=compression.x_s_m,
            seat_separation_m=compression.seat_separation_m,
            current_coilover_length_m=current_coilover_length_m,
            installed_as_built_authority=definition.installed_as_built_authority and reference.installed_as_built_authority,
            failure_code=compression.failure_code,
            message=compression.message,
        )

    constitutive = evaluate_spring_law(definition, compression.x_s_m)
    if not constitutive.ok:
        return SpringStateResult(
            status=SpringStatus.FAILURE,
            spring_id=definition.spring_id,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=assumptions,
            x_s_m=compression.x_s_m,
            seat_separation_m=compression.seat_separation_m,
            current_coilover_length_m=current_coilover_length_m,
            installed_as_built_authority=definition.installed_as_built_authority and reference.installed_as_built_authority,
            failure_code=constitutive.failure_code,
            message=constitutive.message,
        )

    order: tuple[str, ...] = ()
    units: tuple[str, ...] = ()
    derivatives: tuple[float, ...] = ()
    q_values: tuple[float, ...] = ()
    q_available = False
    if dL_dq is not None and constitutive.force_N is not None:
        q_result = generalized_spring_force(
            constitutive.force_N,
            dL_dq,
            coordinate_order=coordinate_order,
            coordinate_units=coordinate_units,
        )
        if not q_result.ok:
            return SpringStateResult(
                status=SpringStatus.FAILURE,
                spring_id=definition.spring_id,
                source_id=definition.source_id,
                configuration_id=definition.configuration_id,
                assumption_ids=assumptions,
                x_s_m=compression.x_s_m,
                seat_separation_m=compression.seat_separation_m,
                current_coilover_length_m=current_coilover_length_m,
                force_N=constitutive.force_N,
                stored_energy_J=constitutive.stored_energy_J,
                tangent_stiffness_N_per_m=constitutive.tangent_stiffness_N_per_m,
                segment_index=constitutive.segment_index,
                installed_as_built_authority=definition.installed_as_built_authority and reference.installed_as_built_authority,
                failure_code=q_result.failure_code,
                message=q_result.message,
            )
        order = q_result.coordinate_order
        units = q_result.coordinate_units
        derivatives = q_result.dL_dq
        q_values = q_result.generalized_force
        q_available = True

    return SpringStateResult(
        status=SpringStatus.SUCCESS,
        spring_id=definition.spring_id,
        source_id=definition.source_id,
        configuration_id=definition.configuration_id,
        assumption_ids=assumptions,
        x_s_m=compression.x_s_m,
        seat_separation_m=compression.seat_separation_m,
        current_coilover_length_m=current_coilover_length_m,
        force_N=constitutive.force_N,
        stored_energy_J=constitutive.stored_energy_J,
        tangent_stiffness_N_per_m=constitutive.tangent_stiffness_N_per_m,
        segment_index=constitutive.segment_index,
        coordinate_order=order,
        coordinate_units=units,
        dL_dq=derivatives,
        generalized_force=q_values,
        generalized_force_available=q_available,
        installed_as_built_authority=definition.installed_as_built_authority and reference.installed_as_built_authority,
    )


def evaluate_spring_from_actuation(
    definition: SpringDefinition,
    reference: SpringReference,
    actuation_state: ActuationStateResult,
    *,
    dL_dq: float | Iterable[float] | None = None,
    coordinate_order: Sequence[str] = (),
    coordinate_units: Sequence[str] = (),
    use_local_rho_dw_when_available: bool = True,
) -> SpringStateResult:
    """Compose a successful MOD-SUSP-0003 actuation state with the spring provider."""
    if not actuation_state.ok or actuation_state.current_coilover_length_m is None:
        return SpringStateResult(
            status=SpringStatus.FAILURE,
            spring_id=definition.spring_id,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=tuple(dict.fromkeys((*definition.assumption_ids, *reference.assumption_ids))),
            installed_as_built_authority=False,
            failure_code=SpringFailureCode.UPSTREAM_ACTUATION_FAILURE,
            message=actuation_state.message or "MOD-SUSP-0003 actuation state is unavailable",
        )
    if actuation_state.configuration_id and actuation_state.configuration_id != definition.configuration_id:
        return SpringStateResult(
            status=SpringStatus.FAILURE,
            spring_id=definition.spring_id,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=tuple(dict.fromkeys((*definition.assumption_ids, *reference.assumption_ids))),
            installed_as_built_authority=False,
            failure_code=SpringFailureCode.MISSING_SPRING_PARAMETER_AUTHORITY,
            message="Actuation and spring configuration identities do not match",
        )

    derivative = dL_dq
    order = tuple(coordinate_order)
    units = tuple(coordinate_units)
    if derivative is None and use_local_rho_dw_when_available and actuation_state.rho_dw is not None:
        derivative = actuation_state.rho_dw
        order = ("delta_z_wc_body_m",)
        units = ("m",)

    return evaluate_spring_from_coilover(
        definition,
        reference,
        actuation_state.current_coilover_length_m,
        dL_dq=derivative,
        coordinate_order=order,
        coordinate_units=units,
    )


def load_wufr27_spring_package(path: str | Path) -> WufrSpringPackage:
    """Load the frozen WUFR27_SPRING_PACKAGE_V0 design-intent source adapter."""
    source_path = Path(path)
    with source_path.open("rb") as stream:
        data = tomllib.load(stream)

    configuration_id = str(data["configuration_id"])
    source_record_id = str(data["record_id"])
    installed_authority = bool(data.get("installed_as_built_authority", False))
    setup = data["reviewed_setup"]
    rear_span = float(setup["rear_progression_span_m"])
    assumption_ids = ("ASM-SUSP-0002",)

    front = SpringDefinition(
        spring_id="WUFR27_FRONT_SPRING_V0",
        kind=SpringLawKind.LINEAR,
        free_length_m=float(setup["spring_free_length_m"]),
        source_id=source_record_id,
        configuration_id=configuration_id,
        assumption_ids=assumption_ids,
        installed_as_built_authority=installed_authority,
        linear_rate_N_per_m=float(setup["front_linear_rate_N_per_m"]),
        domain_min_m=0.0,
    )
    rear = SpringDefinition(
        spring_id="WUFR27_REAR_SPRING_V0",
        kind=SpringLawKind.AFFINE_TANGENT,
        free_length_m=float(setup["spring_free_length_m"]),
        source_id=source_record_id,
        configuration_id=configuration_id,
        assumption_ids=assumption_ids,
        installed_as_built_authority=installed_authority,
        tangent_rate_intercept_N_per_m=float(setup["rear_rate_start_N_per_m"]),
        tangent_rate_gradient_N_per_m2=float(setup["rear_tangent_rate_gradient_N_per_m2"]),
        domain_min_m=0.0,
        domain_max_m=rear_span,
    )
    reference_data = data["wufr27_zero_preload_reference"]
    reference = SpringReference(
        reference_id="WUFR27_KW_ZERO_PRELOAD_FULL_EXTENSION_V0",
        configuration_id=configuration_id,
        reference_coilover_length_m=float(reference_data["full_extension_eye_to_eye_m"]),
        preload_compression_m=0.0,
        assumption_ids=assumption_ids,
        installed_as_built_authority=False,
    )
    return WufrSpringPackage(
        configuration_id=configuration_id,
        source_record_id=source_record_id,
        front=front,
        rear=rear,
        reference=reference,
        front_nominal_coilover_length_m=float(reference_data["front_nominal_L_d_m"]),
        rear_nominal_coilover_length_m=float(reference_data["rear_nominal_L_d_m"]),
        front_nominal_force_N=float(reference_data["front_nominal_force_N_under_reviewed_model"]),
        rear_nominal_force_N=float(reference_data["rear_nominal_force_N_under_reviewed_model"]),
        rear_nominal_tangent_rate_N_per_m=float(reference_data["rear_nominal_tangent_rate_N_per_m_under_reviewed_model"]),
        shockpot_reported_raw=str(data["shockpot_ride_height_note"]["reported_raw"]),
        installed_as_built_authority=installed_authority,
    )
