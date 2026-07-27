"""Physical WUFR Z-bar rocker-to-blade linkage force recovery.

Authorized by ``AUTH-SUSP-0013``.  This module converts the already-reviewed
transverse blade elastic action from ``MOD-SUSP-0005`` into the signed physical
axial force carried by each rod-ended ARB linkage.  It does not solve rocker
balance, wheel/tire load transfer, stress, or installed/as-built loads.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Sequence

from .wufr_zbar import (
    WUFR_BLADE_STIFFNESS_N_PER_M,
    Point3,
    ZBarAxleFixture,
    ZBarForceResult,
    ZBarMechanismResult,
)


class ZBarLinkForceStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class ZBarLinkForceFailureCode(str, Enum):
    UPSTREAM_MECHANISM_FAILURE = "upstream_mechanism_failure"
    UPSTREAM_FORCE_FAILURE = "upstream_force_failure"
    SOURCE_MISMATCH = "source_mismatch"
    NONFINITE_GEOMETRY = "nonfinite_geometry"
    DEGENERATE_LINK = "degenerate_link"
    DEGENERATE_LINK_PROJECTION = "degenerate_link_projection"
    LINK_CLOSURE_RESIDUAL = "link_closure_residual"
    FORCE_PROJECTION_RESIDUAL = "force_projection_residual"
    ROCKER_TORQUE_MISMATCH = "rocker_torque_mismatch"


@dataclass(frozen=True)
class ZBarLinkForceConfig:
    projection_absolute_threshold: float = 1.0e-6
    force_projection_residual_tolerance_N: float = 1.0e-8
    rocker_torque_agreement_tolerance_Nm: float = 1.0e-8
    unit_vector_tolerance: float = 1.0e-12
    link_closure_residual_tolerance_m: float = 1.0e-9
    source_deflection_tolerance_m: float = 1.0e-12
    source_stiffness_tolerance_N_per_m: float = 1.0e-9

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in self.__dict__.values())
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("Z-bar physical-link-force tolerances must be finite and positive")


@dataclass(frozen=True)
class ZBarLinkSideForce:
    side: str
    link_axis_blade_to_rocker: Point3
    blade_transverse_unit: Point3
    projection_u_dot_n: float
    elastic_transverse_force_N: float
    axial_force_N: float
    force_on_rocker_N: Point3
    force_on_blade_N: Point3
    physical_rocker_torque_Nm: float
    expected_generalized_rocker_torque_Nm: float | None
    force_projection_residual_N: float
    rocker_torque_residual_Nm: float | None
    current_link_length_m: float
    nominal_link_length_m: float
    link_closure_residual_m: float


@dataclass(frozen=True)
class ZBarPhysicalLinkForceResult:
    status: ZBarLinkForceStatus
    axle: str
    fixture_id: str
    configuration_id: str
    setting: int | None = None
    stiffness_N_per_m: float | None = None
    left: ZBarLinkSideForce | None = None
    right: ZBarLinkSideForce | None = None
    failure_code: ZBarLinkForceFailureCode | None = None
    message: str = ""
    authorization_id: str = "AUTH-SUSP-0013"
    assumption_id: str = "ASM-SUSP-0006"

    @property
    def ok(self) -> bool:
        return self.status is ZBarLinkForceStatus.SUCCESS


@dataclass(frozen=True)
class SingleLinkForceResult:
    status: ZBarLinkForceStatus
    side_force: ZBarLinkSideForce | None = None
    failure_code: ZBarLinkForceFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is ZBarLinkForceStatus.SUCCESS


def _p(values: Sequence[float]) -> Point3:
    if len(values) != 3:
        raise ValueError("Expected a three-component vector")
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


def _rotate_vector_about_axis(vector: Point3, axis: Point3, angle_rad: float, tolerance: float) -> Point3 | None:
    unit_axis = _unit(axis, tolerance)
    if unit_axis is None or not math.isfinite(angle_rad):
        return None
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return _add(
        _add(_scale(c, vector), _scale(s, _cross(unit_axis, vector))),
        _scale((1.0 - c) * _dot(unit_axis, vector), unit_axis),
    )


def _blade_transverse_direction(
    housing_pivot_m: Point3,
    housing_axis_unit: Point3,
    nominal_blade_tip_m: Point3,
    housing_theta_rad: float,
    *,
    tolerance: float,
) -> Point3 | None:
    arm = _sub(nominal_blade_tip_m, housing_pivot_m)
    arm_hat = _unit(arm, tolerance)
    axis_hat = _unit(housing_axis_unit, tolerance)
    if arm_hat is None or axis_hat is None:
        return None
    transverse_nominal = _unit(_cross(axis_hat, arm_hat), tolerance)
    if transverse_nominal is None:
        return None
    transverse_current = _rotate_vector_about_axis(
        transverse_nominal,
        axis_hat,
        housing_theta_rad,
        tolerance,
    )
    if transverse_current is None:
        return None
    return _unit(transverse_current, tolerance)


def recover_single_link_force(
    *,
    side: str,
    blade_tip_m: Point3,
    rocker_pickup_m: Point3,
    blade_transverse_unit: Point3,
    elastic_transverse_force_N: float,
    rocker_pivot_m: Point3,
    rocker_axis_unit: Point3,
    nominal_link_length_m: float,
    expected_generalized_rocker_torque_Nm: float | None,
    config: ZBarLinkForceConfig | None = None,
) -> SingleLinkForceResult:
    """Recover one signed physical linkage force from exact current geometry.

    The canonical link axis points from blade tip to rocker pickup and positive
    axial force denotes tension.
    """
    cfg = config or ZBarLinkForceConfig()
    vector_inputs = (blade_tip_m, rocker_pickup_m, blade_transverse_unit, rocker_pivot_m, rocker_axis_unit)
    scalar_inputs = (elastic_transverse_force_N, nominal_link_length_m)
    if expected_generalized_rocker_torque_Nm is not None:
        scalar_inputs += (expected_generalized_rocker_torque_Nm,)
    if not all(_finite3(value) for value in vector_inputs) or not all(math.isfinite(float(value)) for value in scalar_inputs):
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.NONFINITE_GEOMETRY,
            message=f"{side} physical-link inputs must be finite",
        )
    if nominal_link_length_m <= cfg.unit_vector_tolerance:
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.DEGENERATE_LINK,
            message=f"{side} nominal link length is degenerate",
        )

    link_vector = _sub(_p(rocker_pickup_m), _p(blade_tip_m))
    current_link_length = _norm(link_vector)
    link_axis = _unit(link_vector, cfg.unit_vector_tolerance)
    transverse = _unit(_p(blade_transverse_unit), cfg.unit_vector_tolerance)
    rocker_axis = _unit(_p(rocker_axis_unit), cfg.unit_vector_tolerance)
    if link_axis is None or transverse is None or rocker_axis is None:
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.DEGENERATE_LINK,
            message=f"{side} link/transverse/rocker axis is degenerate",
        )

    closure_residual = current_link_length - nominal_link_length_m
    if abs(closure_residual) > cfg.link_closure_residual_tolerance_m:
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.LINK_CLOSURE_RESIDUAL,
            message=(
                f"{side} current link length residual {closure_residual:.6g} m exceeds "
                f"{cfg.link_closure_residual_tolerance_m:.6g} m"
            ),
        )

    projection = _dot(link_axis, transverse)
    if not math.isfinite(projection) or abs(projection) <= cfg.projection_absolute_threshold:
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.DEGENERATE_LINK_PROJECTION,
            message=(
                f"{side} |u_link dot n_blade|={abs(projection):.6g} is at/below "
                f"{cfg.projection_absolute_threshold:.6g}"
            ),
        )

    axial_force = float(elastic_transverse_force_N) / projection
    force_on_blade = _scale(axial_force, link_axis)
    force_on_rocker = _scale(-1.0, force_on_blade)
    reconstructed_transverse = axial_force * projection
    force_residual = reconstructed_transverse - float(elastic_transverse_force_N)
    if not all(math.isfinite(value) for value in (*force_on_blade, *force_on_rocker, axial_force, force_residual)):
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.NONFINITE_GEOMETRY,
            message=f"{side} recovered physical linkage force is nonfinite",
        )
    if abs(force_residual) > cfg.force_projection_residual_tolerance_N:
        return SingleLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            failure_code=ZBarLinkForceFailureCode.FORCE_PROJECTION_RESIDUAL,
            message=f"{side} projected-force residual exceeds tolerance",
        )

    lever = _sub(_p(rocker_pickup_m), _p(rocker_pivot_m))
    physical_torque = _dot(rocker_axis, _cross(lever, force_on_rocker))
    torque_residual: float | None = None
    if expected_generalized_rocker_torque_Nm is not None:
        torque_residual = physical_torque - float(expected_generalized_rocker_torque_Nm)
        if abs(torque_residual) > cfg.rocker_torque_agreement_tolerance_Nm:
            return SingleLinkForceResult(
                ZBarLinkForceStatus.FAILURE,
                failure_code=ZBarLinkForceFailureCode.ROCKER_TORQUE_MISMATCH,
                message=(
                    f"{side} physical rocker torque {physical_torque:.12g} N*m differs from "
                    f"AUTH-SUSP-0008 generalized torque {expected_generalized_rocker_torque_Nm:.12g} N*m"
                ),
            )

    return SingleLinkForceResult(
        ZBarLinkForceStatus.SUCCESS,
        side_force=ZBarLinkSideForce(
            side=side,
            link_axis_blade_to_rocker=link_axis,
            blade_transverse_unit=transverse,
            projection_u_dot_n=projection,
            elastic_transverse_force_N=float(elastic_transverse_force_N),
            axial_force_N=axial_force,
            force_on_rocker_N=force_on_rocker,
            force_on_blade_N=force_on_blade,
            physical_rocker_torque_Nm=physical_torque,
            expected_generalized_rocker_torque_Nm=expected_generalized_rocker_torque_Nm,
            force_projection_residual_N=force_residual,
            rocker_torque_residual_Nm=torque_residual,
            current_link_length_m=current_link_length,
            nominal_link_length_m=nominal_link_length_m,
            link_closure_residual_m=closure_residual,
        ),
    )


def recover_wufr_zbar_physical_link_forces(
    fixture: ZBarAxleFixture,
    mechanism: ZBarMechanismResult,
    force: ZBarForceResult,
    *,
    config: ZBarLinkForceConfig | None = None,
) -> ZBarPhysicalLinkForceResult:
    """Recover signed left/right physical ARB linkage forces.

    ``force.force_left_N`` and ``force.force_right_N`` remain the transverse
    elastic-coordinate actions ``k_b*d``.  This function is the authorized
    projection from those actions to physical axial linkage forces.
    """
    cfg = config or ZBarLinkForceConfig()
    base = dict(axle=fixture.axle, fixture_id=fixture.fixture_id, configuration_id=fixture.configuration_id)
    if not mechanism.ok:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            failure_code=ZBarLinkForceFailureCode.UPSTREAM_MECHANISM_FAILURE,
            message=mechanism.message or "Upstream Z-bar mechanism state failed",
        )
    if not force.ok:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.UPSTREAM_FORCE_FAILURE,
            message=force.message or "Upstream Z-bar elastic force state failed",
        )
    if fixture.axle != mechanism.axle:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.SOURCE_MISMATCH,
            message=f"Fixture axle {fixture.axle!r} does not match mechanism axle {mechanism.axle!r}",
        )
    if force.setting < 1 or force.setting > len(WUFR_BLADE_STIFFNESS_N_PER_M):
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.SOURCE_MISMATCH,
            message="Discrete blade setting is outside the reviewed 1..5 source set",
        )
    expected_stiffness = WUFR_BLADE_STIFFNESS_N_PER_M[force.setting - 1]
    if abs(force.stiffness_N_per_m - expected_stiffness) > cfg.source_stiffness_tolerance_N_per_m:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.SOURCE_MISMATCH,
            message="Z-bar force stiffness does not match the reviewed discrete setting",
        )

    required_scalars = (
        mechanism.housing_theta_rad,
        mechanism.d_left_m,
        mechanism.d_right_m,
        force.d_left_m,
        force.d_right_m,
        force.force_left_N,
        force.force_right_N,
    )
    required_points = (
        mechanism.blade_tip_left_m,
        mechanism.blade_tip_right_m,
        mechanism.rocker_pickup_left_m,
        mechanism.rocker_pickup_right_m,
    )
    if any(value is None or not math.isfinite(float(value)) for value in required_scalars) or any(
        value is None or not _finite3(value) for value in required_points
    ):
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.NONFINITE_GEOMETRY,
            message="Successful upstream states are missing finite current mechanism geometry/forces",
        )
    assert mechanism.housing_theta_rad is not None
    assert mechanism.d_left_m is not None and mechanism.d_right_m is not None
    assert force.d_left_m is not None and force.d_right_m is not None
    assert force.force_left_N is not None and force.force_right_N is not None
    assert mechanism.blade_tip_left_m is not None and mechanism.blade_tip_right_m is not None
    assert mechanism.rocker_pickup_left_m is not None and mechanism.rocker_pickup_right_m is not None

    if max(abs(mechanism.d_left_m - force.d_left_m), abs(mechanism.d_right_m - force.d_right_m)) > cfg.source_deflection_tolerance_m:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.SOURCE_MISMATCH,
            message="Mechanism and elastic-force states do not contain the same blade deflections",
        )
    if mechanism.link_residual_left_m is None or mechanism.link_residual_right_m is None or max(
        abs(mechanism.link_residual_left_m), abs(mechanism.link_residual_right_m)
    ) > cfg.link_closure_residual_tolerance_m:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.LINK_CLOSURE_RESIDUAL,
            message="Upstream rigid-link closure residual exceeds the physical-link-force tolerance",
        )

    transverse_left = _blade_transverse_direction(
        fixture.housing_pivot_m,
        fixture.housing_axis_unit,
        fixture.blade_link_joint_left_m,
        mechanism.housing_theta_rad,
        tolerance=cfg.unit_vector_tolerance,
    )
    transverse_right = _blade_transverse_direction(
        fixture.housing_pivot_m,
        fixture.housing_axis_unit,
        fixture.blade_link_joint_right_m,
        mechanism.housing_theta_rad,
        tolerance=cfg.unit_vector_tolerance,
    )
    if transverse_left is None or transverse_right is None:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.NONFINITE_GEOMETRY,
            message="Blade transverse direction is unavailable",
        )

    expected_torque_left: float | None = None
    expected_torque_right: float | None = None
    if len(force.generalized_rocker_torque_Nm) == 2:
        expected_torque_left = float(force.generalized_rocker_torque_Nm[0])
        expected_torque_right = float(force.generalized_rocker_torque_Nm[1])
    elif force.generalized_rocker_torque_Nm:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=ZBarLinkForceFailureCode.SOURCE_MISMATCH,
            message="Generalized rocker torque must be empty or contain exactly left/right values",
        )

    left = recover_single_link_force(
        side="left",
        blade_tip_m=mechanism.blade_tip_left_m,
        rocker_pickup_m=mechanism.rocker_pickup_left_m,
        blade_transverse_unit=transverse_left,
        elastic_transverse_force_N=force.force_left_N,
        rocker_pivot_m=fixture.rocker_pivot_left_m,
        rocker_axis_unit=fixture.rocker_axis_unit,
        nominal_link_length_m=fixture.link_length_left_m,
        expected_generalized_rocker_torque_Nm=expected_torque_left,
        config=cfg,
    )
    if not left.ok:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=left.failure_code,
            message=left.message,
        )
    right = recover_single_link_force(
        side="right",
        blade_tip_m=mechanism.blade_tip_right_m,
        rocker_pickup_m=mechanism.rocker_pickup_right_m,
        blade_transverse_unit=transverse_right,
        elastic_transverse_force_N=force.force_right_N,
        rocker_pivot_m=fixture.rocker_pivot_right_m,
        rocker_axis_unit=fixture.rocker_axis_unit,
        nominal_link_length_m=fixture.link_length_right_m,
        expected_generalized_rocker_torque_Nm=expected_torque_right,
        config=cfg,
    )
    if not right.ok:
        return ZBarPhysicalLinkForceResult(
            ZBarLinkForceStatus.FAILURE,
            **base,
            setting=force.setting,
            stiffness_N_per_m=force.stiffness_N_per_m,
            failure_code=right.failure_code,
            message=right.message,
        )

    return ZBarPhysicalLinkForceResult(
        ZBarLinkForceStatus.SUCCESS,
        **base,
        setting=force.setting,
        stiffness_N_per_m=force.stiffness_N_per_m,
        left=left.side_force,
        right=right.side_force,
    )
