"""Synchronized four-corner WUFR static Level-1 interface-load composition.

Implements ``AUTH-SUSP-0017`` / ``MOD-SUSP-0009``.  The composition pairs the
four exact ``MOD-VEH-0008`` static-gravity carrier wrenches with exact current
``MOD-SUSP-0007`` geometry and invokes the existing Level-1 solver unchanged.
It creates no load and publishes no partial four-corner result.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Callable, Sequence

from pssd_steering import AxisLine, SteeringCorner, solve_corner_position

from .actuation import ActuationStateResult, solve_actuation_q_L_state
from .geometry import Axle, Side
from .wheel_reference import build_nominal_wheel_reference
from .wufr_interface_adapter import (
    CurrentLateralLinkState,
    WufrInterfaceAdapterError,
    build_level1_geometry_from_current_states,
)
from .wufr_interface_statics import (
    CompleteCarrierWrench,
    InterfaceStaticsSolverConfig,
    Level1CornerGeometry,
    WufrInterfaceStaticsResult,
    solve_wufr_level1_interface_statics,
)

from pssd_vehicle.wufr_road_contact import (
    CORNER_ORDER,
    evaluate_corner_point_state,
)
from pssd_vehicle.wufr_static_carrier_wrench import (
    WUFRStaticCarrierCornerResult,
    WUFRStaticCarrierWrenchProvider,
    WUFRStaticCarrierWrenchResult,
    evaluate_wufr_static_carrier_wrenches,
    load_wufr_static_carrier_wrench_provider,
)


Vector3 = tuple[float, float, float]
RESULT_LABEL = "uncorrelated_design_intent_static_level1_interface_loads"
REQUIRED_RECORD_ID = "WUFR27_STATIC_LEVEL1_INTERFACE_LOADS_V0"
REQUIRED_AUTHORIZATION_ID = "AUTH-SUSP-0017"
REQUIRED_MODEL_ID = "MOD-SUSP-0009"
REQUIRED_CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
REQUIRED_STATIC_STATE_ID = "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE"
REQUIRED_CARRIER_AUTHORIZATION_ID = "AUTH-VEH-0011"
REQUIRED_CARRIER_MODEL_ID = "MOD-VEH-0008"
REQUIRED_CARRIER_RESULT_LABEL = "uncorrelated_design_intent_static_carrier_wrench"
REQUIRED_LEVEL1_AUTHORIZATION_ID = "AUTH-SUSP-0012"
REQUIRED_LEVEL1_MODEL_ID = "MOD-SUSP-0007"
LEVEL1_FRAME_ID = "WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL"
GEOMETRY_SOURCE_ID = "WUFR27_LEVEL1_LINKAGE_TOPOLOGY_V0"


class WUFRStaticLevel1Status(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WUFRStaticLevel1FailureCode(str, Enum):
    SOURCE_MISMATCH = "source_mismatch"
    UPSTREAM_CARRIER_RESULT_FAILURE = "upstream_carrier_result_failure"
    CORNER_COUNT_OR_ORDER_MISMATCH = "corner_count_or_order_mismatch"
    STATE_IDENTITY_MISMATCH = "state_identity_mismatch"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    LOAD_CASE_MISMATCH = "load_case_mismatch"
    FRAME_OR_REFERENCE_MISMATCH = "frame_or_reference_mismatch"
    GEOMETRY_SOURCE_MISMATCH = "geometry_source_mismatch"
    FRONT_STEERING_STATE_UNAVAILABLE = "front_steering_state_unavailable"
    CURRENT_GEOMETRY_FAILURE = "current_geometry_failure"
    CORNER_SOLVE_FAILURE = "corner_solve_failure"
    CORNER_RESIDUAL_FAILURE = "corner_residual_failure"
    COLLECTION_INCOMPLETE = "collection_incomplete"
    NONFINITE_OUTPUT = "nonfinite_output"


class WUFRStaticLevel1Error(ValueError):
    def __init__(self, code: WUFRStaticLevel1FailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WUFRStaticLevel1Source:
    record_id: str
    configuration_id: str
    static_state_id: str
    authorization_id: str
    model_id: str
    result_label: str
    corner_order: tuple[str, str, str, str]
    carrier_model_id: str
    carrier_authorization_id: str
    carrier_result_label: str
    carrier_frame_id: str
    level1_model_id: str
    level1_authorization_id: str
    geometry_source_id: str
    complete_for_authorized_static_gravity_case: bool
    complete_physical_vehicle_load_case: bool
    maneuver_complete: bool
    rocker_result_publication_authorized: bool
    installed_as_built_authority: bool
    production_authority: bool


@dataclass(frozen=True)
class WUFRStaticLevel1Config:
    carrier_reference_match_tolerance_m: float = 1.0e-12
    spherical_point_match_tolerance_m: float = 1.0e-12
    state_coordinate_match_tolerance_m: float = 1.0e-12
    solver_config: InterfaceStaticsSolverConfig = InterfaceStaticsSolverConfig()

    def __post_init__(self) -> None:
        values = (
            self.carrier_reference_match_tolerance_m,
            self.spherical_point_match_tolerance_m,
            self.state_coordinate_match_tolerance_m,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise WUFRStaticLevel1Error(
                WUFRStaticLevel1FailureCode.NONFINITE_OUTPUT,
                "Composition tolerances must be finite and positive",
            )


@dataclass(frozen=True)
class WUFRStaticLevel1Provider:
    source: WUFRStaticLevel1Source
    carrier_provider: WUFRStaticCarrierWrenchProvider
    config: WUFRStaticLevel1Config


@dataclass(frozen=True)
class WUFRStaticLevel1CornerResult:
    corner_id: str
    axle: str
    side: str
    wheel_coordinate_m: float
    q_L_rad: float
    geometry: Level1CornerGeometry
    carrier_wrench: CompleteCarrierWrench
    steering_source_id: str | None
    steering_closure_residual_m: float | None
    actuation_state: ActuationStateResult
    solve: WufrInterfaceStaticsResult

    @property
    def ok(self) -> bool:
        return self.solve.ok


@dataclass(frozen=True)
class WUFRStaticLevel1Result:
    status: WUFRStaticLevel1Status
    result_label: str
    authorization_id: str
    model_id: str
    configuration_id: str
    static_state_id: str
    upstream_carrier_result_label: str
    upstream_carrier_model_id: str
    upstream_carrier_authorization_id: str
    corners: tuple[WUFRStaticLevel1CornerResult, ...] = ()
    maximum_force_residual_N: float | None = None
    maximum_moment_residual_Nm: float | None = None
    maximum_hinge_axis_moment_Nm: float | None = None
    maximum_condition_number_inf: float | None = None
    minimum_relative_pivot: float | None = None
    complete_for_authorized_static_gravity_case: bool = False
    complete_physical_vehicle_load_case: bool = False
    maneuver_complete: bool = False
    individual_a_arm_joint_split_authorized: bool = False
    rocker_result_publication_authorized: bool = False
    installed_as_built_authority: bool = False
    production_authority: bool = False
    failure_code: WUFRStaticLevel1FailureCode | None = None
    failed_corner_id: str | None = None
    failed_stage: str | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticLevel1Status.SUCCESS


FrontSteeringBuilder = Callable[
    [WUFRStaticLevel1Provider, str, object],
    tuple[CurrentLateralLinkState, float | None],
]


def _v3(values: Sequence[float], label: str) -> Vector3:
    if len(values) != 3:
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.NONFINITE_OUTPUT,
            f"{label} must contain three values",
        )
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.NONFINITE_OUTPUT,
            f"{label} must be finite",
        )
    return result  # type: ignore[return-value]


def _max_difference(left: Sequence[float], right: Sequence[float]) -> float:
    return max(abs(float(a) - float(b)) for a, b in zip(left, right))


def _corner_identity(corner_id: str) -> tuple[Axle, Side, str, str]:
    if corner_id == "front_left":
        return Axle.FRONT, Side.LEFT, "front", "left"
    if corner_id == "front_right":
        return Axle.FRONT, Side.RIGHT, "front", "right"
    if corner_id == "rear_left":
        return Axle.REAR, Side.LEFT, "rear", "left"
    if corner_id == "rear_right":
        return Axle.REAR, Side.RIGHT, "rear", "right"
    raise WUFRStaticLevel1Error(
        WUFRStaticLevel1FailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
        f"Unknown corner {corner_id!r}",
    )


def load_wufr_static_level1_source(path: str | Path) -> WUFRStaticLevel1Source:
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    carrier = document.get("source", {}).get("carrier_wrench", {})
    level1 = document.get("source", {}).get("level1_solver", {})
    boundaries = document.get("boundaries", {})
    source = WUFRStaticLevel1Source(
        record_id=str(document.get("record_id", "")),
        configuration_id=str(document.get("configuration_id", "")),
        static_state_id=str(document.get("static_state_id", "")),
        authorization_id=str(document.get("authorization_id", "")),
        model_id=str(document.get("model_id", "")),
        result_label=str(document.get("result_label", "")),
        corner_order=tuple(str(value) for value in document.get("corner_order", ())),  # type: ignore[arg-type]
        carrier_model_id=str(carrier.get("model_id", "")),
        carrier_authorization_id=str(carrier.get("authorization_id", "")),
        carrier_result_label=str(carrier.get("required_result_label", "")),
        carrier_frame_id=str(carrier.get("required_frame", "")),
        level1_model_id=str(level1.get("model_id", "")),
        level1_authorization_id=str(level1.get("authorization_id", "")),
        geometry_source_id="WUFR27_LEVEL1_LINKAGE_TOPOLOGY_V0",
        complete_for_authorized_static_gravity_case=bool(
            boundaries.get("complete_for_authorized_static_gravity_case", False)
        ),
        complete_physical_vehicle_load_case=bool(
            boundaries.get("complete_physical_vehicle_load_case", True)
        ),
        maneuver_complete=bool(boundaries.get("maneuver_complete", True)),
        rocker_result_publication_authorized=bool(
            boundaries.get("rocker_result_publication_authorized", True)
        ),
        installed_as_built_authority=bool(
            boundaries.get("installed_as_built_authority", True)
        ),
        production_authority=bool(boundaries.get("production_authority", True)),
    )
    valid = (
        source.record_id == REQUIRED_RECORD_ID
        and source.configuration_id == REQUIRED_CONFIGURATION_ID
        and source.static_state_id == REQUIRED_STATIC_STATE_ID
        and source.authorization_id == REQUIRED_AUTHORIZATION_ID
        and source.model_id == REQUIRED_MODEL_ID
        and source.result_label == RESULT_LABEL
        and source.corner_order == CORNER_ORDER
        and source.carrier_model_id == REQUIRED_CARRIER_MODEL_ID
        and source.carrier_authorization_id == REQUIRED_CARRIER_AUTHORIZATION_ID
        and source.carrier_result_label == REQUIRED_CARRIER_RESULT_LABEL
        and source.carrier_frame_id == LEVEL1_FRAME_ID
        and source.level1_model_id == REQUIRED_LEVEL1_MODEL_ID
        and source.level1_authorization_id == REQUIRED_LEVEL1_AUTHORIZATION_ID
        and source.complete_for_authorized_static_gravity_case
        and not source.complete_physical_vehicle_load_case
        and not source.maneuver_complete
        and not source.rocker_result_publication_authorized
        and not source.installed_as_built_authority
        and not source.production_authority
    )
    if not valid:
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.SOURCE_MISMATCH,
            "Static Level-1 source identity/boundary does not match AUTH-SUSP-0017",
        )
    return source


def load_wufr_static_level1_provider(
    *,
    source_path: str | Path,
    carrier_source_path: str | Path,
    static_equilibrium_result_path: str | Path,
    static_equilibrium_source_path: str | Path,
    road_contact_source_path: str | Path,
    suspension_geometry_path: str | Path,
    wheel_profile_path: str | Path,
    steering_geometry_path: str | Path,
    whole_vehicle_path: str | Path,
    gravity_path: str | Path,
    spring_package_path: str | Path,
    zbar_fixture_path: str | Path,
    config: WUFRStaticLevel1Config | None = None,
) -> WUFRStaticLevel1Provider:
    return WUFRStaticLevel1Provider(
        source=load_wufr_static_level1_source(source_path),
        carrier_provider=load_wufr_static_carrier_wrench_provider(
            source_path=carrier_source_path,
            static_equilibrium_result_path=static_equilibrium_result_path,
            static_equilibrium_source_path=static_equilibrium_source_path,
            road_contact_source_path=road_contact_source_path,
            suspension_geometry_path=suspension_geometry_path,
            wheel_profile_path=wheel_profile_path,
            steering_geometry_path=steering_geometry_path,
            whole_vehicle_path=whole_vehicle_path,
            gravity_path=gravity_path,
            spring_package_path=spring_package_path,
            zbar_fixture_path=zbar_fixture_path,
        ),
        config=config or WUFRStaticLevel1Config(),
    )


def _failure(
    provider: WUFRStaticLevel1Provider,
    code: WUFRStaticLevel1FailureCode,
    message: str,
    *,
    corner_id: str | None = None,
    stage: str | None = None,
) -> WUFRStaticLevel1Result:
    source = provider.source
    return WUFRStaticLevel1Result(
        status=WUFRStaticLevel1Status.FAILURE,
        result_label=source.result_label,
        authorization_id=source.authorization_id,
        model_id=source.model_id,
        configuration_id=source.configuration_id,
        static_state_id=source.static_state_id,
        upstream_carrier_result_label=source.carrier_result_label,
        upstream_carrier_model_id=source.carrier_model_id,
        upstream_carrier_authorization_id=source.carrier_authorization_id,
        corners=(),
        failure_code=code,
        failed_corner_id=corner_id,
        failed_stage=stage,
        message=message,
    )


def _validate_carrier_collection(
    provider: WUFRStaticLevel1Provider,
    carrier_result: WUFRStaticCarrierWrenchResult,
) -> tuple[WUFRStaticLevel1FailureCode, str] | None:
    source = provider.source
    if not carrier_result.ok:
        return (
            WUFRStaticLevel1FailureCode.UPSTREAM_CARRIER_RESULT_FAILURE,
            carrier_result.message or "MOD-VEH-0008 carrier result is unsuccessful",
        )
    if (
        carrier_result.result_label != source.carrier_result_label
        or carrier_result.authorization_id != source.carrier_authorization_id
        or carrier_result.model_id != source.carrier_model_id
    ):
        return WUFRStaticLevel1FailureCode.SOURCE_MISMATCH, "Carrier result identity mismatch"
    if carrier_result.configuration_id != source.configuration_id:
        return WUFRStaticLevel1FailureCode.CONFIGURATION_MISMATCH, "Carrier configuration mismatch"
    if carrier_result.static_state_id != source.static_state_id:
        return WUFRStaticLevel1FailureCode.STATE_IDENTITY_MISMATCH, "Carrier static-state mismatch"
    if tuple(corner.corner_id for corner in carrier_result.corners) != source.corner_order:
        return (
            WUFRStaticLevel1FailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
            "Carrier corners must be exactly FL/FR/RL/RR in fixed order",
        )
    if not carrier_result.complete_for_authorized_static_gravity_case:
        return (
            WUFRStaticLevel1FailureCode.UPSTREAM_CARRIER_RESULT_FAILURE,
            "Carrier collection is not complete for the authorized static-gravity case",
        )
    return None


def _build_current_front_lateral_state(
    provider: WUFRStaticLevel1Provider,
    corner_id: str,
    suspension_state: object,
) -> tuple[CurrentLateralLinkState, float | None]:
    road_provider = provider.carrier_provider.equilibrium_provider.road_contact
    _, _, _, side_name = _corner_identity(corner_id)
    transform = getattr(suspension_state, "minimum_twist_transform", None)
    if transform is None:
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.FRONT_STEERING_STATE_UNAVAILABLE,
            f"{corner_id} minimum-twist suspension transform is unavailable",
        )
    base = road_provider.steering_geometry
    original = base.left if side_name == "left" else base.right
    axis = AxisLine(
        point=transform.apply_point(original.steering_axis.point),
        direction=transform.apply_direction(original.steering_axis.direction),
    )
    transformed_corner = SteeringCorner(
        side=original.side,
        steering_axis=axis,
        rack_inner_joint_at_center=original.rack_inner_joint_at_center,
        outer_tie_rod_joint_at_center=transform.apply_point(
            original.outer_tie_rod_joint_at_center
        ),
        tie_rod_length=original.tie_rod_length,
        reference_upright_rotation=0.0,
        mechanical_rotation_min=original.mechanical_rotation_min,
        mechanical_rotation_max=original.mechanical_rotation_max,
        wheel_forward_direction_at_center=(
            transform.apply_direction(original.wheel_forward_direction_at_center)
            if original.wheel_forward_direction_at_center is not None
            else None
        ),
        static_toe=original.static_toe,
        source_role=f"AUTH-SUSP-0017:{original.source_role}",
    )
    posed = replace(
        base,
        geometry_id=f"{base.geometry_id}:STATIC_LEVEL1:{corner_id}",
        left=transformed_corner if side_name == "left" else base.left,
        right=transformed_corner if side_name == "right" else base.right,
        steering_axis_track=None,
    )
    solved = solve_corner_position(posed, side_name, 0.0)
    if (
        not solved.ok
        or solved.rotated_outer_joint is None
        or solved.rack_inner_joint is None
    ):
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.FRONT_STEERING_STATE_UNAVAILABLE,
            f"{corner_id} centered-rack MOD-STEER-0001 closure failed: {solved.failure_code} {solved.message}",
        )
    return (
        CurrentLateralLinkState(
            body_point_m=_v3(solved.rotated_outer_joint, "steering outer joint"),
            remote_point_m=_v3(solved.rack_inner_joint, "steering rack joint"),
            source_id=f"MOD-STEER-0001:current_centered_rack_closure:{corner_id}",
        ),
        solved.closure_length_residual,
    )


def _current_geometry(
    provider: WUFRStaticLevel1Provider,
    carrier_corner: WUFRStaticCarrierCornerResult,
    wheel_coordinate_m: float,
    *,
    front_steering_builder: FrontSteeringBuilder,
) -> tuple[float, Level1CornerGeometry, ActuationStateResult, str | None, float | None]:
    axle, side, axle_name, _ = _corner_identity(carrier_corner.corner_id)
    road_provider = provider.carrier_provider.equilibrium_provider.road_contact
    point_state = evaluate_corner_point_state(
        road_provider,
        carrier_corner.corner_id,
        wheel_coordinate_m,
    )
    corner = road_provider.suspension_geometry.corner(axle, side)
    nominal = build_nominal_wheel_reference(road_provider.wheel_profile, axle, side)
    actuation = solve_actuation_q_L_state(
        corner,
        nominal,
        point_state.q_L_rad,
        kinematics_config=road_provider.config.kinematics_solver,
        geometry_id=road_provider.suspension_geometry.geometry_id,
        configuration_id=provider.source.configuration_id,
        source_authority=road_provider.suspension_geometry.authority,
    )
    suspension = actuation.wheel_state.upstream_state if actuation.wheel_state else None
    if not actuation.ok or suspension is None or not suspension.ok:
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.CURRENT_GEOMETRY_FAILURE,
            actuation.message or f"{carrier_corner.corner_id} current suspension/actuation state failed",
        )
    steering: CurrentLateralLinkState | None = None
    steering_residual: float | None = None
    if axle is Axle.FRONT:
        steering, steering_residual = front_steering_builder(
            provider, carrier_corner.corner_id, suspension
        )
    try:
        geometry = build_level1_geometry_from_current_states(
            corner,
            suspension,
            actuation,
            front_lateral_state=steering,
            geometry_source_id=provider.source.geometry_source_id,
        )
    except WufrInterfaceAdapterError as exc:
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.CURRENT_GEOMETRY_FAILURE,
            str(exc),
        ) from exc
    if geometry.axle != axle_name:
        raise WUFRStaticLevel1Error(
            WUFRStaticLevel1FailureCode.STATE_IDENTITY_MISMATCH,
            f"{carrier_corner.corner_id} current geometry axle mismatch",
        )
    return (
        point_state.q_L_rad,
        geometry,
        actuation,
        steering.source_id if steering else None,
        steering_residual,
    )


def evaluate_wufr_static_level1_interface_loads(
    provider: WUFRStaticLevel1Provider,
    *,
    carrier_result: WUFRStaticCarrierWrenchResult | None = None,
    front_steering_builder: FrontSteeringBuilder = _build_current_front_lateral_state,
) -> WUFRStaticLevel1Result:
    carrier = carrier_result or evaluate_wufr_static_carrier_wrenches(
        provider.carrier_provider
    )
    validation = _validate_carrier_collection(provider, carrier)
    if validation is not None:
        code, message = validation
        return _failure(provider, code, message, stage="carrier_collection")

    accepted = provider.carrier_provider.accepted_result
    results: list[WUFRStaticLevel1CornerResult] = []
    for index, corner_id in enumerate(CORNER_ORDER):
        carrier_corner = carrier.corners[index]
        axle, _, axle_name, side_name = _corner_identity(corner_id)
        try:
            if (
                not carrier_corner.ok
                or carrier_corner.corner_id != corner_id
                or carrier_corner.axle != axle_name
                or carrier_corner.side != side_name
                or carrier_corner.configuration_id != provider.source.configuration_id
                or carrier_corner.static_state_id != provider.source.static_state_id
                or not carrier_corner.complete_for_authorized_static_gravity_case
                or carrier_corner.level1_wrench is None
            ):
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.STATE_IDENTITY_MISMATCH,
                    f"{corner_id} carrier corner identity/completeness mismatch",
                )
            wrench = carrier_corner.level1_wrench
            expected_load_case_suffix = f":{corner_id}"
            if not wrench.load_case_id.endswith(expected_load_case_suffix):
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.LOAD_CASE_MISMATCH,
                    f"{corner_id} carrier load-case identity mismatch",
                )
            if wrench.frame_id != provider.source.carrier_frame_id:
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.FRAME_OR_REFERENCE_MISMATCH,
                    f"{corner_id} carrier wrench frame mismatch",
                )
            q_L, geometry, actuation, steering_id, steering_residual = _current_geometry(
                provider,
                carrier_corner,
                accepted.wheel_coordinates_m[index],
                front_steering_builder=front_steering_builder,
            )
            if geometry.geometry_source_id != provider.source.geometry_source_id:
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.GEOMETRY_SOURCE_MISMATCH,
                    f"{corner_id} Level-1 geometry source mismatch",
                )
            cfg = provider.config
            if (
                _max_difference(geometry.carrier_reference_m, wrench.reference_point_m)
                > cfg.carrier_reference_match_tolerance_m
                or carrier_corner.carrier_reference_level1_m is None
                or _max_difference(
                    geometry.carrier_reference_m,
                    carrier_corner.carrier_reference_level1_m,
                )
                > cfg.carrier_reference_match_tolerance_m
            ):
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.FRAME_OR_REFERENCE_MISMATCH,
                    f"{corner_id} current carrier reference disagrees with MOD-VEH-0008",
                )
            if (
                carrier_corner.upper_spherical_level1_m is None
                or carrier_corner.lower_spherical_level1_m is None
                or _max_difference(
                    geometry.upper_spherical_point_m,
                    carrier_corner.upper_spherical_level1_m,
                )
                > cfg.spherical_point_match_tolerance_m
                or _max_difference(
                    geometry.lower_spherical_point_m,
                    carrier_corner.lower_spherical_level1_m,
                )
                > cfg.spherical_point_match_tolerance_m
            ):
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.STATE_IDENTITY_MISMATCH,
                    f"{corner_id} current spherical points disagree with carrier record",
                )
            solved = solve_wufr_level1_interface_statics(
                geometry,
                wrench,
                config=cfg.solver_config,
            )
            if not solved.ok:
                raise WUFRStaticLevel1Error(
                    WUFRStaticLevel1FailureCode.CORNER_SOLVE_FAILURE,
                    f"{corner_id} MOD-SUSP-0007 solve failed: {solved.failure_code} {solved.message}",
                )
            results.append(
                WUFRStaticLevel1CornerResult(
                    corner_id=corner_id,
                    axle=axle_name,
                    side=side_name,
                    wheel_coordinate_m=accepted.wheel_coordinates_m[index],
                    q_L_rad=q_L,
                    geometry=geometry,
                    carrier_wrench=wrench,
                    steering_source_id=steering_id,
                    steering_closure_residual_m=steering_residual,
                    actuation_state=actuation,
                    solve=solved,
                )
            )
        except WUFRStaticLevel1Error as exc:
            return _failure(
                provider,
                exc.code,
                str(exc),
                corner_id=corner_id,
                stage="current_geometry_or_solve",
            )
        except Exception as exc:  # fail closed on unexpected provider/geometry exceptions
            return _failure(
                provider,
                WUFRStaticLevel1FailureCode.CURRENT_GEOMETRY_FAILURE,
                f"{corner_id} current-state composition failed: {exc}",
                corner_id=corner_id,
                stage="current_geometry_or_solve",
            )

    if tuple(result.corner_id for result in results) != CORNER_ORDER:
        return _failure(
            provider,
            WUFRStaticLevel1FailureCode.COLLECTION_INCOMPLETE,
            "Four-corner result collection is incomplete or reordered",
            stage="collection",
        )

    force_residual = max(
        body.force_inf_norm_N
        for corner in results
        for body in corner.solve.body_residuals
    )
    moment_residual = max(
        body.moment_inf_norm_Nm
        for corner in results
        for body in corner.solve.body_residuals
    )
    hinge_axis = max(
        abs(reaction.moment_axis_component_Nm)
        for corner in results
        for reaction in (corner.solve.upper_hinge, corner.solve.lower_hinge)
        if reaction is not None
    )
    conditions = [
        corner.solve.condition_number_inf
        for corner in results
        if corner.solve.condition_number_inf is not None
    ]
    pivots = [
        corner.solve.minimum_relative_pivot
        for corner in results
        if corner.solve.minimum_relative_pivot is not None
    ]
    scalar_outputs = (
        force_residual,
        moment_residual,
        hinge_axis,
        *conditions,
        *pivots,
        *(corner.solve.lateral.axial_force_N for corner in results if corner.solve.lateral),
        *(corner.solve.actuation.axial_force_N for corner in results if corner.solve.actuation),
    )
    if not all(math.isfinite(float(value)) for value in scalar_outputs):
        return _failure(
            provider,
            WUFRStaticLevel1FailureCode.NONFINITE_OUTPUT,
            "Integrated Level-1 result contains nonfinite output",
            stage="collection",
        )

    source = provider.source
    return WUFRStaticLevel1Result(
        status=WUFRStaticLevel1Status.SUCCESS,
        result_label=source.result_label,
        authorization_id=source.authorization_id,
        model_id=source.model_id,
        configuration_id=source.configuration_id,
        static_state_id=source.static_state_id,
        upstream_carrier_result_label=source.carrier_result_label,
        upstream_carrier_model_id=source.carrier_model_id,
        upstream_carrier_authorization_id=source.carrier_authorization_id,
        corners=tuple(results),
        maximum_force_residual_N=force_residual,
        maximum_moment_residual_Nm=moment_residual,
        maximum_hinge_axis_moment_Nm=hinge_axis,
        maximum_condition_number_inf=max(conditions),
        minimum_relative_pivot=min(pivots),
        complete_for_authorized_static_gravity_case=True,
        complete_physical_vehicle_load_case=False,
        maneuver_complete=False,
        individual_a_arm_joint_split_authorized=False,
        rocker_result_publication_authorized=False,
        installed_as_built_authority=False,
        production_authority=False,
        message="Four synchronized WUFR Level-1 interface solves completed",
    )
