"""WUFR27 Level-1 three-body suspension interface statics.

Authorized by ``AUTH-SUSP-0012``.  The v0.1 graph solves exactly three rigid
bodies (outboard carrier/upright, UCA, LCA) and exactly eighteen reaction
unknowns.  It preserves the reviewed arm-mounted actuation topology and returns
only Level-1 interface resultants.

This module deliberately does *not* generate tire/maneuver/brake/drive loads,
resolve rocker/spring/ARB structural reactions, split the equivalent A-arm hinge
reaction between forward/aft chassis joints, or calculate member stress.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence


Point3 = tuple[float, float, float]
Vector = tuple[float, ...]
Matrix = tuple[Vector, ...]


class WufrInterfaceStaticsStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WufrInterfaceStaticsFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    FRAME_MISMATCH = "frame_mismatch"
    SOURCE_MISMATCH = "source_mismatch"
    DUPLICATE_OR_MISSING_IDENTITY = "duplicate_or_missing_identity"
    DEGENERATE_HINGE_AXIS = "degenerate_hinge_axis"
    DEGENERATE_AXIAL_LINK = "degenerate_axial_link"
    UNSUPPORTED_TOPOLOGY = "unsupported_topology"
    SOURCE_OWNERSHIP_MISMATCH = "source_ownership_mismatch"
    INCOMPLETE_EXTERNAL_WRENCH = "incomplete_external_wrench"
    DEGENERATE_CHARACTERISTIC_LENGTH = "degenerate_characteristic_length"
    SINGULAR_EQUILIBRIUM = "singular_equilibrium"
    ILL_CONDITIONED_EQUILIBRIUM = "ill_conditioned_equilibrium"
    LINEAR_SOLVE_FAILURE = "linear_solve_failure"
    HINGE_AXIS_MOMENT_VIOLATION = "hinge_axis_moment_violation"
    EQUILIBRIUM_RESIDUAL_EXCEEDED = "equilibrium_residual_exceeded"


@dataclass(frozen=True)
class Level1CornerGeometry:
    """Explicit current geometry for the AUTH-SUSP-0012 three-body graph."""

    axle: str
    side: str
    frame_id: str
    configuration_id: str
    geometry_source_id: str
    carrier_reference_m: Point3
    upper_arm_reference_m: Point3
    lower_arm_reference_m: Point3
    upper_hinge_point_m: Point3
    upper_hinge_axis_unit: Point3
    lower_hinge_point_m: Point3
    lower_hinge_axis_unit: Point3
    upper_spherical_point_m: Point3
    lower_spherical_point_m: Point3
    lateral_body_point_m: Point3
    lateral_remote_point_m: Point3
    lateral_source_id: str
    actuation_body_point_m: Point3
    actuation_remote_point_m: Point3
    actuation_owner: str
    actuation_source_id: str


@dataclass(frozen=True)
class CompleteCarrierWrench:
    frame_id: str
    reference_point_m: Point3
    force_N: Point3
    moment_Nm: Point3
    source_id: str
    load_case_id: str
    complete: bool = True


@dataclass(frozen=True)
class InterfaceStaticsSolverConfig:
    condition_limit: float = 1.0e10
    pivot_relative_threshold: float = 1.0e-12
    degenerate_axis_tolerance: float = 1.0e-12
    degenerate_link_tolerance_m: float = 1.0e-12
    characteristic_length_tolerance_m: float = 1.0e-12
    force_residual_tolerance_N: float = 1.0e-9
    moment_residual_tolerance_Nm: float = 1.0e-9
    hinge_axis_moment_tolerance_Nm: float = 1.0e-9

    def __post_init__(self) -> None:
        values = (
            self.condition_limit,
            self.pivot_relative_threshold,
            self.degenerate_axis_tolerance,
            self.degenerate_link_tolerance_m,
            self.characteristic_length_tolerance_m,
            self.force_residual_tolerance_N,
            self.moment_residual_tolerance_Nm,
            self.hinge_axis_moment_tolerance_Nm,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("All Level-1 statics solver limits must be finite and positive")


@dataclass(frozen=True)
class HingeReaction:
    body_id: str
    point_m: Point3
    axis_unit: Point3
    force_N: Point3
    moment_Nm: Point3
    moment_axis_component_Nm: float
    basis_v1: Point3
    basis_v2: Point3
    scalar_moment_v1_Nm: float
    scalar_moment_v2_Nm: float


@dataclass(frozen=True)
class SphericalReaction:
    interface_id: str
    point_m: Point3
    force_on_carrier_N: Point3
    force_on_arm_N: Point3


@dataclass(frozen=True)
class AxialReaction:
    element_id: str
    body_id: str
    body_point_m: Point3
    remote_point_m: Point3
    unit_axis_body_to_remote: Point3
    axial_force_N: float
    force_on_body_N: Point3
    force_on_remote_N: Point3
    source_id: str


@dataclass(frozen=True)
class BodyResidual:
    body_id: str
    force_residual_N: Point3
    moment_residual_Nm: Point3
    force_inf_norm_N: float
    moment_inf_norm_Nm: float


@dataclass(frozen=True)
class WufrInterfaceStaticsResult:
    status: WufrInterfaceStaticsStatus
    axle: str
    side: str
    frame_id: str
    configuration_id: str
    geometry_source_id: str
    load_case_id: str
    external_wrench_source_id: str
    failure_code: WufrInterfaceStaticsFailureCode | None = None
    message: str = ""
    unknown_order: tuple[str, ...] = ()
    solution: tuple[float, ...] = ()
    equilibrium_matrix: Matrix = ()
    rhs: Vector = ()
    scaled_equilibrium_matrix: Matrix = ()
    scaled_rhs: Vector = ()
    characteristic_lengths_m: tuple[float, float, float] | tuple[()] = ()
    condition_number_inf: float | None = None
    minimum_relative_pivot: float | None = None
    upper_hinge: HingeReaction | None = None
    lower_hinge: HingeReaction | None = None
    upper_spherical: SphericalReaction | None = None
    lower_spherical: SphericalReaction | None = None
    lateral: AxialReaction | None = None
    actuation: AxialReaction | None = None
    body_residuals: tuple[BodyResidual, ...] = ()
    translated_carrier_force_N: Point3 | None = None
    translated_carrier_moment_Nm: Point3 | None = None
    authorization_id: str = "AUTH-SUSP-0012"
    assumption_id: str = "ASM-SUSP-0005"

    @property
    def ok(self) -> bool:
        return self.status is WufrInterfaceStaticsStatus.SUCCESS


@dataclass(frozen=True)
class _DirectSolve:
    ok: bool
    solution: tuple[float, ...] = ()
    minimum_relative_pivot: float | None = None
    message: str = ""


UNKNOWN_ORDER = (
    "upper_hinge_force_x_N",
    "upper_hinge_force_y_N",
    "upper_hinge_force_z_N",
    "upper_hinge_moment_v1_Nm",
    "upper_hinge_moment_v2_Nm",
    "lower_hinge_force_x_N",
    "lower_hinge_force_y_N",
    "lower_hinge_force_z_N",
    "lower_hinge_moment_v1_Nm",
    "lower_hinge_moment_v2_Nm",
    "upper_spherical_force_on_carrier_x_N",
    "upper_spherical_force_on_carrier_y_N",
    "upper_spherical_force_on_carrier_z_N",
    "lower_spherical_force_on_carrier_x_N",
    "lower_spherical_force_on_carrier_y_N",
    "lower_spherical_force_on_carrier_z_N",
    "lateral_link_axial_force_N",
    "actuation_rod_axial_force_N",
)


def _p(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("Expected a three-component Cartesian vector")
    return (float(values[0]), float(values[1]), float(values[2]))


def _finite3(values: Sequence[float]) -> bool:
    return len(values) == 3 and all(math.isfinite(float(value)) for value in values)


def _add(a: Point3, b: Point3) -> Point3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Point3, b: Point3) -> Point3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(s: float, a: Point3) -> Point3:
    return (s * a[0], s * a[1], s * a[2])


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Point3) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Point3, *, tolerance: float) -> Point3 | None:
    magnitude = _norm(a)
    if not math.isfinite(magnitude) or magnitude <= tolerance:
        return None
    return _scale(1.0 / magnitude, a)


def _inf3(a: Point3) -> float:
    return max(abs(value) for value in a)


def _least_aligned_hinge_basis(axis: Point3, *, tolerance: float) -> tuple[Point3, Point3] | None:
    u = _unit(axis, tolerance=tolerance)
    if u is None:
        return None
    seeds: tuple[Point3, ...] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    seed = min(seeds, key=lambda candidate: abs(_dot(candidate, u)))
    projected = _sub(seed, _scale(_dot(seed, u), u))
    v1 = _unit(projected, tolerance=tolerance)
    if v1 is None:
        return None
    v2 = _unit(_cross(u, v1), tolerance=tolerance)
    if v2 is None:
        return None
    return v1, v2


def _force_wrench(point: Point3, reference: Point3, force: Point3) -> tuple[float, ...]:
    return (*force, *_cross(_sub(point, reference), force))


def _moment_wrench(moment: Point3) -> tuple[float, ...]:
    return (0.0, 0.0, 0.0, *moment)


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
        return _DirectSolve(False, message="Linear-system RHS is nonfinite")
    if any(any(not math.isfinite(float(value)) for value in row) for row in matrix):
        return _DirectSolve(False, message="Linear-system matrix is nonfinite")

    scale = _matrix_inf_norm(matrix)
    if not math.isfinite(scale) or scale <= 0.0:
        return _DirectSolve(False, minimum_relative_pivot=0.0, message="Linear-system matrix norm is zero")

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
                message=f"Singular/near-singular pivot at column {column}",
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
                message=f"Singular/near-singular back-substitution pivot at row {row}",
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
    geometry: Level1CornerGeometry,
    wrench: CompleteCarrierWrench,
    code: WufrInterfaceStaticsFailureCode,
    message: str,
    *,
    equilibrium_matrix: Matrix = (),
    rhs: Vector = (),
    scaled_equilibrium_matrix: Matrix = (),
    scaled_rhs: Vector = (),
    characteristic_lengths_m: tuple[float, float, float] | tuple[()] = (),
    condition_number_inf: float | None = None,
    minimum_relative_pivot: float | None = None,
) -> WufrInterfaceStaticsResult:
    return WufrInterfaceStaticsResult(
        status=WufrInterfaceStaticsStatus.FAILURE,
        axle=geometry.axle,
        side=geometry.side,
        frame_id=geometry.frame_id,
        configuration_id=geometry.configuration_id,
        geometry_source_id=geometry.geometry_source_id,
        load_case_id=wrench.load_case_id,
        external_wrench_source_id=wrench.source_id,
        failure_code=code,
        message=message,
        unknown_order=UNKNOWN_ORDER,
        equilibrium_matrix=equilibrium_matrix,
        rhs=rhs,
        scaled_equilibrium_matrix=scaled_equilibrium_matrix,
        scaled_rhs=scaled_rhs,
        characteristic_lengths_m=characteristic_lengths_m,
        condition_number_inf=condition_number_inf,
        minimum_relative_pivot=minimum_relative_pivot,
    )


def _translate_wrench_to_reference(wrench: CompleteCarrierWrench, target_reference: Point3) -> tuple[Point3, Point3]:
    force = _p(wrench.force_N)
    moment = _add(_p(wrench.moment_Nm), _cross(_sub(_p(wrench.reference_point_m), target_reference), force))
    return force, moment


def _body_characteristic_length(reference: Point3, points: Sequence[Point3]) -> float:
    return max(_norm(_sub(point, reference)) for point in points)


def _append_column(matrix: list[list[float]], row_start: int, column: int, wrench_column: Sequence[float], sign: float = 1.0) -> None:
    for local_row, value in enumerate(wrench_column):
        matrix[row_start + local_row][column] += sign * float(value)


def _physical_body_residual(
    body_id: str,
    reference: Point3,
    prescribed_force: Point3,
    prescribed_moment: Point3,
    point_forces: Sequence[tuple[Point3, Point3]],
    pure_moments: Sequence[Point3],
) -> BodyResidual:
    force = prescribed_force
    moment = prescribed_moment
    for point, reaction_force in point_forces:
        force = _add(force, reaction_force)
        moment = _add(moment, _cross(_sub(point, reference), reaction_force))
    for reaction_moment in pure_moments:
        moment = _add(moment, reaction_moment)
    return BodyResidual(
        body_id=body_id,
        force_residual_N=force,
        moment_residual_Nm=moment,
        force_inf_norm_N=_inf3(force),
        moment_inf_norm_Nm=_inf3(moment),
    )


def solve_wufr_level1_interface_statics(
    geometry: Level1CornerGeometry,
    external_wrench: CompleteCarrierWrench,
    *,
    config: InterfaceStaticsSolverConfig | None = None,
) -> WufrInterfaceStaticsResult:
    """Solve the AUTH-SUSP-0012 exact Level-1 WUFR interface problem."""

    cfg = config or InterfaceStaticsSolverConfig()

    if geometry.axle not in ("front", "rear") or geometry.side not in ("left", "right"):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.UNSUPPORTED_TOPOLOGY, "Axle must be front/rear and side must be left/right")
    expected_owner = "upper_a_arm" if geometry.axle == "front" else "lower_a_arm"
    if geometry.actuation_owner != expected_owner:
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.SOURCE_OWNERSHIP_MISMATCH,
            f"{geometry.axle} actuation must remain on {expected_owner}; received {geometry.actuation_owner}",
        )
    if not geometry.frame_id or external_wrench.frame_id != geometry.frame_id:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.FRAME_MISMATCH, "Geometry and external wrench must use one nonempty frame")
    if not geometry.configuration_id or not geometry.geometry_source_id or not geometry.lateral_source_id or not geometry.actuation_source_id:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.SOURCE_MISMATCH, "Geometry/configuration and interface source identities are required")
    if not external_wrench.complete or not external_wrench.source_id or not external_wrench.load_case_id:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.INCOMPLETE_EXTERNAL_WRENCH, "A complete external carrier wrench with source/load-case provenance is required")

    point_fields = (
        geometry.carrier_reference_m,
        geometry.upper_arm_reference_m,
        geometry.lower_arm_reference_m,
        geometry.upper_hinge_point_m,
        geometry.lower_hinge_point_m,
        geometry.upper_spherical_point_m,
        geometry.lower_spherical_point_m,
        geometry.lateral_body_point_m,
        geometry.lateral_remote_point_m,
        geometry.actuation_body_point_m,
        geometry.actuation_remote_point_m,
        external_wrench.reference_point_m,
        external_wrench.force_N,
        external_wrench.moment_Nm,
    )
    if not all(_finite3(point) for point in point_fields):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.NONFINITE_INPUT, "All geometry and wrench vectors must be finite three-component values")

    upper_axis = _unit(_p(geometry.upper_hinge_axis_unit), tolerance=cfg.degenerate_axis_tolerance)
    lower_axis = _unit(_p(geometry.lower_hinge_axis_unit), tolerance=cfg.degenerate_axis_tolerance)
    if upper_axis is None or lower_axis is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_HINGE_AXIS, "A-arm hinge axes must be finite and nondegenerate")
    upper_basis = _least_aligned_hinge_basis(upper_axis, tolerance=cfg.degenerate_axis_tolerance)
    lower_basis = _least_aligned_hinge_basis(lower_axis, tolerance=cfg.degenerate_axis_tolerance)
    if upper_basis is None or lower_basis is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_HINGE_AXIS, "Unable to construct deterministic hinge moment basis")
    upper_v1, upper_v2 = upper_basis
    lower_v1, lower_v2 = lower_basis

    lateral_vector = _sub(_p(geometry.lateral_remote_point_m), _p(geometry.lateral_body_point_m))
    actuation_vector = _sub(_p(geometry.actuation_remote_point_m), _p(geometry.actuation_body_point_m))
    lateral_axis = _unit(lateral_vector, tolerance=cfg.degenerate_link_tolerance_m)
    actuation_axis = _unit(actuation_vector, tolerance=cfg.degenerate_link_tolerance_m)
    if lateral_axis is None or actuation_axis is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_AXIAL_LINK, "Lateral and actuation elements must have finite nonzero endpoint separation")

    carrier_ref = _p(geometry.carrier_reference_m)
    upper_ref = _p(geometry.upper_arm_reference_m)
    lower_ref = _p(geometry.lower_arm_reference_m)
    upper_hinge_point = _p(geometry.upper_hinge_point_m)
    lower_hinge_point = _p(geometry.lower_hinge_point_m)
    upper_joint = _p(geometry.upper_spherical_point_m)
    lower_joint = _p(geometry.lower_spherical_point_m)
    lateral_point = _p(geometry.lateral_body_point_m)
    actuation_point = _p(geometry.actuation_body_point_m)

    matrix = [[0.0 for _ in range(18)] for _ in range(18)]
    basis_xyz: tuple[Point3, ...] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    # UCA net equivalent revolute support: columns 0..4, UCA rows 6..11.
    for index, axis in enumerate(basis_xyz):
        _append_column(matrix, 6, index, _force_wrench(upper_hinge_point, upper_ref, axis))
    _append_column(matrix, 6, 3, _moment_wrench(upper_v1))
    _append_column(matrix, 6, 4, _moment_wrench(upper_v2))

    # LCA net equivalent revolute support: columns 5..9, LCA rows 12..17.
    for index, axis in enumerate(basis_xyz):
        _append_column(matrix, 12, 5 + index, _force_wrench(lower_hinge_point, lower_ref, axis))
    _append_column(matrix, 12, 8, _moment_wrench(lower_v1))
    _append_column(matrix, 12, 9, _moment_wrench(lower_v2))

    # Spherical joint forces are reported as force on carrier and act equal/opposite on arm.
    for index, axis in enumerate(basis_xyz):
        _append_column(matrix, 0, 10 + index, _force_wrench(upper_joint, carrier_ref, axis))
        _append_column(matrix, 6, 10 + index, _force_wrench(upper_joint, upper_ref, axis), sign=-1.0)
        _append_column(matrix, 0, 13 + index, _force_wrench(lower_joint, carrier_ref, axis))
        _append_column(matrix, 12, 13 + index, _force_wrench(lower_joint, lower_ref, axis), sign=-1.0)

    # Lateral link always acts on carrier.
    _append_column(matrix, 0, 16, _force_wrench(lateral_point, carrier_ref, lateral_axis))

    # Actuation stays on its reviewed owning arm.
    if geometry.axle == "front":
        _append_column(matrix, 6, 17, _force_wrench(actuation_point, upper_ref, actuation_axis))
    else:
        _append_column(matrix, 12, 17, _force_wrench(actuation_point, lower_ref, actuation_axis))

    carrier_force, carrier_moment = _translate_wrench_to_reference(external_wrench, carrier_ref)
    rhs = tuple(-value for value in (*carrier_force, *carrier_moment, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    physical_matrix: Matrix = tuple(tuple(row) for row in matrix)

    carrier_length = _body_characteristic_length(carrier_ref, (upper_joint, lower_joint, lateral_point))
    upper_points = [upper_hinge_point, upper_joint]
    lower_points = [lower_hinge_point, lower_joint]
    if geometry.axle == "front":
        upper_points.append(actuation_point)
    else:
        lower_points.append(actuation_point)
    upper_length = _body_characteristic_length(upper_ref, upper_points)
    lower_length = _body_characteristic_length(lower_ref, lower_points)
    characteristic_lengths = (carrier_length, upper_length, lower_length)
    if any(not math.isfinite(length) or length <= cfg.characteristic_length_tolerance_m for length in characteristic_lengths):
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.DEGENERATE_CHARACTERISTIC_LENGTH,
            "Every solved body requires a finite positive characteristic length",
            equilibrium_matrix=physical_matrix,
            rhs=rhs,
            characteristic_lengths_m=characteristic_lengths,
        )

    scaled = [list(row) for row in physical_matrix]
    scaled_rhs_list = list(rhs)
    for body_index, length in enumerate(characteristic_lengths):
        for row in range(body_index * 6 + 3, body_index * 6 + 6):
            scaled[row] = [value / length for value in scaled[row]]
            scaled_rhs_list[row] /= length
    scaled_matrix: Matrix = tuple(tuple(row) for row in scaled)
    scaled_rhs: Vector = tuple(scaled_rhs_list)

    condition, condition_pivot, condition_message = _condition_number_inf(
        scaled_matrix,
        pivot_relative_threshold=cfg.pivot_relative_threshold,
    )
    if condition is None:
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.SINGULAR_EQUILIBRIUM,
            condition_message or "Scaled Level-1 equilibrium matrix is singular",
            equilibrium_matrix=physical_matrix,
            rhs=rhs,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            characteristic_lengths_m=characteristic_lengths,
            minimum_relative_pivot=condition_pivot,
        )
    if condition > cfg.condition_limit:
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM,
            f"Scaled cond_inf={condition:.6g} exceeds limit {cfg.condition_limit:.6g}",
            equilibrium_matrix=physical_matrix,
            rhs=rhs,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            characteristic_lengths_m=characteristic_lengths,
            condition_number_inf=condition,
            minimum_relative_pivot=condition_pivot,
        )

    solved = _direct_solve(
        scaled_matrix,
        scaled_rhs,
        pivot_relative_threshold=cfg.pivot_relative_threshold,
    )
    if not solved.ok or len(solved.solution) != 18:
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.LINEAR_SOLVE_FAILURE,
            solved.message or "Direct Level-1 equilibrium solve failed",
            equilibrium_matrix=physical_matrix,
            rhs=rhs,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            characteristic_lengths_m=characteristic_lengths,
            condition_number_inf=condition,
            minimum_relative_pivot=solved.minimum_relative_pivot,
        )

    x = solved.solution
    upper_hinge_force = (x[0], x[1], x[2])
    upper_hinge_moment = _add(_scale(x[3], upper_v1), _scale(x[4], upper_v2))
    lower_hinge_force = (x[5], x[6], x[7])
    lower_hinge_moment = _add(_scale(x[8], lower_v1), _scale(x[9], lower_v2))
    upper_joint_force = (x[10], x[11], x[12])
    lower_joint_force = (x[13], x[14], x[15])
    lateral_force = _scale(x[16], lateral_axis)
    actuation_force = _scale(x[17], actuation_axis)

    upper_hinge = HingeReaction(
        body_id="upper_a_arm",
        point_m=upper_hinge_point,
        axis_unit=upper_axis,
        force_N=upper_hinge_force,
        moment_Nm=upper_hinge_moment,
        moment_axis_component_Nm=_dot(upper_hinge_moment, upper_axis),
        basis_v1=upper_v1,
        basis_v2=upper_v2,
        scalar_moment_v1_Nm=x[3],
        scalar_moment_v2_Nm=x[4],
    )
    lower_hinge = HingeReaction(
        body_id="lower_a_arm",
        point_m=lower_hinge_point,
        axis_unit=lower_axis,
        force_N=lower_hinge_force,
        moment_Nm=lower_hinge_moment,
        moment_axis_component_Nm=_dot(lower_hinge_moment, lower_axis),
        basis_v1=lower_v1,
        basis_v2=lower_v2,
        scalar_moment_v1_Nm=x[8],
        scalar_moment_v2_Nm=x[9],
    )
    upper_spherical = SphericalReaction(
        interface_id="upper_arm_to_carrier",
        point_m=upper_joint,
        force_on_carrier_N=upper_joint_force,
        force_on_arm_N=_scale(-1.0, upper_joint_force),
    )
    lower_spherical = SphericalReaction(
        interface_id="lower_arm_to_carrier",
        point_m=lower_joint,
        force_on_carrier_N=lower_joint_force,
        force_on_arm_N=_scale(-1.0, lower_joint_force),
    )
    lateral = AxialReaction(
        element_id="front_tie_rod" if geometry.axle == "front" else "rear_toe_link",
        body_id="outboard_carrier",
        body_point_m=lateral_point,
        remote_point_m=_p(geometry.lateral_remote_point_m),
        unit_axis_body_to_remote=lateral_axis,
        axial_force_N=x[16],
        force_on_body_N=lateral_force,
        force_on_remote_N=_scale(-1.0, lateral_force),
        source_id=geometry.lateral_source_id,
    )
    actuation = AxialReaction(
        element_id="front_pullrod" if geometry.axle == "front" else "rear_pushrod",
        body_id=expected_owner,
        body_point_m=actuation_point,
        remote_point_m=_p(geometry.actuation_remote_point_m),
        unit_axis_body_to_remote=actuation_axis,
        axial_force_N=x[17],
        force_on_body_N=actuation_force,
        force_on_remote_N=_scale(-1.0, actuation_force),
        source_id=geometry.actuation_source_id,
    )

    carrier_residual = _physical_body_residual(
        "outboard_carrier",
        carrier_ref,
        carrier_force,
        carrier_moment,
        (
            (upper_joint, upper_joint_force),
            (lower_joint, lower_joint_force),
            (lateral_point, lateral_force),
        ),
        (),
    )
    upper_point_forces: list[tuple[Point3, Point3]] = [
        (upper_hinge_point, upper_hinge_force),
        (upper_joint, _scale(-1.0, upper_joint_force)),
    ]
    lower_point_forces: list[tuple[Point3, Point3]] = [
        (lower_hinge_point, lower_hinge_force),
        (lower_joint, _scale(-1.0, lower_joint_force)),
    ]
    if geometry.axle == "front":
        upper_point_forces.append((actuation_point, actuation_force))
    else:
        lower_point_forces.append((actuation_point, actuation_force))
    upper_residual = _physical_body_residual(
        "upper_a_arm",
        upper_ref,
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        upper_point_forces,
        (upper_hinge_moment,),
    )
    lower_residual = _physical_body_residual(
        "lower_a_arm",
        lower_ref,
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        lower_point_forces,
        (lower_hinge_moment,),
    )
    residuals = (carrier_residual, upper_residual, lower_residual)

    if abs(upper_hinge.moment_axis_component_Nm) > cfg.hinge_axis_moment_tolerance_Nm or abs(lower_hinge.moment_axis_component_Nm) > cfg.hinge_axis_moment_tolerance_Nm:
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.HINGE_AXIS_MOMENT_VIOLATION,
            "Reconstructed equivalent revolute support contains a prohibited hinge-axis reaction moment",
            equilibrium_matrix=physical_matrix,
            rhs=rhs,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            characteristic_lengths_m=characteristic_lengths,
            condition_number_inf=condition,
            minimum_relative_pivot=solved.minimum_relative_pivot,
        )
    if any(
        residual.force_inf_norm_N > cfg.force_residual_tolerance_N
        or residual.moment_inf_norm_Nm > cfg.moment_residual_tolerance_Nm
        for residual in residuals
    ):
        return _failure(
            geometry,
            external_wrench,
            WufrInterfaceStaticsFailureCode.EQUILIBRIUM_RESIDUAL_EXCEEDED,
            "Physical per-body force/moment residual exceeds the AUTH-SUSP-0012 tolerance",
            equilibrium_matrix=physical_matrix,
            rhs=rhs,
            scaled_equilibrium_matrix=scaled_matrix,
            scaled_rhs=scaled_rhs,
            characteristic_lengths_m=characteristic_lengths,
            condition_number_inf=condition,
            minimum_relative_pivot=solved.minimum_relative_pivot,
        )

    return WufrInterfaceStaticsResult(
        status=WufrInterfaceStaticsStatus.SUCCESS,
        axle=geometry.axle,
        side=geometry.side,
        frame_id=geometry.frame_id,
        configuration_id=geometry.configuration_id,
        geometry_source_id=geometry.geometry_source_id,
        load_case_id=external_wrench.load_case_id,
        external_wrench_source_id=external_wrench.source_id,
        unknown_order=UNKNOWN_ORDER,
        solution=x,
        equilibrium_matrix=physical_matrix,
        rhs=rhs,
        scaled_equilibrium_matrix=scaled_matrix,
        scaled_rhs=scaled_rhs,
        characteristic_lengths_m=characteristic_lengths,
        condition_number_inf=condition,
        minimum_relative_pivot=solved.minimum_relative_pivot,
        upper_hinge=upper_hinge,
        lower_hinge=lower_hinge,
        upper_spherical=upper_spherical,
        lower_spherical=lower_spherical,
        lateral=lateral,
        actuation=actuation,
        body_residuals=residuals,
        translated_carrier_force_N=carrier_force,
        translated_carrier_moment_Nm=carrier_moment,
    )
