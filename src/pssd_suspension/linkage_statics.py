"""Provider-neutral determinate suspension linkage statics.

Authorized by ``AUTH-SUSP-0010``.  The first implementation solves exactly one
rigid body supported by exactly six ideal pin-ended two-force links:

    A N = -W_ext

where each column of ``A`` is the unit-force wrench of one link about an
explicit reference point. Positive axial force means tension.

The module deliberately contains no WUFR load-case generator, tire/road force
model, spring/ARB/damper constitutive law, redundant-link force sharing, or
stress/factor-of-safety calculation.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
import math


Point3 = tuple[float, float, float]
Vector6 = tuple[float, float, float, float, float, float]
Matrix6 = tuple[Vector6, Vector6, Vector6, Vector6, Vector6, Vector6]


class LinkageStaticsStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class LinkageStaticsFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    FRAME_MISMATCH = "frame_mismatch"
    DUPLICATE_LINK_ID = "duplicate_link_id"
    DEGENERATE_LINK = "degenerate_link"
    UNSUPPORTED_TOPOLOGY = "unsupported_topology"
    DEGENERATE_CHARACTERISTIC_LENGTH = "degenerate_characteristic_length"
    SINGULAR_EQUILIBRIUM = "singular_equilibrium"
    ILL_CONDITIONED_EQUILIBRIUM = "ill_conditioned_equilibrium"
    LINEAR_SOLVE_FAILURE = "linear_solve_failure"
    EQUILIBRIUM_RESIDUAL_EXCEEDED = "equilibrium_residual_exceeded"


@dataclass(frozen=True)
class IdealTwoForceLink:
    link_id: str
    frame_id: str
    body_point_m: Point3
    remote_point_m: Point3
    source_id: str = ""
    configuration_id: str = ""


@dataclass(frozen=True)
class PrescribedExternalWrench:
    frame_id: str
    reference_point_m: Point3
    force_N: Point3
    moment_Nm: Point3
    load_case_id: str = ""
    source_id: str = ""


@dataclass(frozen=True)
class LinkGeometryState:
    link_id: str
    frame_id: str
    body_point_m: Point3
    remote_point_m: Point3
    length_m: float
    unit_axis_body_to_remote: Point3
    source_id: str = ""
    configuration_id: str = ""


@dataclass(frozen=True)
class LinkForceState:
    link_id: str
    axial_force_N: float
    body_force_N: Point3
    remote_force_N: Point3


@dataclass(frozen=True)
class LinkageStaticsSolverConfig:
    condition_limit: float = 1.0e10
    pivot_relative_threshold: float = 1.0e-12
    degenerate_link_tolerance_m: float = 1.0e-12
    characteristic_length_tolerance_m: float = 1.0e-12
    force_residual_tolerance_N: float = 1.0e-9
    moment_residual_tolerance_Nm: float = 1.0e-9

    def __post_init__(self) -> None:
        values = (
            self.condition_limit,
            self.pivot_relative_threshold,
            self.degenerate_link_tolerance_m,
            self.characteristic_length_tolerance_m,
            self.force_residual_tolerance_N,
            self.moment_residual_tolerance_Nm,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("All linkage-statics solver limits must be finite and positive")


@dataclass(frozen=True)
class LinkageStaticsResult:
    status: LinkageStaticsStatus
    frame_id: str
    reference_point_m: Point3
    external_force_N: Point3
    external_moment_Nm: Point3
    load_case_id: str = ""
    source_id: str = ""
    link_order: tuple[str, ...] = ()
    link_geometry: tuple[LinkGeometryState, ...] = ()
    link_forces: tuple[LinkForceState, ...] = ()
    equilibrium_matrix: Matrix6 | tuple[()] = ()
    rhs: Vector6 | tuple[()] = ()
    characteristic_length_m: float | None = None
    scaled_equilibrium_matrix: Matrix6 | tuple[()] = ()
    scaled_rhs: Vector6 | tuple[()] = ()
    condition_number_inf: float | None = None
    minimum_relative_pivot: float | None = None
    reconstructed_link_force_N: Point3 = (0.0, 0.0, 0.0)
    reconstructed_link_moment_Nm: Point3 = (0.0, 0.0, 0.0)
    force_residual_N: Point3 = (0.0, 0.0, 0.0)
    moment_residual_Nm: Point3 = (0.0, 0.0, 0.0)
    force_residual_inf_norm_N: float | None = None
    moment_residual_inf_norm_Nm: float | None = None
    failure_code: LinkageStaticsFailureCode | None = None
    message: str = ""
    authorization_id: str = "AUTH-SUSP-0010"
    assumption_id: str = "ASM-SUSP-0004"

    @property
    def ok(self) -> bool:
        return self.status is LinkageStaticsStatus.SUCCESS

    @property
    def axial_force_N(self) -> tuple[float, ...]:
        return tuple(state.axial_force_N for state in self.link_forces)


@dataclass(frozen=True)
class _DirectSolve:
    ok: bool
    solution: tuple[float, ...] = ()
    minimum_relative_pivot: float | None = None
    message: str = ""


def _point3(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("Expected a three-component Cartesian vector")
    return (float(values[0]), float(values[1]), float(values[2]))


def _finite3(values: Sequence[float]) -> bool:
    return len(values) == 3 and all(math.isfinite(float(value)) for value in values)


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(scalar: float, vector: Point3) -> Point3:
    return (scalar * vector[0], scalar * vector[1], scalar * vector[2])


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(vector: Point3) -> float:
    return math.sqrt(_dot(vector, vector))


def _cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _inf_norm3(vector: Point3) -> float:
    return max(abs(value) for value in vector)


def _matrix_inf_norm(matrix: Sequence[Sequence[float]]) -> float:
    return max(sum(abs(float(value)) for value in row) for row in matrix)


def _direct_solve(
    matrix: Sequence[Sequence[float]],
    rhs: Sequence[float],
    *,
    pivot_relative_threshold: float,
) -> _DirectSolve:
    n = len(rhs)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return _DirectSolve(False, message="Linear system must be finite and square")
    if any(not math.isfinite(float(value)) for value in rhs):
        return _DirectSolve(False, message="Linear-system right-hand side is nonfinite")
    if any(any(not math.isfinite(float(value)) for value in row) for row in matrix):
        return _DirectSolve(False, message="Linear-system matrix is nonfinite")

    scale = _matrix_inf_norm(matrix)
    if not math.isfinite(scale) or scale <= 0.0:
        return _DirectSolve(False, minimum_relative_pivot=0.0, message="Linear system has zero matrix norm")

    a = [[float(value) for value in row] for row in matrix]
    b = [float(value) for value in rhs]
    relative_pivots: list[float] = []

    for column in range(n):
        pivot_row = max(range(column, n), key=lambda row: abs(a[row][column]))
        pivot = abs(a[pivot_row][column])
        relative_pivot = pivot / scale
        if pivot == 0.0 or relative_pivot <= pivot_relative_threshold:
            return _DirectSolve(
                False,
                minimum_relative_pivot=min(relative_pivots + [relative_pivot]),
                message=f"Scaled equilibrium is singular/near-singular at pivot {column}",
            )
        if pivot_row != column:
            a[column], a[pivot_row] = a[pivot_row], a[column]
            b[column], b[pivot_row] = b[pivot_row], b[column]
        relative_pivots.append(abs(a[column][column]) / scale)
        for row in range(column + 1, n):
            factor = a[row][column] / a[column][column]
            a[row][column] = 0.0
            for j in range(column + 1, n):
                a[row][j] -= factor * a[column][j]
            b[row] -= factor * b[column]

    x = [0.0] * n
    for row in range(n - 1, -1, -1):
        pivot = a[row][row]
        relative_pivot = abs(pivot) / scale
        if pivot == 0.0 or relative_pivot <= pivot_relative_threshold:
            return _DirectSolve(
                False,
                minimum_relative_pivot=min(relative_pivots + [relative_pivot]),
                message=f"Back substitution encountered singular/near-singular pivot {row}",
            )
        remaining = sum(a[row][j] * x[j] for j in range(row + 1, n))
        x[row] = (b[row] - remaining) / pivot

    if not all(math.isfinite(value) for value in x):
        return _DirectSolve(False, minimum_relative_pivot=min(relative_pivots), message="Linear solution is nonfinite")
    return _DirectSolve(True, tuple(x), min(relative_pivots))


def _condition_number_inf(
    matrix: Sequence[Sequence[float]],
    *,
    pivot_relative_threshold: float,
) -> tuple[float | None, float | None, str]:
    n = len(matrix)
    norm_a = _matrix_inf_norm(matrix)
    inverse_columns: list[tuple[float, ...]] = []
    minimum_relative_pivot: float | None = None
    for column in range(n):
        rhs = tuple(1.0 if row == column else 0.0 for row in range(n))
        solved = _direct_solve(matrix, rhs, pivot_relative_threshold=pivot_relative_threshold)
        if not solved.ok:
            return None, solved.minimum_relative_pivot, solved.message
        inverse_columns.append(solved.solution)
        if solved.minimum_relative_pivot is not None:
            minimum_relative_pivot = (
                solved.minimum_relative_pivot
                if minimum_relative_pivot is None
                else min(minimum_relative_pivot, solved.minimum_relative_pivot)
            )
    inverse_rows = tuple(
        tuple(inverse_columns[column][row] for column in range(n))
        for row in range(n)
    )
    condition = norm_a * _matrix_inf_norm(inverse_rows)
    if not math.isfinite(condition):
        return None, minimum_relative_pivot, "Condition number is nonfinite"
    return condition, minimum_relative_pivot, ""


def _failure(
    wrench: PrescribedExternalWrench,
    code: LinkageStaticsFailureCode,
    message: str,
    *,
    link_order: tuple[str, ...] = (),
    link_geometry: tuple[LinkGeometryState, ...] = (),
    equilibrium_matrix: Matrix6 | tuple[()] = (),
    rhs: Vector6 | tuple[()] = (),
    characteristic_length_m: float | None = None,
    scaled_equilibrium_matrix: Matrix6 | tuple[()] = (),
    scaled_rhs: Vector6 | tuple[()] = (),
    condition_number_inf: float | None = None,
    minimum_relative_pivot: float | None = None,
) -> LinkageStaticsResult:
    reference = (
        _point3(wrench.reference_point_m)
        if len(wrench.reference_point_m) == 3
        else (math.nan, math.nan, math.nan)
    )
    force = _point3(wrench.force_N) if len(wrench.force_N) == 3 else (math.nan, math.nan, math.nan)
    moment = _point3(wrench.moment_Nm) if len(wrench.moment_Nm) == 3 else (math.nan, math.nan, math.nan)
    return LinkageStaticsResult(
        status=LinkageStaticsStatus.FAILURE,
        frame_id=wrench.frame_id,
        reference_point_m=reference,
        external_force_N=force,
        external_moment_Nm=moment,
        load_case_id=wrench.load_case_id,
        source_id=wrench.source_id,
        link_order=link_order,
        link_geometry=link_geometry,
        equilibrium_matrix=equilibrium_matrix,
        rhs=rhs,
        characteristic_length_m=characteristic_length_m,
        scaled_equilibrium_matrix=scaled_equilibrium_matrix,
        scaled_rhs=scaled_rhs,
        condition_number_inf=condition_number_inf,
        minimum_relative_pivot=minimum_relative_pivot,
        failure_code=code,
        message=message,
    )


def solve_linkage_statics(
    links: Sequence[IdealTwoForceLink],
    external_wrench: PrescribedExternalWrench,
    *,
    config: LinkageStaticsSolverConfig | None = None,
) -> LinkageStaticsResult:
    """Solve the AUTH-SUSP-0010 exactly-six-link rigid-body statics problem."""

    cfg = config or LinkageStaticsSolverConfig()
    link_order = tuple(link.link_id for link in links)

    if len(links) != 6:
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.UNSUPPORTED_TOPOLOGY,
            f"AUTH-SUSP-0010 v0.1 requires exactly six links; received {len(links)}",
            link_order=link_order,
        )
    if len(set(link_order)) != len(link_order):
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.DUPLICATE_LINK_ID,
            "Each linkage-statics link ID must be unique",
            link_order=link_order,
        )

    if not (
        _finite3(external_wrench.reference_point_m)
        and _finite3(external_wrench.force_N)
        and _finite3(external_wrench.moment_Nm)
    ):
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.NONFINITE_INPUT,
            "External wrench/reference point must contain finite three-component vectors",
            link_order=link_order,
        )
    if not external_wrench.frame_id:
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.FRAME_MISMATCH,
            "External wrench requires a nonempty frame ID",
            link_order=link_order,
        )

    reference = _point3(external_wrench.reference_point_m)
    geometry: list[LinkGeometryState] = []
    for link in links:
        if link.frame_id != external_wrench.frame_id or not link.frame_id:
            return _failure(
                external_wrench,
                LinkageStaticsFailureCode.FRAME_MISMATCH,
                f"Link {link.link_id!r} frame does not match external-wrench frame",
                link_order=link_order,
                link_geometry=tuple(geometry),
            )
        if not (_finite3(link.body_point_m) and _finite3(link.remote_point_m)):
            return _failure(
                external_wrench,
                LinkageStaticsFailureCode.NONFINITE_INPUT,
                f"Link {link.link_id!r} contains nonfinite endpoint geometry",
                link_order=link_order,
                link_geometry=tuple(geometry),
            )
        body = _point3(link.body_point_m)
        remote = _point3(link.remote_point_m)
        axis_vector = _sub(remote, body)
        length = _norm(axis_vector)
        if not math.isfinite(length) or length <= cfg.degenerate_link_tolerance_m:
            return _failure(
                external_wrench,
                LinkageStaticsFailureCode.DEGENERATE_LINK,
                f"Link {link.link_id!r} has coincident/near-coincident endpoints",
                link_order=link_order,
                link_geometry=tuple(geometry),
            )
        unit = _scale(1.0 / length, axis_vector)
        geometry.append(
            LinkGeometryState(
                link_id=link.link_id,
                frame_id=link.frame_id,
                body_point_m=body,
                remote_point_m=remote,
                length_m=length,
                unit_axis_body_to_remote=unit,
                source_id=link.source_id,
                configuration_id=link.configuration_id,
            )
        )

    moment_arms = tuple(_sub(state.body_point_m, reference) for state in geometry)
    characteristic_length = max(_norm(arm) for arm in moment_arms)
    if not math.isfinite(characteristic_length) or characteristic_length <= cfg.characteristic_length_tolerance_m:
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.DEGENERATE_CHARACTERISTIC_LENGTH,
            "Characteristic moment-arm length is unavailable/near zero",
            link_order=link_order,
            link_geometry=tuple(geometry),
            characteristic_length_m=characteristic_length,
        )

    columns: list[Vector6] = []
    for arm, state in zip(moment_arms, geometry):
        moment = _cross(arm, state.unit_axis_body_to_remote)
        columns.append(
            (
                state.unit_axis_body_to_remote[0],
                state.unit_axis_body_to_remote[1],
                state.unit_axis_body_to_remote[2],
                moment[0],
                moment[1],
                moment[2],
            )
        )
    matrix: Matrix6 = tuple(
        tuple(columns[column][row] for column in range(6)) for row in range(6)
    )  # type: ignore[assignment]
    force = _point3(external_wrench.force_N)
    external_moment = _point3(external_wrench.moment_Nm)
    rhs: Vector6 = (
        -force[0],
        -force[1],
        -force[2],
        -external_moment[0],
        -external_moment[1],
        -external_moment[2],
    )

    inv_length = 1.0 / characteristic_length
    row_scales = (1.0, 1.0, 1.0, inv_length, inv_length, inv_length)
    scaled_matrix: Matrix6 = tuple(
        tuple(row_scales[row] * matrix[row][column] for column in range(6))
        for row in range(6)
    )  # type: ignore[assignment]
    scaled_rhs: Vector6 = tuple(row_scales[row] * rhs[row] for row in range(6))  # type: ignore[assignment]

    condition, inverse_pivot, condition_message = _condition_number_inf(
        scaled_matrix,
        pivot_relative_threshold=cfg.pivot_relative_threshold,
    )
    if condition is None:
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.SINGULAR_EQUILIBRIUM,
            condition_message or "Scaled equilibrium matrix is singular",
            link_order=link_order,
            link_geometry=tuple(geometry),
            equilibrium_matrix=matrix,
            rhs=rhs,
            characteristic_length_m=characteristic_length,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            minimum_relative_pivot=inverse_pivot,
        )
    if condition > cfg.condition_limit:
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM,
            f"Scaled equilibrium condition number {condition:.6g} exceeds {cfg.condition_limit:.6g}",
            link_order=link_order,
            link_geometry=tuple(geometry),
            equilibrium_matrix=matrix,
            rhs=rhs,
            characteristic_length_m=characteristic_length,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            condition_number_inf=condition,
            minimum_relative_pivot=inverse_pivot,
        )

    solved = _direct_solve(
        scaled_matrix,
        scaled_rhs,
        pivot_relative_threshold=cfg.pivot_relative_threshold,
    )
    if not solved.ok:
        return _failure(
            external_wrench,
            LinkageStaticsFailureCode.LINEAR_SOLVE_FAILURE,
            solved.message or "Scaled equilibrium direct solve failed",
            link_order=link_order,
            link_geometry=tuple(geometry),
            equilibrium_matrix=matrix,
            rhs=rhs,
            characteristic_length_m=characteristic_length,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            condition_number_inf=condition,
            minimum_relative_pivot=solved.minimum_relative_pivot,
        )

    force_states: list[LinkForceState] = []
    total_force: Point3 = (0.0, 0.0, 0.0)
    total_moment: Point3 = (0.0, 0.0, 0.0)
    for state, arm, axial in zip(geometry, moment_arms, solved.solution):
        body_force = _scale(axial, state.unit_axis_body_to_remote)
        remote_force = _scale(-1.0, body_force)
        total_force = _add(total_force, body_force)
        total_moment = _add(total_moment, _cross(arm, body_force))
        force_states.append(
            LinkForceState(
                link_id=state.link_id,
                axial_force_N=axial,
                body_force_N=body_force,
                remote_force_N=remote_force,
            )
        )

    force_residual = _add(force, total_force)
    moment_residual = _add(external_moment, total_moment)
    force_norm = _inf_norm3(force_residual)
    moment_norm = _inf_norm3(moment_residual)
    minimum_pivot = solved.minimum_relative_pivot
    if inverse_pivot is not None:
        minimum_pivot = inverse_pivot if minimum_pivot is None else min(minimum_pivot, inverse_pivot)

    if force_norm > cfg.force_residual_tolerance_N or moment_norm > cfg.moment_residual_tolerance_Nm:
        failed = _failure(
            external_wrench,
            LinkageStaticsFailureCode.EQUILIBRIUM_RESIDUAL_EXCEEDED,
            (
                f"Physical equilibrium residual exceeds tolerance: "
                f"force={force_norm:.6g} N, moment={moment_norm:.6g} N*m"
            ),
            link_order=link_order,
            link_geometry=tuple(geometry),
            equilibrium_matrix=matrix,
            rhs=rhs,
            characteristic_length_m=characteristic_length,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            condition_number_inf=condition,
            minimum_relative_pivot=minimum_pivot,
        )
        return replace(
            failed,
            link_forces=tuple(force_states),
            reconstructed_link_force_N=total_force,
            reconstructed_link_moment_Nm=total_moment,
            force_residual_N=force_residual,
            moment_residual_Nm=moment_residual,
            force_residual_inf_norm_N=force_norm,
            moment_residual_inf_norm_Nm=moment_norm,
        )

    return LinkageStaticsResult(
        status=LinkageStaticsStatus.SUCCESS,
        frame_id=external_wrench.frame_id,
        reference_point_m=reference,
        external_force_N=force,
        external_moment_Nm=external_moment,
        load_case_id=external_wrench.load_case_id,
        source_id=external_wrench.source_id,
        link_order=link_order,
        link_geometry=tuple(geometry),
        link_forces=tuple(force_states),
        equilibrium_matrix=matrix,
        rhs=rhs,
        characteristic_length_m=characteristic_length,
        scaled_equilibrium_matrix=scaled_matrix,
        scaled_rhs=scaled_rhs,
        condition_number_inf=condition,
        minimum_relative_pivot=minimum_pivot,
        reconstructed_link_force_N=total_force,
        reconstructed_link_moment_Nm=total_moment,
        force_residual_N=force_residual,
        moment_residual_Nm=moment_residual,
        force_residual_inf_norm_N=force_norm,
        moment_residual_inf_norm_Nm=moment_norm,
    )
