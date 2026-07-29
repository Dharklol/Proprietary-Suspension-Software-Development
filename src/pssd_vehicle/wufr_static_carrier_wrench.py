"""WUFR static-gravity outboard-carrier external wrench adapter.

Implements ``AUTH-VEH-0011`` / ``MOD-VEH-0008``.  The adapter consumes the
accepted ``MOD-VEH-0007`` machine-readable static-equilibrium record and the
same reviewed providers that generated it.  For each corner it composes only:

* the recovered road-normal point force at the exact current contact point; and
* the ``ASM-VEH-0003`` prototype unsprung gravity point force at the exact
  current physical wheel center.

The result is a complete prescribed outboard-carrier wrench only for the exact
uncorrelated static-gravity model state.  It is not a maneuver, installed,
component-mass-distribution, linkage-load, rocker-load, or structural-release
result.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path
import tomllib
from typing import Mapping, Sequence

from pssd_suspension.geometry import Axle, Side
from pssd_suspension.wheel_reference import (
    build_nominal_wheel_reference,
    solve_wheel_reference_state,
)
from pssd_suspension.wufr_interface_statics import CompleteCarrierWrench

from .force_coordinates import (
    AppliedWrench,
    BodyPose,
    PointReference,
    ResultantWrench,
    assemble_wrenches,
    rotation_matrix_yaw_pitch_roll,
    transport_body_fixed_point,
)
from .wufr_road_contact import CORNER_ORDER, evaluate_corner_road_state
from .wufr_static_equilibrium import (
    WUFRStaticEquilibriumProvider,
    load_wufr_static_equilibrium_provider,
)


Vector3 = tuple[float, float, float]
Matrix3 = tuple[Vector3, Vector3, Vector3]
RESULT_LABEL = "uncorrelated_design_intent_static_carrier_wrench"
REQUIRED_RECORD_ID = "WUFR27_STATIC_CARRIER_WRENCH_V0"
REQUIRED_AUTHORIZATION_ID = "AUTH-VEH-0011"
REQUIRED_MODEL_ID = "MOD-VEH-0008"
REQUIRED_CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
REQUIRED_STATIC_STATE_ID = "WUFR26_DRIVER_NO_FUEL_DESIGN_INTENT_REFERENCE"
REQUIRED_UPSTREAM_AUTHORIZATION_ID = "AUTH-VEH-0010"
REQUIRED_UPSTREAM_MODEL_ID = "MOD-VEH-0007"
REQUIRED_UPSTREAM_RESULT_LABEL = "uncorrelated_design_intent_static_gravity"
REQUIRED_UPSTREAM_ASSUMPTION_IDS = (
    "ASM-VEH-0002",
    "ASM-VEH-0003",
    "ASM-VEH-0005",
    "ASM-SUSP-0002",
    "ASM-SUSP-0003",
)
LEVEL1_FRAME_ID = "WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL"


class WUFRStaticCarrierWrenchStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WUFRStaticCarrierWrenchFailureCode(str, Enum):
    SOURCE_MISMATCH = "source_mismatch"
    NONFINITE_INPUT = "nonfinite_input"
    UPSTREAM_RESULT_FAILURE = "upstream_result_failure"
    CORNER_CONTRACT_MISMATCH = "corner_contract_mismatch"
    NEGATIVE_REACTION = "negative_reaction"
    PHYSICAL_POINT_MISMATCH = "physical_point_mismatch"
    FRAME_MISMATCH = "frame_mismatch"
    GRAVITY_SOURCE_MISMATCH = "gravity_source_mismatch"
    CARRIER_REFERENCE_FAILURE = "carrier_reference_failure"
    TRANSFORM_FAILURE = "transform_failure"
    WRENCH_COMPOSITION_FAILURE = "wrench_composition_failure"
    ROUND_TRIP_FAILURE = "round_trip_failure"
    RECONSTRUCTION_FAILURE = "reconstruction_failure"


class WUFRStaticCarrierWrenchError(ValueError):
    def __init__(self, code: WUFRStaticCarrierWrenchFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WUFRStaticCarrierWrenchSource:
    record_id: str
    configuration_id: str
    static_state_id: str
    authorization_id: str
    model_id: str
    result_label: str
    upstream_model_id: str
    upstream_authorization_id: str
    upstream_result_label: str
    upstream_frozen_result: str
    corner_order: tuple[str, str, str, str]
    axle_order: tuple[str, str, str, str]
    side_order: tuple[str, str, str, str]
    road_frame_id: str
    road_origin_id: str
    body_frame_id: str
    body_origin_id: str
    source_frame_id: str
    source_origin_id: str
    level1_frame_id: str
    complete_for_authorized_static_gravity_case: bool
    complete_physical_hardware_wrench: bool
    complete_maneuver_wrench: bool
    installed_as_built_authority: bool
    integrated_level1_linkage_result_authority: bool


@dataclass(frozen=True)
class WUFRStaticCarrierWrenchConfig:
    point_match_tolerance_m: float = 1.0e-10
    component_composition_tolerance: float = 1.0e-12
    wrench_transport_tolerance_N: float = 1.0e-10
    wrench_transport_tolerance_Nm: float = 1.0e-10
    four_corner_force_reconstruction_tolerance_N: float = 1.0e-6
    four_corner_moment_reconstruction_tolerance_Nm: float = 1.0e-6
    accepted_closure_match_tolerance_N: float = 1.0e-10
    accepted_closure_match_tolerance_Nm: float = 1.0e-10

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(float(value)) and float(value) > 0.0
            for value in self.__dict__.values()
        ):
            raise WUFRStaticCarrierWrenchError(
                WUFRStaticCarrierWrenchFailureCode.NONFINITE_INPUT,
                "Carrier-wrench tolerances must be finite and positive",
            )


@dataclass(frozen=True)
class AcceptedStaticEquilibriumRecord:
    version: str
    authorization_id: str
    model_id: str
    configuration_id: str
    static_state_id: str
    result_label: str
    assumption_ids: tuple[str, ...]
    report_status: str
    primary_ok: bool
    primary_status: str
    primary_result_label: str
    front_arb_setting: int
    rear_arb_setting: int
    q_body: Vector3
    wheel_coordinate_order: tuple[str, str, str, str]
    wheel_coordinates_m: tuple[float, float, float, float]
    road_reactions_N: tuple[float, float, float, float]
    contact_points_road_m: tuple[Vector3, Vector3, Vector3, Vector3]
    wheel_centers_road_m: tuple[Vector3, Vector3, Vector3, Vector3]
    physical_closure_ok: bool
    physical_closure_force_N: Vector3
    physical_closure_moment_Nm: Vector3
    complete_static_road_reaction: bool
    installed_as_built_authority: bool
    historical_scale_reconstruction_used: bool
    source_path: str


@dataclass(frozen=True)
class RigidFrameTransform:
    source_frame_id: str
    target_frame_id: str
    target_origin_id: str
    rotation_target_from_source: Matrix3
    translation_target_of_source_origin_m: Vector3
    axle_source_x_m: float
    body_pose: BodyPose
    authority: str = REQUIRED_AUTHORIZATION_ID


@dataclass(frozen=True)
class CarrierWrenchRepresentation:
    frame_id: str
    origin_id: str
    reference_point_id: str
    reference_point_m: Vector3
    force_N: Vector3
    moment_Nm: Vector3


@dataclass(frozen=True)
class WUFRStaticCarrierCornerResult:
    status: WUFRStaticCarrierWrenchStatus
    corner_id: str
    axle: str
    side: str
    configuration_id: str
    static_state_id: str
    road_reaction_N: float | None = None
    road_normal: Vector3 | None = None
    contact_point_road: PointReference | None = None
    wheel_center_road: PointReference | None = None
    upper_spherical_level1_m: Vector3 | None = None
    lower_spherical_level1_m: Vector3 | None = None
    carrier_reference_level1_m: Vector3 | None = None
    carrier_reference_source_m: Vector3 | None = None
    carrier_reference_body_m: Vector3 | None = None
    carrier_reference_road: PointReference | None = None
    frame_transform: RigidFrameTransform | None = None
    road_force_wrench: AppliedWrench | None = None
    unsprung_gravity_wrench: AppliedWrench | None = None
    road_resultant: ResultantWrench | None = None
    road_representation: CarrierWrenchRepresentation | None = None
    level1_wrench: CompleteCarrierWrench | None = None
    round_trip_force_residual_N: float | None = None
    round_trip_moment_residual_Nm: float | None = None
    complete_for_authorized_static_gravity_case: bool = False
    complete_physical_hardware_wrench: bool = False
    maneuver_complete: bool = False
    installed_as_built_authority: bool = False
    failure_code: WUFRStaticCarrierWrenchFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticCarrierWrenchStatus.SUCCESS


@dataclass(frozen=True)
class WUFRStaticCarrierWrenchResult:
    status: WUFRStaticCarrierWrenchStatus
    result_label: str
    authorization_id: str
    model_id: str
    configuration_id: str
    static_state_id: str
    upstream_result_path: str
    corners: tuple[WUFRStaticCarrierCornerResult, ...] = ()
    reconstruction_at_road_origin: ResultantWrench | None = None
    reconstruction_at_body_origin: ResultantWrench | None = None
    accepted_closure_force_N: Vector3 | None = None
    accepted_closure_moment_Nm: Vector3 | None = None
    maximum_force_residual_N: float | None = None
    maximum_moment_residual_Nm: float | None = None
    accepted_force_match_residual_N: float | None = None
    accepted_moment_match_residual_Nm: float | None = None
    complete_for_authorized_static_gravity_case: bool = False
    complete_physical_hardware_wrench: bool = False
    maneuver_complete: bool = False
    installed_as_built_authority: bool = False
    integrated_level1_linkage_result_authority: bool = False
    historical_scale_reconstruction_used: bool = False
    hidden_balancing_wrench_used: bool = False
    failure_code: WUFRStaticCarrierWrenchFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticCarrierWrenchStatus.SUCCESS


@dataclass(frozen=True)
class WUFRStaticCarrierWrenchProvider:
    source: WUFRStaticCarrierWrenchSource
    equilibrium_provider: WUFRStaticEquilibriumProvider
    accepted_result: AcceptedStaticEquilibriumRecord
    config: WUFRStaticCarrierWrenchConfig


def _v3(values: Sequence[float], label: str) -> Vector3:
    if len(values) != 3:
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.NONFINITE_INPUT,
            f"{label} must contain three values",
        )
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.NONFINITE_INPUT,
            f"{label} must be finite",
        )
    return result  # type: ignore[return-value]


def _v4(values: Sequence[float], label: str) -> tuple[float, float, float, float]:
    if len(values) != 4:
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.CORNER_CONTRACT_MISMATCH,
            f"{label} must contain four values in canonical corner order",
        )
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.NONFINITE_INPUT,
            f"{label} must be finite",
        )
    return result  # type: ignore[return-value]


def _add(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: Vector3, b: Vector3) -> Vector3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(value: float, vector: Vector3) -> Vector3:
    return (value * vector[0], value * vector[1], value * vector[2])


def _midpoint(a: Vector3, b: Vector3) -> Vector3:
    return (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]), 0.5 * (a[2] + b[2]))


def _mat_vec(matrix: Matrix3, vector: Vector3) -> Vector3:
    return tuple(
        sum(float(matrix[row][col]) * float(vector[col]) for col in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _transpose(matrix: Matrix3) -> Matrix3:
    return tuple(zip(*matrix))  # type: ignore[return-value]


def _max_difference(left: Sequence[float], right: Sequence[float]) -> float:
    return max(abs(float(a) - float(b)) for a, b in zip(left, right))


def _corner_identity(corner_id: str) -> tuple[Axle, Side, str, str]:
    mapping = {
        "front_left": (Axle.FRONT, Side.LEFT, "front", "left"),
        "front_right": (Axle.FRONT, Side.RIGHT, "front", "right"),
        "rear_left": (Axle.REAR, Side.LEFT, "rear", "left"),
        "rear_right": (Axle.REAR, Side.RIGHT, "rear", "right"),
    }
    try:
        return mapping[corner_id]
    except KeyError as exc:
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.CORNER_CONTRACT_MISMATCH,
            f"Unknown corner identity {corner_id!r}",
        ) from exc


def load_wufr_static_carrier_wrench_source(
    path: str | Path,
) -> WUFRStaticCarrierWrenchSource:
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    upstream = document.get("upstream", {}).get("static_equilibrium", {})
    corner = document.get("corner_contract", {})
    frames = document.get("frame_contract", {})
    complete = document.get("completeness", {})
    boundaries = document.get("boundaries", {})
    source = WUFRStaticCarrierWrenchSource(
        record_id=str(document.get("record_id", "")),
        configuration_id=str(document.get("configuration_id", "")),
        static_state_id=str(document.get("static_state_id", "")),
        authorization_id=str(document.get("authorization_id", "")),
        model_id=str(document.get("model_id", "")),
        result_label=str(document.get("result_label", "")),
        upstream_model_id=str(upstream.get("model_id", "")),
        upstream_authorization_id=str(upstream.get("authorization_id", "")),
        upstream_result_label=str(upstream.get("required_result_label", "")),
        upstream_frozen_result=str(upstream.get("frozen_result", "")),
        corner_order=tuple(str(value) for value in corner.get("order", ())),  # type: ignore[arg-type]
        axle_order=tuple(str(value) for value in corner.get("axle_order", ())),  # type: ignore[arg-type]
        side_order=tuple(str(value) for value in corner.get("side_order", ())),  # type: ignore[arg-type]
        road_frame_id=str(frames.get("road_frame_id", "")),
        road_origin_id=str(frames.get("road_origin_id", "")),
        body_frame_id=str(frames.get("body_frame_id", "")),
        body_origin_id=str(frames.get("body_origin_id", "")),
        source_frame_id=str(frames.get("source_frame_id", "")),
        source_origin_id=str(frames.get("source_origin_id", "")),
        level1_frame_id=str(frames.get("level1_frame_id", "")),
        complete_for_authorized_static_gravity_case=bool(
            complete.get("complete_for_authorized_static_gravity_case", False)
        ),
        complete_physical_hardware_wrench=bool(
            complete.get("complete_physical_hardware_wrench", True)
        ),
        complete_maneuver_wrench=bool(complete.get("complete_maneuver_wrench", True)),
        installed_as_built_authority=bool(complete.get("installed_as_built_authority", True)),
        integrated_level1_linkage_result_authority=bool(
            boundaries.get("integrated_level1_linkage_result_authority", True)
        ),
    )
    expected = (
        source.record_id == REQUIRED_RECORD_ID
        and source.configuration_id == REQUIRED_CONFIGURATION_ID
        and source.static_state_id == REQUIRED_STATIC_STATE_ID
        and source.authorization_id == REQUIRED_AUTHORIZATION_ID
        and source.model_id == REQUIRED_MODEL_ID
        and source.result_label == RESULT_LABEL
        and source.upstream_model_id == REQUIRED_UPSTREAM_MODEL_ID
        and source.upstream_authorization_id == REQUIRED_UPSTREAM_AUTHORIZATION_ID
        and source.upstream_result_label == REQUIRED_UPSTREAM_RESULT_LABEL
        and source.corner_order == CORNER_ORDER
        and source.axle_order == ("front", "front", "rear", "rear")
        and source.side_order == ("left", "right", "left", "right")
        and source.level1_frame_id == LEVEL1_FRAME_ID
        and source.complete_for_authorized_static_gravity_case
        and not source.complete_physical_hardware_wrench
        and not source.complete_maneuver_wrench
        and not source.installed_as_built_authority
        and not source.integrated_level1_linkage_result_authority
    )
    if not expected:
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.SOURCE_MISMATCH,
            "Static carrier-wrench source identity/boundary does not match AUTH-VEH-0011",
        )
    return source


def load_accepted_static_equilibrium_record(
    path: str | Path,
) -> AcceptedStaticEquilibriumRecord:
    source_path = Path(path)
    document = json.loads(source_path.read_text(encoding="utf-8"))
    primary = document.get("primary", {})
    solve = primary.get("solve", {})
    contact = primary.get("contact", {})
    closure = primary.get("physical_closure", {})
    physical_points = primary.get("physical_points", {})
    if tuple(physical_points.keys()) != CORNER_ORDER:
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.CORNER_CONTRACT_MISMATCH,
            "Frozen physical-point keys must preserve canonical corner order",
        )
    contact_points = tuple(
        _v3(physical_points[corner]["contact_point_m"], f"{corner} contact point")
        for corner in CORNER_ORDER
    )
    wheel_centers = tuple(
        _v3(physical_points[corner]["wheel_center_m"], f"{corner} wheel center")
        for corner in CORNER_ORDER
    )
    return AcceptedStaticEquilibriumRecord(
        version=str(document.get("version", "")),
        authorization_id=str(document.get("authorization_id", "")),
        model_id=str(document.get("model_id", "")),
        configuration_id=str(document.get("configuration_id", "")),
        static_state_id=str(document.get("static_state_id", "")),
        result_label=str(document.get("result_label", "")),
        assumption_ids=tuple(str(value) for value in document.get("assumption_ids", ())),
        report_status=str(document.get("status", "")),
        primary_ok=bool(primary.get("ok", False)),
        primary_status=str(primary.get("status", "")),
        primary_result_label=str(primary.get("result_label", "")),
        front_arb_setting=int(primary.get("front_arb_setting", 0)),
        rear_arb_setting=int(primary.get("rear_arb_setting", 0)),
        q_body=_v3(solve.get("q_body", ()), "q_body"),
        wheel_coordinate_order=tuple(
            str(value) for value in solve.get("wheel_coordinate_order", ())
        ),  # type: ignore[arg-type]
        wheel_coordinates_m=_v4(solve.get("wheel_coordinates_m", ()), "wheel coordinates"),
        road_reactions_N=_v4(contact.get("normal_reaction_N", ()), "road reactions"),
        contact_points_road_m=contact_points,  # type: ignore[arg-type]
        wheel_centers_road_m=wheel_centers,  # type: ignore[arg-type]
        physical_closure_ok=bool(closure.get("ok", False)),
        physical_closure_force_N=_v3(
            closure.get("resultant_force_N", ()), "physical closure force"
        ),
        physical_closure_moment_Nm=_v3(
            closure.get("resultant_moment_Nm", ()), "physical closure moment"
        ),
        complete_static_road_reaction=bool(
            primary.get("complete_static_road_reaction", False)
        ),
        installed_as_built_authority=bool(
            primary.get("installed_as_built_authority", True)
        ),
        historical_scale_reconstruction_used=bool(
            primary.get("historical_scale_reconstruction_used", True)
        ),
        source_path=str(source_path.as_posix()),
    )


def load_wufr_static_carrier_wrench_provider(
    *,
    source_path: str | Path,
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
    config: WUFRStaticCarrierWrenchConfig | None = None,
) -> WUFRStaticCarrierWrenchProvider:
    source = load_wufr_static_carrier_wrench_source(source_path)
    equilibrium = load_wufr_static_equilibrium_provider(
        source_path=static_equilibrium_source_path,
        road_contact_source_path=road_contact_source_path,
        suspension_geometry_path=suspension_geometry_path,
        wheel_profile_path=wheel_profile_path,
        steering_geometry_path=steering_geometry_path,
        whole_vehicle_path=whole_vehicle_path,
        gravity_path=gravity_path,
        spring_package_path=spring_package_path,
        zbar_fixture_path=zbar_fixture_path,
    )
    accepted = load_accepted_static_equilibrium_record(static_equilibrium_result_path)
    return WUFRStaticCarrierWrenchProvider(
        source=source,
        equilibrium_provider=equilibrium,
        accepted_result=accepted,
        config=config or WUFRStaticCarrierWrenchConfig(),
    )


def _failure(
    provider: WUFRStaticCarrierWrenchProvider,
    code: WUFRStaticCarrierWrenchFailureCode,
    message: str,
    *,
    corners: Sequence[WUFRStaticCarrierCornerResult] = (),
) -> WUFRStaticCarrierWrenchResult:
    return WUFRStaticCarrierWrenchResult(
        WUFRStaticCarrierWrenchStatus.FAILURE,
        provider.source.result_label,
        provider.source.authorization_id,
        provider.source.model_id,
        provider.source.configuration_id,
        provider.source.static_state_id,
        provider.accepted_result.source_path,
        corners=tuple(corners),
        complete_for_authorized_static_gravity_case=False,
        complete_physical_hardware_wrench=False,
        maneuver_complete=False,
        installed_as_built_authority=False,
        integrated_level1_linkage_result_authority=False,
        historical_scale_reconstruction_used=(
            provider.accepted_result.historical_scale_reconstruction_used
        ),
        hidden_balancing_wrench_used=False,
        failure_code=code,
        message=message,
    )


def _validate_upstream(
    provider: WUFRStaticCarrierWrenchProvider,
) -> tuple[WUFRStaticCarrierWrenchFailureCode, str] | None:
    result = provider.accepted_result
    source = provider.source
    equilibrium = provider.equilibrium_provider
    if (
        result.authorization_id != source.upstream_authorization_id
        or result.model_id != source.upstream_model_id
        or result.configuration_id != source.configuration_id
        or result.static_state_id != source.static_state_id
        or result.result_label != source.upstream_result_label
        or result.primary_result_label != source.upstream_result_label
        or result.assumption_ids != REQUIRED_UPSTREAM_ASSUMPTION_IDS
        or result.wheel_coordinate_order != CORNER_ORDER
        or equilibrium.source.configuration_id != source.configuration_id
        or equilibrium.source.authorization_id != source.upstream_authorization_id
    ):
        return (
            WUFRStaticCarrierWrenchFailureCode.SOURCE_MISMATCH,
            "Accepted static-equilibrium source/configuration identities do not match AUTH-VEH-0011",
        )
    if (
        result.report_status != "pass"
        or not result.primary_ok
        or result.primary_status != "success"
        or not result.physical_closure_ok
        or not result.complete_static_road_reaction
        or result.installed_as_built_authority
        or result.historical_scale_reconstruction_used
    ):
        return (
            WUFRStaticCarrierWrenchFailureCode.UPSTREAM_RESULT_FAILURE,
            "Carrier-wrench generation requires one accepted unmodified MOD-VEH-0007 result",
        )
    if not (1 <= result.front_arb_setting <= 5 and 1 <= result.rear_arb_setting <= 5):
        return (
            WUFRStaticCarrierWrenchFailureCode.UPSTREAM_RESULT_FAILURE,
            "Accepted static-equilibrium record does not retain valid explicit ARB settings",
        )
    if not all(math.isfinite(value) for value in result.road_reactions_N):
        return (
            WUFRStaticCarrierWrenchFailureCode.NONFINITE_INPUT,
            "Road reactions must be finite",
        )
    if any(value < 0.0 for value in result.road_reactions_N):
        return (
            WUFRStaticCarrierWrenchFailureCode.NEGATIVE_REACTION,
            "Negative road reaction is incompatible with the authorized all-four-active mode",
        )
    return None


def _pose(provider: WUFRStaticCarrierWrenchProvider) -> BodyPose:
    q = provider.accepted_result.q_body
    nominal = provider.equilibrium_provider.nominal_body_pose()
    return BodyPose(
        inertial_frame_id=nominal.inertial_frame_id,
        inertial_origin_id=nominal.inertial_origin_id,
        body_frame_id=nominal.body_frame_id,
        body_origin_id=nominal.body_origin_id,
        body_origin_position_m=nominal.body_origin_position_m,
        z_s_m=q[0],
        phi_rad=q[1],
        theta_rad=q[2],
        psi_rad=nominal.psi_rad,
        authority="AUTH-VEH-0011 accepted MOD-VEH-0007 body state",
    )


def build_level1_to_road_transform(
    provider: WUFRStaticCarrierWrenchProvider,
    pose: BodyPose,
    axle: Axle,
) -> RigidFrameTransform:
    whole = provider.equilibrium_provider.road_contact.whole_vehicle
    x_axle = (
        whole.front_axle_source_position_m[0]
        if axle is Axle.FRONT
        else whole.rear_axle_source_position_m[0]
    )
    rotation = rotation_matrix_yaw_pitch_roll(
        psi_rad=pose.psi_rad,
        theta_rad=pose.theta_rad,
        phi_rad=pose.phi_rad,
    )
    source_origin_body = _add(
        whole.source_to_body_translation_m,
        (x_axle, 0.0, 0.0),
    )
    pose_origin = _add(pose.body_origin_position_m, (0.0, 0.0, pose.z_s_m))
    translation = _add(pose_origin, _mat_vec(rotation, source_origin_body))
    return RigidFrameTransform(
        source_frame_id=provider.source.level1_frame_id,
        target_frame_id=provider.source.road_frame_id,
        target_origin_id=provider.source.road_origin_id,
        rotation_target_from_source=rotation,
        translation_target_of_source_origin_m=translation,
        axle_source_x_m=x_axle,
        body_pose=pose,
    )


def transform_level1_point_to_road(
    transform: RigidFrameTransform,
    point_level1_m: Sequence[float],
) -> Vector3:
    point = _v3(point_level1_m, "Level-1 point")
    return _add(
        transform.translation_target_of_source_origin_m,
        _mat_vec(transform.rotation_target_from_source, point),
    )


def pullback_road_wrench_to_level1(
    transform: RigidFrameTransform,
    force_road_N: Sequence[float],
    moment_road_Nm: Sequence[float],
) -> tuple[Vector3, Vector3]:
    """Rotate one road-expressed wrench to Level-1 at the same physical reference."""
    rotation_level1_from_road = _transpose(transform.rotation_target_from_source)
    return (
        _mat_vec(rotation_level1_from_road, _v3(force_road_N, "road force")),
        _mat_vec(rotation_level1_from_road, _v3(moment_road_Nm, "road moment")),
    )


def pushforward_level1_wrench_to_road(
    transform: RigidFrameTransform,
    force_level1_N: Sequence[float],
    moment_level1_Nm: Sequence[float],
) -> tuple[Vector3, Vector3]:
    """Rotate one Level-1 wrench to road coordinates at the same physical reference."""
    return (
        _mat_vec(transform.rotation_target_from_source, _v3(force_level1_N, "Level-1 force")),
        _mat_vec(transform.rotation_target_from_source, _v3(moment_level1_Nm, "Level-1 moment")),
    )


def compose_static_carrier_point_wrenches(
    *,
    corner_id: str,
    road_frame_id: str,
    road_origin_id: str,
    configuration_id: str,
    contact_point: PointReference,
    wheel_center: PointReference,
    carrier_reference: PointReference,
    road_reaction_N: float,
    road_normal: Sequence[float],
    unsprung_force_N: Sequence[float],
    road_source_id: str,
    gravity_source_id: str,
) -> tuple[AppliedWrench, AppliedWrench, ResultantWrench]:
    normal = _v3(road_normal, "road normal")
    gravity = _v3(unsprung_force_N, "unsprung gravity force")
    if not math.isfinite(road_reaction_N) or road_reaction_N < 0.0:
        raise WUFRStaticCarrierWrenchError(
            WUFRStaticCarrierWrenchFailureCode.NEGATIVE_REACTION,
            f"{corner_id} road reaction must be finite and nonnegative",
        )
    for point, role in (
        (contact_point, "contact point"),
        (wheel_center, "wheel center"),
        (carrier_reference, "carrier reference"),
    ):
        if (
            point.frame_id != road_frame_id
            or point.origin_id != road_origin_id
            or point.configuration_id != configuration_id
        ):
            raise WUFRStaticCarrierWrenchError(
                WUFRStaticCarrierWrenchFailureCode.FRAME_MISMATCH,
                f"{corner_id} {role} does not match the required road frame/origin/configuration",
            )
    road_force = _scale(road_reaction_N, normal)
    road_wrench = AppliedWrench(
        wrench_id=f"{corner_id}_road_normal_reaction",
        frame_id=road_frame_id,
        origin_id=road_origin_id,
        application_point=contact_point,
        force_N=road_force,
        free_couple_Nm=(0.0, 0.0, 0.0),
        source_id=road_source_id,
        authority="AUTH-VEH-0011 recovered road-normal external load",
    )
    gravity_wrench = AppliedWrench(
        wrench_id=f"{corner_id}_prototype_unsprung_gravity",
        frame_id=road_frame_id,
        origin_id=road_origin_id,
        application_point=wheel_center,
        force_N=gravity,
        free_couple_Nm=(0.0, 0.0, 0.0),
        source_id=gravity_source_id,
        authority="AUTH-VEH-0011 / ASM-VEH-0003 prototype wheel-center gravity",
    )
    return road_wrench, gravity_wrench, assemble_wrenches(
        (road_wrench, gravity_wrench), carrier_reference
    )


def evaluate_wufr_static_carrier_wrenches(
    provider: WUFRStaticCarrierWrenchProvider,
) -> WUFRStaticCarrierWrenchResult:
    upstream_error = _validate_upstream(provider)
    if upstream_error is not None:
        code, message = upstream_error
        return _failure(provider, code, message)

    accepted = provider.accepted_result
    equilibrium = provider.equilibrium_provider
    cfg = provider.config
    pose = _pose(provider)
    road = equilibrium.road_contact.road_plane(pose)
    whole = equilibrium.road_contact.whole_vehicle
    if (
        road.frame_id != provider.source.road_frame_id
        or road.origin_id != provider.source.road_origin_id
        or pose.body_frame_id != provider.source.body_frame_id
        or pose.body_origin_id != provider.source.body_origin_id
        or whole.source_frame_id != provider.source.source_frame_id
        or whole.source_origin_id != provider.source.source_origin_id
        or whole.body_frame_id != provider.source.body_frame_id
        or whole.body_origin_id != provider.source.body_origin_id
        or whole.road_frame_id != provider.source.road_frame_id
        or whole.road_origin_id != provider.source.road_origin_id
    ):
        return _failure(
            provider,
            WUFRStaticCarrierWrenchFailureCode.FRAME_MISMATCH,
            "Road/body frame identities do not match the AUTH-VEH-0011 source contract",
        )
    normal_magnitude = math.sqrt(sum(value * value for value in road.normal))
    if abs(normal_magnitude - 1.0) > cfg.component_composition_tolerance:
        return _failure(
            provider,
            WUFRStaticCarrierWrenchFailureCode.FRAME_MISMATCH,
            "Road normal is not unit length",
        )

    masses = {mass.corner_id: mass for mass in equilibrium.gravity.unsprung}
    if tuple(masses.keys()) != CORNER_ORDER:
        return _failure(
            provider,
            WUFRStaticCarrierWrenchFailureCode.GRAVITY_SOURCE_MISMATCH,
            "Unsprung gravity allocation does not preserve canonical corner order",
        )

    corners: list[WUFRStaticCarrierCornerResult] = []
    for index, corner_id in enumerate(CORNER_ORDER):
        axle, side, axle_name, side_name = _corner_identity(corner_id)
        try:
            road_state = evaluate_corner_road_state(
                equilibrium.road_contact,
                pose,
                corner_id,
                accepted.wheel_coordinates_m[index],
            )
            if (
                _max_difference(
                    road_state.contact_road.position_m,
                    accepted.contact_points_road_m[index],
                )
                > cfg.point_match_tolerance_m
                or _max_difference(
                    road_state.wheel_center_road.position_m,
                    accepted.wheel_centers_road_m[index],
                )
                > cfg.point_match_tolerance_m
            ):
                raise WUFRStaticCarrierWrenchError(
                    WUFRStaticCarrierWrenchFailureCode.PHYSICAL_POINT_MISMATCH,
                    f"{corner_id} recomputed physical points disagree with the accepted MOD-VEH-0007 record",
                )

            suspension_corner = equilibrium.road_contact.suspension_geometry.corner(axle, side)
            nominal = build_nominal_wheel_reference(
                equilibrium.road_contact.wheel_profile, axle, side
            )
            wheel_state = solve_wheel_reference_state(
                suspension_corner,
                nominal,
                road_state.point_state.q_L_rad,
                kinematics_config=equilibrium.road_contact.config.kinematics_solver,
                geometry_id=equilibrium.road_contact.suspension_geometry.geometry_id,
                configuration_id=provider.source.configuration_id,
                source_authority=equilibrium.road_contact.suspension_geometry.authority,
            )
            suspension_state = wheel_state.upstream_state
            if (
                not wheel_state.ok
                or suspension_state is None
                or not suspension_state.ok
                or suspension_state.upper_upright_m is None
                or suspension_state.lower_upright_m is None
            ):
                raise WUFRStaticCarrierWrenchError(
                    WUFRStaticCarrierWrenchFailureCode.CARRIER_REFERENCE_FAILURE,
                    f"{corner_id} current upper/lower spherical centers are unavailable",
                )
            upper = _v3(suspension_state.upper_upright_m, "upper spherical point")
            lower = _v3(suspension_state.lower_upright_m, "lower spherical point")
            carrier_local = _midpoint(upper, lower)
            transform = build_level1_to_road_transform(provider, pose, axle)
            carrier_source = _add(carrier_local, (transform.axle_source_x_m, 0.0, 0.0))
            carrier_body = _add(carrier_source, whole.source_to_body_translation_m)
            carrier_body_point = PointReference(
                point_id=f"{corner_id}_current_carrier_reference",
                frame_id=pose.body_frame_id,
                origin_id=pose.body_origin_id,
                position_m=carrier_body,
                role="MOD-SUSP-0007 current outboard-carrier reference",
                source_id=equilibrium.road_contact.suspension_geometry.geometry_id,
                configuration_id=provider.source.configuration_id,
                authority="AUTH-VEH-0011 / AUTH-SUSP-0012 exact current carrier reference",
                fixed_role="body_fixed",
                provenance=(("corner", corner_id), ("assumption", "ASM-SUSP-0005")),
            )
            carrier_road = transport_body_fixed_point(carrier_body_point, pose)
            direct_transform_point = transform_level1_point_to_road(transform, carrier_local)
            if (
                _max_difference(carrier_road.position_m, direct_transform_point)
                > cfg.point_match_tolerance_m
            ):
                raise WUFRStaticCarrierWrenchError(
                    WUFRStaticCarrierWrenchFailureCode.TRANSFORM_FAILURE,
                    f"{corner_id} reviewed placement chains disagree",
                )

            mass = masses[corner_id]
            if (
                mass.configuration_id != provider.source.configuration_id
                or mass.assumption_id != "ASM-VEH-0003"
                or not math.isclose(mass.mass_kg, 5.0, rel_tol=0.0, abs_tol=1.0e-12)
            ):
                raise WUFRStaticCarrierWrenchError(
                    WUFRStaticCarrierWrenchFailureCode.GRAVITY_SOURCE_MISMATCH,
                    f"{corner_id} unsprung gravity source is not the reviewed 5 kg prototype allocation",
                )

            road_wrench, gravity_wrench, resultant = compose_static_carrier_point_wrenches(
                corner_id=corner_id,
                road_frame_id=road.frame_id,
                road_origin_id=road.origin_id,
                configuration_id=provider.source.configuration_id,
                contact_point=road_state.contact_road,
                wheel_center=road_state.wheel_center_road,
                carrier_reference=carrier_road,
                road_reaction_N=accepted.road_reactions_N[index],
                road_normal=road.normal,
                unsprung_force_N=mass.force_N(equilibrium.gravity.g_mps2),
                road_source_id=equilibrium.source.record_id,
                gravity_source_id=equilibrium.gravity.record_id,
            )

            local_force, local_moment = pullback_road_wrench_to_level1(
                transform,
                resultant.resultant_force_N,
                resultant.resultant_moment_Nm,
            )
            level1_wrench = CompleteCarrierWrench(
                frame_id=provider.source.level1_frame_id,
                reference_point_m=carrier_local,
                force_N=local_force,
                moment_Nm=local_moment,
                source_id=provider.source.record_id,
                load_case_id=(
                    f"{provider.source.static_state_id}:ARB_"
                    f"{accepted.front_arb_setting}_{accepted.rear_arb_setting}:{corner_id}"
                ),
                complete=True,
            )
            round_force, round_moment = pushforward_level1_wrench_to_road(
                transform, local_force, local_moment
            )
            force_residual = _max_difference(
                round_force, resultant.resultant_force_N
            )
            moment_residual = _max_difference(
                round_moment, resultant.resultant_moment_Nm
            )
            if (
                force_residual > cfg.wrench_transport_tolerance_N
                or moment_residual > cfg.wrench_transport_tolerance_Nm
            ):
                raise WUFRStaticCarrierWrenchError(
                    WUFRStaticCarrierWrenchFailureCode.ROUND_TRIP_FAILURE,
                    f"{corner_id} road/Level-1 wrench round trip exceeds tolerance",
                )

            road_representation = CarrierWrenchRepresentation(
                frame_id=road.frame_id,
                origin_id=road.origin_id,
                reference_point_id=carrier_road.point_id,
                reference_point_m=carrier_road.position_m,
                force_N=resultant.resultant_force_N,
                moment_Nm=resultant.resultant_moment_Nm,
            )
            corners.append(
                WUFRStaticCarrierCornerResult(
                    WUFRStaticCarrierWrenchStatus.SUCCESS,
                    corner_id,
                    axle_name,
                    side_name,
                    provider.source.configuration_id,
                    provider.source.static_state_id,
                    road_reaction_N=accepted.road_reactions_N[index],
                    road_normal=road.normal,
                    contact_point_road=road_state.contact_road,
                    wheel_center_road=road_state.wheel_center_road,
                    upper_spherical_level1_m=upper,
                    lower_spherical_level1_m=lower,
                    carrier_reference_level1_m=carrier_local,
                    carrier_reference_source_m=carrier_source,
                    carrier_reference_body_m=carrier_body,
                    carrier_reference_road=carrier_road,
                    frame_transform=transform,
                    road_force_wrench=road_wrench,
                    unsprung_gravity_wrench=gravity_wrench,
                    road_resultant=resultant,
                    road_representation=road_representation,
                    level1_wrench=level1_wrench,
                    round_trip_force_residual_N=force_residual,
                    round_trip_moment_residual_Nm=moment_residual,
                    complete_for_authorized_static_gravity_case=True,
                    complete_physical_hardware_wrench=False,
                    maneuver_complete=False,
                    installed_as_built_authority=False,
                    message="Complete external carrier wrench for the authorized static-gravity model only",
                )
            )
        except WUFRStaticCarrierWrenchError as exc:
            corners.append(
                WUFRStaticCarrierCornerResult(
                    WUFRStaticCarrierWrenchStatus.FAILURE,
                    corner_id,
                    axle_name,
                    side_name,
                    provider.source.configuration_id,
                    provider.source.static_state_id,
                    failure_code=exc.code,
                    message=str(exc),
                )
            )
            return _failure(provider, exc.code, str(exc), corners=corners)
        except Exception as exc:  # provider failures stay structured at this boundary
            message = f"{corner_id} carrier-wrench provider failed: {type(exc).__name__}: {exc}"
            corners.append(
                WUFRStaticCarrierCornerResult(
                    WUFRStaticCarrierWrenchStatus.FAILURE,
                    corner_id,
                    axle_name,
                    side_name,
                    provider.source.configuration_id,
                    provider.source.static_state_id,
                    failure_code=WUFRStaticCarrierWrenchFailureCode.WRENCH_COMPOSITION_FAILURE,
                    message=message,
                )
            )
            return _failure(
                provider,
                WUFRStaticCarrierWrenchFailureCode.WRENCH_COMPOSITION_FAILURE,
                message,
                corners=corners,
            )

    road_origin = PointReference(
        point_id="wufr_static_carrier_reconstruction_road_origin",
        frame_id=road.frame_id,
        origin_id=road.origin_id,
        position_m=(0.0, 0.0, 0.0),
        role="AUTH-VEH-0011 road-origin reconstruction reference",
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
        authority=REQUIRED_AUTHORIZATION_ID,
        fixed_role="road_fixed",
    )
    body_origin = PointReference(
        point_id="wufr_static_carrier_reconstruction_body_origin",
        frame_id=road.frame_id,
        origin_id=road.origin_id,
        position_m=_add(pose.body_origin_position_m, (0.0, 0.0, pose.z_s_m)),
        role="AUTH-VEH-0011 current body-origin reconstruction reference",
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
        authority=REQUIRED_AUTHORIZATION_ID,
        fixed_role="road_expressed_body_fixed",
    )
    reconstruction_wrenches: list[AppliedWrench] = []
    for corner in corners:
        assert corner.road_resultant is not None and corner.carrier_reference_road is not None
        reconstruction_wrenches.append(
            AppliedWrench(
                wrench_id=f"{corner.corner_id}_carrier_external_resultant",
                frame_id=road.frame_id,
                origin_id=road.origin_id,
                application_point=corner.carrier_reference_road,
                force_N=corner.road_resultant.resultant_force_N,
                free_couple_Nm=corner.road_resultant.resultant_moment_Nm,
                source_id=provider.source.record_id,
                authority="AUTH-VEH-0011 reconstructed carrier-boundary external load",
            )
        )
    sprung_body = equilibrium.gravity.sprung_body_point_reference(
        body_frame_id=pose.body_frame_id,
        body_origin_id=pose.body_origin_id,
    )
    sprung_road = transport_body_fixed_point(sprung_body, pose)
    reconstruction_wrenches.append(
        AppliedWrench(
            wrench_id="sprung_body_gravity",
            frame_id=road.frame_id,
            origin_id=road.origin_id,
            application_point=sprung_road,
            force_N=equilibrium.gravity.sprung.force_N(equilibrium.gravity.g_mps2),
            source_id=equilibrium.gravity.record_id,
            authority="AUTH-VEH-0005 sprung gravity",
        )
    )
    at_road_origin = assemble_wrenches(reconstruction_wrenches, road_origin)
    at_body_origin = assemble_wrenches(reconstruction_wrenches, body_origin)
    force_residual = max(abs(value) for value in at_body_origin.resultant_force_N)
    moment_residual = max(abs(value) for value in at_body_origin.resultant_moment_Nm)
    force_match = _max_difference(
        at_road_origin.resultant_force_N, accepted.physical_closure_force_N
    )
    moment_match = _max_difference(
        at_road_origin.resultant_moment_Nm, accepted.physical_closure_moment_Nm
    )
    if (
        force_residual > cfg.four_corner_force_reconstruction_tolerance_N
        or moment_residual > cfg.four_corner_moment_reconstruction_tolerance_Nm
        or force_match > cfg.accepted_closure_match_tolerance_N
        or moment_match > cfg.accepted_closure_match_tolerance_Nm
    ):
        return WUFRStaticCarrierWrenchResult(
            WUFRStaticCarrierWrenchStatus.FAILURE,
            provider.source.result_label,
            provider.source.authorization_id,
            provider.source.model_id,
            provider.source.configuration_id,
            provider.source.static_state_id,
            accepted.source_path,
            corners=tuple(corners),
            reconstruction_at_road_origin=at_road_origin,
            reconstruction_at_body_origin=at_body_origin,
            accepted_closure_force_N=accepted.physical_closure_force_N,
            accepted_closure_moment_Nm=accepted.physical_closure_moment_Nm,
            maximum_force_residual_N=force_residual,
            maximum_moment_residual_Nm=moment_residual,
            accepted_force_match_residual_N=force_match,
            accepted_moment_match_residual_Nm=moment_match,
            complete_for_authorized_static_gravity_case=False,
            complete_physical_hardware_wrench=False,
            maneuver_complete=False,
            installed_as_built_authority=False,
            integrated_level1_linkage_result_authority=False,
            historical_scale_reconstruction_used=False,
            hidden_balancing_wrench_used=False,
            failure_code=WUFRStaticCarrierWrenchFailureCode.RECONSTRUCTION_FAILURE,
            message="Four-corner carrier-boundary reconstruction exceeds AUTH-VEH-0011 tolerance",
        )
    return WUFRStaticCarrierWrenchResult(
        WUFRStaticCarrierWrenchStatus.SUCCESS,
        provider.source.result_label,
        provider.source.authorization_id,
        provider.source.model_id,
        provider.source.configuration_id,
        provider.source.static_state_id,
        accepted.source_path,
        corners=tuple(corners),
        reconstruction_at_road_origin=at_road_origin,
        reconstruction_at_body_origin=at_body_origin,
        accepted_closure_force_N=accepted.physical_closure_force_N,
        accepted_closure_moment_Nm=accepted.physical_closure_moment_Nm,
        maximum_force_residual_N=force_residual,
        maximum_moment_residual_Nm=moment_residual,
        accepted_force_match_residual_N=force_match,
        accepted_moment_match_residual_Nm=moment_match,
        complete_for_authorized_static_gravity_case=True,
        complete_physical_hardware_wrench=False,
        maneuver_complete=False,
        installed_as_built_authority=False,
        integrated_level1_linkage_result_authority=False,
        historical_scale_reconstruction_used=False,
        hidden_balancing_wrench_used=False,
        message="Four source-preserving static carrier external wrenches verified",
    )
