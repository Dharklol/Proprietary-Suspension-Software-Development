"""WUFR27 Level-1 three-body suspension interface statics.

Authorized by ``AUTH-SUSP-0012``.  The v0.1 graph solves exactly three rigid
bodies (outboard carrier/upright, UCA, LCA) and exactly eighteen reaction
unknowns.  It preserves the reviewed arm-mounted actuation topology and returns
only Level-1 interface resultants.

This module deliberately does not generate tire/maneuver/brake/drive loads,
resolve rocker/spring/ARB structural reactions, split an equivalent A-arm hinge
reaction between fore/aft chassis joints, or calculate member stress.
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
        values = tuple(float(value) for value in self.__dict__.values())
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
    "upper_hinge_force_x_N", "upper_hinge_force_y_N", "upper_hinge_force_z_N",
    "upper_hinge_moment_v1_Nm", "upper_hinge_moment_v2_Nm",
    "lower_hinge_force_x_N", "lower_hinge_force_y_N", "lower_hinge_force_z_N",
    "lower_hinge_moment_v1_Nm", "lower_hinge_moment_v2_Nm",
    "upper_spherical_force_on_carrier_x_N", "upper_spherical_force_on_carrier_y_N",
    "upper_spherical_force_on_carrier_z_N", "lower_spherical_force_on_carrier_x_N",
    "lower_spherical_force_on_carrier_y_N", "lower_spherical_force_on_carrier_z_N",
    "lateral_link_axial_force_N", "actuation_rod_axial_force_N",
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


def _scale(scalar: float, vector: Point3) -> Point3:
    return (scalar * vector[0], scalar * vector[1], scalar * vector[2])


def _dot(a: Point3, b: Point3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(vector: Point3) -> float:
    return math.sqrt(_dot(vector, vector))


def _unit(vector: Point3, tolerance: float) -> Point3 | None:
    magnitude = _norm(vector)
    if not math.isfinite(magnitude) or magnitude <= tolerance:
        return None
    return _scale(1.0 / magnitude, vector)


def _least_aligned_hinge_basis(axis: Point3, tolerance: float) -> tuple[Point3, Point3] | None:
    unit = _unit(axis, tolerance)
    if unit is None:
        return None
    seeds: tuple[Point3, ...] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    seed = min(seeds, key=lambda candidate: abs(_dot(candidate, unit)))
    v1 = _unit(_sub(seed, _scale(_dot(seed, unit), unit)), tolerance)
    if v1 is None:
        return None
    v2 = _unit(_cross(unit, v1), tolerance)
    return None if v2 is None else (v1, v2)


def _force_wrench(point: Point3, reference: Point3, force: Point3) -> tuple[float, ...]:
    return (*force, *_cross(_sub(point, reference), force))


def _moment_wrench(moment: Point3) -> tuple[float, ...]:
    return (0.0, 0.0, 0.0, *moment)


def _matrix_inf_norm(matrix: Sequence[Sequence[float]]) -> float:
    return max(sum(abs(float(value)) for value in row) for row in matrix)


def _direct_solve(matrix: Sequence[Sequence[float]], rhs: Sequence[float], threshold: float) -> _DirectSolve:
    n = len(rhs)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return _DirectSolve(False, message="Linear system must be finite and square")
    if any(not math.isfinite(float(value)) for value in rhs) or any(
        any(not math.isfinite(float(value)) for value in row) for row in matrix
    ):
        return _DirectSolve(False, message="Linear system contains nonfinite values")
    scale = _matrix_inf_norm(matrix)
    if not math.isfinite(scale) or scale <= 0.0:
        return _DirectSolve(False, minimum_relative_pivot=0.0, message="Linear system has zero norm")
    a = [[float(value) for value in row] for row in matrix]
    b = [float(value) for value in rhs]
    relative_pivots: list[float] = []
    for column in range(n):
        pivot_row = max(range(column, n), key=lambda row: abs(a[row][column]))
        relative_pivot = abs(a[pivot_row][column]) / scale
        if relative_pivot <= threshold:
            return _DirectSolve(False, minimum_relative_pivot=min(relative_pivots + [relative_pivot]), message=f"Singular/near-singular pivot at column {column}")
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
        relative_pivot = abs(a[row][row]) / scale
        if relative_pivot <= threshold:
            return _DirectSolve(False, minimum_relative_pivot=min(relative_pivots + [relative_pivot]), message=f"Singular/near-singular back-substitution pivot at row {row}")
        x[row] = (b[row] - sum(a[row][j] * x[j] for j in range(row + 1, n))) / a[row][row]
    if not all(math.isfinite(value) for value in x):
        return _DirectSolve(False, minimum_relative_pivot=min(relative_pivots), message="Linear solution is nonfinite")
    return _DirectSolve(True, tuple(x), min(relative_pivots))


def _condition_number_inf(matrix: Sequence[Sequence[float]], threshold: float) -> tuple[float | None, float | None, str]:
    norm_a = _matrix_inf_norm(matrix)
    n = len(matrix)
    inverse_columns: list[tuple[float, ...]] = []
    minimum_pivot: float | None = None
    for column in range(n):
        unit_rhs = tuple(1.0 if row == column else 0.0 for row in range(n))
        solved = _direct_solve(matrix, unit_rhs, threshold)
        if not solved.ok:
            return None, solved.minimum_relative_pivot, solved.message
        inverse_columns.append(solved.solution)
        if solved.minimum_relative_pivot is not None:
            minimum_pivot = solved.minimum_relative_pivot if minimum_pivot is None else min(minimum_pivot, solved.minimum_relative_pivot)
    inverse_rows = tuple(tuple(inverse_columns[column][row] for column in range(n)) for row in range(n))
    condition = norm_a * _matrix_inf_norm(inverse_rows)
    return (condition, minimum_pivot, "") if math.isfinite(condition) else (None, minimum_pivot, "Condition number is nonfinite")


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


def _translated_wrench(wrench: CompleteCarrierWrench, target_reference: Point3) -> tuple[Point3, Point3]:
    force = _p(wrench.force_N)
    moment = _add(_p(wrench.moment_Nm), _cross(_sub(_p(wrench.reference_point_m), target_reference), force))
    return force, moment


def _append_column(matrix: list[list[float]], row_start: int, column: int, values: Sequence[float], sign: float = 1.0) -> None:
    for local_row, value in enumerate(values):
        matrix[row_start + local_row][column] += sign * float(value)


def _residual(
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
    return BodyResidual(body_id, force, moment, max(abs(v) for v in force), max(abs(v) for v in moment))


def solve_wufr_level1_interface_statics(
    geometry: Level1CornerGeometry,
    external_wrench: CompleteCarrierWrench,
    *,
    config: InterfaceStaticsSolverConfig | None = None,
) -> WufrInterfaceStaticsResult:
    """Solve the exact AUTH-SUSP-0012 Level-1 WUFR interface problem."""
    cfg = config or InterfaceStaticsSolverConfig()
    if geometry.axle not in ("front", "rear") or geometry.side not in ("left", "right"):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.UNSUPPORTED_TOPOLOGY, "Axle/side identity is unsupported")
    expected_owner = "upper_a_arm" if geometry.axle == "front" else "lower_a_arm"
    if geometry.actuation_owner != expected_owner:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.SOURCE_OWNERSHIP_MISMATCH, f"{geometry.axle} actuation must remain on {expected_owner}")
    if not geometry.frame_id or external_wrench.frame_id != geometry.frame_id:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.FRAME_MISMATCH, "Geometry and external wrench must use one nonempty frame")
    if not all((geometry.configuration_id, geometry.geometry_source_id, geometry.lateral_source_id, geometry.actuation_source_id)):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.SOURCE_MISMATCH, "Geometry/configuration/interface source identities are required")
    if not external_wrench.complete or not external_wrench.source_id or not external_wrench.load_case_id:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.INCOMPLETE_EXTERNAL_WRENCH, "A complete external carrier wrench with provenance is required")

    vector_fields = (
        geometry.carrier_reference_m, geometry.upper_arm_reference_m, geometry.lower_arm_reference_m,
        geometry.upper_hinge_point_m, geometry.upper_hinge_axis_unit, geometry.lower_hinge_point_m,
        geometry.lower_hinge_axis_unit, geometry.upper_spherical_point_m, geometry.lower_spherical_point_m,
        geometry.lateral_body_point_m, geometry.lateral_remote_point_m, geometry.actuation_body_point_m,
        geometry.actuation_remote_point_m, external_wrench.reference_point_m, external_wrench.force_N,
        external_wrench.moment_Nm,
    )
    if not all(_finite3(values) for values in vector_fields):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.NONFINITE_INPUT, "All geometry/wrench vectors must be finite three-component values")

    upper_axis = _unit(_p(geometry.upper_hinge_axis_unit), cfg.degenerate_axis_tolerance)
    lower_axis = _unit(_p(geometry.lower_hinge_axis_unit), cfg.degenerate_axis_tolerance)
    if upper_axis is None or lower_axis is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_HINGE_AXIS, "A-arm hinge axis is degenerate")
    upper_basis = _least_aligned_hinge_basis(upper_axis, cfg.degenerate_axis_tolerance)
    lower_basis = _least_aligned_hinge_basis(lower_axis, cfg.degenerate_axis_tolerance)
    if upper_basis is None or lower_basis is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_HINGE_AXIS, "Unable to construct hinge moment basis")
    upper_v1, upper_v2 = upper_basis
    lower_v1, lower_v2 = lower_basis

    lateral_axis = _unit(_sub(_p(geometry.lateral_remote_point_m), _p(geometry.lateral_body_point_m)), cfg.degenerate_link_tolerance_m)
    actuation_axis = _unit(_sub(_p(geometry.actuation_remote_point_m), _p(geometry.actuation_body_point_m)), cfg.degenerate_link_tolerance_m)
    if lateral_axis is None or actuation_axis is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_AXIAL_LINK, "Lateral/actuation element is degenerate")

    carrier_ref = _p(geometry.carrier_reference_m)
    upper_ref = _p(geometry.upper_arm_reference_m)
    lower_ref = _p(geometry.lower_arm_reference_m)
    upper_hinge = _p(geometry.upper_hinge_point_m)
    lower_hinge = _p(geometry.lower_hinge_point_m)
    upper_joint = _p(geometry.upper_spherical_point_m)
    lower_joint = _p(geometry.lower_spherical_point_m)
    lateral_point = _p(geometry.lateral_body_point_m)
    actuation_point = _p(geometry.actuation_body_point_m)

    matrix = [[0.0] * 18 for _ in range(18)]
    xyz: tuple[Point3, ...] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    for index, axis in enumerate(xyz):
        _append_column(matrix, 6, index, _force_wrench(upper_hinge, upper_ref, axis))
        _append_column(matrix, 12, 5 + index, _force_wrench(lower_hinge, lower_ref, axis))
        _append_column(matrix, 0, 10 + index, _force_wrench(upper_joint, carrier_ref, axis))
        _append_column(matrix, 6, 10 + index, _force_wrench(upper_joint, upper_ref, axis), -1.0)
        _append_column(matrix, 0, 13 + index, _force_wrench(lower_joint, carrier_ref, axis))
        _append_column(matrix, 12, 13 + index, _force_wrench(lower_joint, lower_ref, axis), -1.0)
    _append_column(matrix, 6, 3, _moment_wrench(upper_v1))
    _append_column(matrix, 6, 4, _moment_wrench(upper_v2))
    _append_column(matrix, 12, 8, _moment_wrench(lower_v1))
    _append_column(matrix, 12, 9, _moment_wrench(lower_v2))
    _append_column(matrix, 0, 16, _force_wrench(lateral_point, carrier_ref, lateral_axis))
    _append_column(matrix, 6 if geometry.axle == "front" else 12, 17, _force_wrench(actuation_point, upper_ref if geometry.axle == "front" else lower_ref, actuation_axis))

    carrier_force, carrier_moment = _translated_wrench(external_wrench, carrier_ref)
    # Exactly 18 rows: six prescribed carrier-wrench rows plus twelve zero UCA/LCA rows.
    rhs: Vector = tuple(-value for value in (*carrier_force, *carrier_moment)) + (0.0,) * 12
    physical_matrix: Matrix = tuple(tuple(row) for row in matrix)

    carrier_length = max(_norm(_sub(point, carrier_ref)) for point in (upper_joint, lower_joint, lateral_point))
    upper_points = [upper_hinge, upper_joint] + ([actuation_point] if geometry.axle == "front" else [])
    lower_points = [lower_hinge, lower_joint] + ([actuation_point] if geometry.axle == "rear" else [])
    upper_length = max(_norm(_sub(point, upper_ref)) for point in upper_points)
    lower_length = max(_norm(_sub(point, lower_ref)) for point in lower_points)
    lengths = (carrier_length, upper_length, lower_length)
    if any(not math.isfinite(value) or value <= cfg.characteristic_length_tolerance_m for value in lengths):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.DEGENERATE_CHARACTERISTIC_LENGTH, "Solved body has degenerate characteristic length", equilibrium_matrix=physical_matrix, rhs=rhs, characteristic_lengths_m=lengths)

    scaled = [list(row) for row in physical_matrix]
    scaled_rhs = list(rhs)
    for body_index, length in enumerate(lengths):
        for row in range(body_index * 6 + 3, body_index * 6 + 6):
            scaled[row] = [value / length for value in scaled[row]]
            scaled_rhs[row] /= length
    scaled_matrix: Matrix = tuple(tuple(row) for row in scaled)
    scaled_rhs_tuple: Vector = tuple(scaled_rhs)

    condition, condition_pivot, message = _condition_number_inf(scaled_matrix, cfg.pivot_relative_threshold)
    if condition is None:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.SINGULAR_EQUILIBRIUM, message or "Scaled equilibrium matrix is singular", equilibrium_matrix=physical_matrix, rhs=rhs, scaled_equilibrium_matrix=scaled_matrix, scaled_rhs=scaled_rhs_tuple, characteristic_lengths_m=lengths, minimum_relative_pivot=condition_pivot)
    if condition > cfg.condition_limit:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM, f"Scaled cond_inf={condition:.6g} exceeds limit {cfg.condition_limit:.6g}", equilibrium_matrix=physical_matrix, rhs=rhs, scaled_equilibrium_matrix=scaled_matrix, scaled_rhs=scaled_rhs_tuple, characteristic_lengths_m=lengths, condition_number_inf=condition, minimum_relative_pivot=condition_pivot)

    solved = _direct_solve(scaled_matrix, scaled_rhs_tuple, cfg.pivot_relative_threshold)
    if not solved.ok or len(solved.solution) != 18:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.LINEAR_SOLVE_FAILURE, solved.message or "Direct Level-1 solve failed", equilibrium_matrix=physical_matrix, rhs=rhs, scaled_equilibrium_matrix=scaled_matrix, scaled_rhs=scaled_rhs_tuple, characteristic_lengths_m=lengths, condition_number_inf=condition, minimum_relative_pivot=solved.minimum_relative_pivot)
    x = solved.solution

    upper_hinge_force = (x[0], x[1], x[2])
    lower_hinge_force = (x[5], x[6], x[7])
    upper_hinge_moment = _add(_scale(x[3], upper_v1), _scale(x[4], upper_v2))
    lower_hinge_moment = _add(_scale(x[8], lower_v1), _scale(x[9], lower_v2))
    upper_joint_force = (x[10], x[11], x[12])
    lower_joint_force = (x[13], x[14], x[15])
    lateral_force = _scale(x[16], lateral_axis)
    actuation_force = _scale(x[17], actuation_axis)

    upper_hinge_result = HingeReaction("upper_a_arm", upper_hinge, upper_axis, upper_hinge_force, upper_hinge_moment, _dot(upper_hinge_moment, upper_axis), upper_v1, upper_v2, x[3], x[4])
    lower_hinge_result = HingeReaction("lower_a_arm", lower_hinge, lower_axis, lower_hinge_force, lower_hinge_moment, _dot(lower_hinge_moment, lower_axis), lower_v1, lower_v2, x[8], x[9])
    upper_spherical = SphericalReaction("upper_arm_to_carrier", upper_joint, upper_joint_force, _scale(-1.0, upper_joint_force))
    lower_spherical = SphericalReaction("lower_arm_to_carrier", lower_joint, lower_joint_force, _scale(-1.0, lower_joint_force))
    lateral = AxialReaction("front_tie_rod" if geometry.axle == "front" else "rear_toe_link", "outboard_carrier", lateral_point, _p(geometry.lateral_remote_point_m), lateral_axis, x[16], lateral_force, _scale(-1.0, lateral_force), geometry.lateral_source_id)
    actuation = AxialReaction("front_pullrod" if geometry.axle == "front" else "rear_pushrod", expected_owner, actuation_point, _p(geometry.actuation_remote_point_m), actuation_axis, x[17], actuation_force, _scale(-1.0, actuation_force), geometry.actuation_source_id)

    carrier_residual = _residual("outboard_carrier", carrier_ref, carrier_force, carrier_moment, ((upper_joint, upper_joint_force), (lower_joint, lower_joint_force), (lateral_point, lateral_force)), ())
    upper_forces: list[tuple[Point3, Point3]] = [(upper_hinge, upper_hinge_force), (upper_joint, _scale(-1.0, upper_joint_force))]
    lower_forces: list[tuple[Point3, Point3]] = [(lower_hinge, lower_hinge_force), (lower_joint, _scale(-1.0, lower_joint_force))]
    (upper_forces if geometry.axle == "front" else lower_forces).append((actuation_point, actuation_force))
    upper_residual = _residual("upper_a_arm", upper_ref, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), upper_forces, (upper_hinge_moment,))
    lower_residual = _residual("lower_a_arm", lower_ref, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), lower_forces, (lower_hinge_moment,))
    residuals = (carrier_residual, upper_residual, lower_residual)

    if max(abs(upper_hinge_result.moment_axis_component_Nm), abs(lower_hinge_result.moment_axis_component_Nm)) > cfg.hinge_axis_moment_tolerance_Nm:
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.HINGE_AXIS_MOMENT_VIOLATION, "Equivalent revolute reaction contains prohibited hinge-axis moment", equilibrium_matrix=physical_matrix, rhs=rhs, scaled_equilibrium_matrix=scaled_matrix, scaled_rhs=scaled_rhs_tuple, characteristic_lengths_m=lengths, condition_number_inf=condition, minimum_relative_pivot=solved.minimum_relative_pivot)
    if any(row.force_inf_norm_N > cfg.force_residual_tolerance_N or row.moment_inf_norm_Nm > cfg.moment_residual_tolerance_Nm for row in residuals):
        return _failure(geometry, external_wrench, WufrInterfaceStaticsFailureCode.EQUILIBRIUM_RESIDUAL_EXCEEDED, "Physical per-body equilibrium residual exceeds tolerance", equilibrium_matrix=physical_matrix, rhs=rhs, scaled_equilibrium_matrix=scaled_matrix, scaled_rhs=scaled_rhs_tuple, characteristic_lengths_m=lengths, condition_number_inf=condition, minimum_relative_pivot=solved.minimum_relative_pivot)

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
        scaled_rhs=scaled_rhs_tuple,
        characteristic_lengths_m=lengths,
        condition_number_inf=condition,
        minimum_relative_pivot=solved.minimum_relative_pivot,
        upper_hinge=upper_hinge_result,
        lower_hinge=lower_hinge_result,
        upper_spherical=upper_spherical,
        lower_spherical=lower_spherical,
        lateral=lateral,
        actuation=actuation,
        body_residuals=residuals,
        translated_carrier_force_N=carrier_force,
        translated_carrier_moment_Nm=carrier_moment,
    )
