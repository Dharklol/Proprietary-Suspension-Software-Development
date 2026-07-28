"""Source-preserving WUFR static-gravity equilibrium composition.

Implements ``AUTH-VEH-0009`` / ``MOD-VEH-0007`` by composing the already
reviewed road-compatibility, gravity, spring, Z-bar, force-coordinate, and
provider-neutral quasi-static modules.  The implementation adds no component
force law and no alternate equilibrium solver.

Every successful result is explicitly labelled
``uncorrelated_design_intent_static_gravity``.  It is not an installed/as-built
corner-weight prediction, a setup recommendation, a maneuver load case, or a
structural boundary-condition packet.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Sequence

from pssd_suspension import (
    PhysicalStateSolverConfig,
    RockerWheelDerivativeConfig,
    SpringStateResult,
    WufrSpringPackage,
    ZBarAxleFixture,
    ZBarWheelStateResult,
    build_nominal_wheel_reference,
    evaluate_spring_from_actuation,
    load_wufr27_spring_package,
    load_wufr_zbar_fixture,
    solve_wufr_zbar_wheel_state,
)

from .force_coordinates import (
    AppliedWrench,
    BodyPose,
    PointReference,
    ResultantWrench,
    assemble_wrenches,
    transport_body_fixed_point,
)
from .quasi_static import (
    BodyExternalGeneralizedForceState,
    CompatibilityState,
    ContactRecoveryResult,
    EnergyGradientCheckResult,
    QuasiStaticFailureCode,
    QuasiStaticSolveResult,
    QuasiStaticSolverConfig,
    QuasiStaticStatus,
    SuspensionGeneralizedForceState,
    check_total_potential_gradient,
    recover_active_contact_normal_reactions,
    solve_quasi_static_equilibrium,
)
from .wufr_gravity import WUFRStaticGravityAllocation, load_wufr_static_gravity_allocation
from .wufr_road_contact import (
    CORNER_ORDER,
    WUFRRoadContactEvaluation,
    WUFRRoadContactProvider,
    WUFRRoadContactStatus,
    evaluate_body_to_wheel_jacobian,
    evaluate_wufr_road_contact,
    load_wufr_road_contact_provider,
    solve_road_compatibility,
)


Vector3 = tuple[float, float, float]
Vector4 = tuple[float, float, float, float]
BODY_ORDER = ("z_s_m", "phi_rad", "theta_rad")
BODY_UNITS = ("m", "rad", "rad")
WHEEL_UNITS = ("m", "m", "m", "m")
REQUIRED_RECORD_ID = "WUFR27_STATIC_EQUILIBRIUM_COMPOSITION_V0"
REQUIRED_CONFIGURATION_ID = "WUFR27_SUSPENSION_BASELINE_V0"
REQUIRED_AUTHORIZATION_ID = "AUTH-VEH-0009"
REQUIRED_MODEL_ID = "MOD-VEH-0007"
RESULT_LABEL = "uncorrelated_design_intent_static_gravity"


class WUFRStaticEquilibriumStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WUFRStaticEquilibriumFailureCode(str, Enum):
    SOURCE_MISMATCH = "source_mismatch"
    NONFINITE_INPUT = "nonfinite_input"
    INVALID_ARB_SETTING = "invalid_arb_setting"
    COMPATIBILITY_FAILURE = "compatibility_failure"
    SUSPENSION_FAILURE = "suspension_failure"
    BODY_EXTERNAL_FAILURE = "body_external_failure"
    EQUILIBRIUM_FAILURE = "equilibrium_failure"
    CONTACT_RECOVERY_FAILURE = "contact_recovery_failure"
    ENERGY_GRADIENT_FAILURE = "energy_gradient_failure"
    PHYSICAL_CLOSURE_FAILURE = "physical_closure_failure"


class WUFRStaticEquilibriumError(ValueError):
    def __init__(self, code: WUFRStaticEquilibriumFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WUFRStaticEquilibriumSource:
    record_id: str
    configuration_id: str
    static_state_id: str
    authorization_id: str
    model_id: str
    result_label: str
    body_order: tuple[str, str, str]
    wheel_order: tuple[str, str, str, str]
    explicit_front_setting_required: bool
    explicit_rear_setting_required: bool
    default_setting_authorized: bool
    interpolation_authorized: bool
    installed_as_built_authority: bool
    physical_correlation_authority: bool
    carrier_wrench_authority: bool
    structural_load_case_authority: bool


@dataclass(frozen=True)
class WUFRStaticEquilibriumConfig:
    physical_force_residual_tolerance_N: float = 1.0e-6
    physical_moment_residual_tolerance_Nm: float = 1.0e-6
    wheel_equilibrium_residual_tolerance_N: float = 1.0e-8
    energy_gradient_absolute_tolerance: float = 2.0
    energy_gradient_step_multipliers: tuple[float, float] = (1.0e-5, 5.0e-6)

    def __post_init__(self) -> None:
        values = (
            self.physical_force_residual_tolerance_N,
            self.physical_moment_residual_tolerance_Nm,
            self.wheel_equilibrium_residual_tolerance_N,
            self.energy_gradient_absolute_tolerance,
            *self.energy_gradient_step_multipliers,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise WUFRStaticEquilibriumError(
                WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
                "Static-equilibrium tolerances and energy steps must be finite and positive",
            )
        if len(self.energy_gradient_step_multipliers) < 2:
            raise WUFRStaticEquilibriumError(
                WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
                "At least two energy-gradient step multipliers are required",
            )


@dataclass(frozen=True)
class WUFRStaticEquilibriumProvider:
    source: WUFRStaticEquilibriumSource
    road_contact: WUFRRoadContactProvider
    gravity: WUFRStaticGravityAllocation
    spring_package: WufrSpringPackage
    front_zbar_fixture: ZBarAxleFixture
    rear_zbar_fixture: ZBarAxleFixture
    physical_solver: PhysicalStateSolverConfig
    rocker_derivative: RockerWheelDerivativeConfig
    quasi_static_config: QuasiStaticSolverConfig
    config: WUFRStaticEquilibriumConfig

    def nominal_body_pose(self) -> BodyPose:
        return self.road_contact.nominal_body_pose()


@dataclass(frozen=True)
class WUFRSuspensionCompositionResult:
    status: WUFRStaticEquilibriumStatus
    wheel_coordinates_m: Vector4
    front_arb_setting: int
    rear_arb_setting: int
    generalized_spring_force_N: Vector4 = ()  # type: ignore[assignment]
    generalized_arb_force_N: Vector4 = ()  # type: ignore[assignment]
    generalized_suspension_force_N: Vector4 = ()  # type: ignore[assignment]
    spring_energy_J: float | None = None
    arb_energy_J: float | None = None
    stored_energy_J: float | None = None
    spring_states: tuple[SpringStateResult, ...] = ()
    front_arb_state: ZBarWheelStateResult | None = None
    rear_arb_state: ZBarWheelStateResult | None = None
    failure_code: WUFRStaticEquilibriumFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticEquilibriumStatus.SUCCESS


@dataclass(frozen=True)
class WUFRPhysicalClosureResult:
    status: WUFRStaticEquilibriumStatus
    resultant: ResultantWrench | None = None
    maximum_force_residual_N: float | None = None
    maximum_moment_residual_Nm: float | None = None
    failure_code: WUFRStaticEquilibriumFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticEquilibriumStatus.SUCCESS


@dataclass(frozen=True)
class WUFRStaticEquilibriumResult:
    status: WUFRStaticEquilibriumStatus
    front_arb_setting: int
    rear_arb_setting: int
    result_label: str = RESULT_LABEL
    solve: QuasiStaticSolveResult | None = None
    suspension: WUFRSuspensionCompositionResult | None = None
    road_contact: WUFRRoadContactEvaluation | None = None
    contact_recovery: ContactRecoveryResult | None = None
    energy_gradient: EnergyGradientCheckResult | None = None
    physical_closure: WUFRPhysicalClosureResult | None = None
    complete_static_road_reaction: bool = False
    installed_as_built_authority: bool = False
    historical_scale_reconstruction_used: bool = False
    failure_code: WUFRStaticEquilibriumFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is WUFRStaticEquilibriumStatus.SUCCESS



def _finite(values: Sequence[float]) -> bool:
    return all(math.isfinite(float(value)) for value in values)



def _valid_setting(value: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5



def _pose_from_q(provider: WUFRStaticEquilibriumProvider, q_body: Sequence[float]) -> BodyPose:
    q = tuple(float(value) for value in q_body)
    if len(q) != 3 or not _finite(q):
        raise WUFRStaticEquilibriumError(
            WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
            "Body state must contain finite [z_s, phi, theta] coordinates",
        )
    return replace(provider.nominal_body_pose(), z_s_m=q[0], phi_rad=q[1], theta_rad=q[2])



def load_wufr_static_equilibrium_source(path: str | Path) -> WUFRStaticEquilibriumSource:
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)
    coordinate = document.get("coordinate_contract", {})
    arb = document.get("source", {}).get("anti_roll_bar", {})
    boundaries = document.get("boundaries", {})
    source = WUFRStaticEquilibriumSource(
        record_id=str(document.get("record_id", "")),
        configuration_id=str(document.get("configuration_id", "")),
        static_state_id=str(document.get("static_state_id", "")),
        authorization_id=str(document.get("authorization_id", "")),
        model_id=str(document.get("model_id", "")),
        result_label=str(document.get("result_label", "")),
        body_order=tuple(str(value) for value in coordinate.get("body_order", ())),  # type: ignore[arg-type]
        wheel_order=tuple(str(value) for value in coordinate.get("wheel_order", ())),  # type: ignore[arg-type]
        explicit_front_setting_required=bool(arb.get("explicit_front_setting_required", False)),
        explicit_rear_setting_required=bool(arb.get("explicit_rear_setting_required", False)),
        default_setting_authorized=bool(arb.get("default_setting_authorized", True)),
        interpolation_authorized=bool(arb.get("interpolation_authorized", True)),
        installed_as_built_authority=bool(boundaries.get("installed_as_built_authority", True)),
        physical_correlation_authority=bool(boundaries.get("physical_correlation_authority", True)),
        carrier_wrench_authority=bool(boundaries.get("carrier_wrench_authority", True)),
        structural_load_case_authority=bool(boundaries.get("structural_load_case_authority", True)),
    )
    if (
        source.record_id != REQUIRED_RECORD_ID
        or source.configuration_id != REQUIRED_CONFIGURATION_ID
        or source.authorization_id != REQUIRED_AUTHORIZATION_ID
        or source.model_id != REQUIRED_MODEL_ID
        or source.result_label != RESULT_LABEL
        or source.body_order != BODY_ORDER
        or source.wheel_order != CORNER_ORDER
        or not source.explicit_front_setting_required
        or not source.explicit_rear_setting_required
        or source.default_setting_authorized
        or source.interpolation_authorized
        or source.installed_as_built_authority
        or source.physical_correlation_authority
        or source.carrier_wrench_authority
        or source.structural_load_case_authority
    ):
        raise WUFRStaticEquilibriumError(
            WUFRStaticEquilibriumFailureCode.SOURCE_MISMATCH,
            "Static-equilibrium source record does not match AUTH-VEH-0009 boundaries",
        )
    return source



def default_wufr_quasi_static_config(
    road_contact: WUFRRoadContactProvider,
    gravity: WUFRStaticGravityAllocation,
) -> QuasiStaticSolverConfig:
    total_weight = gravity.total_mass_kg * gravity.g_mps2
    roll_scale = total_weight * max(road_contact.whole_vehicle.front_track_m, road_contact.whole_vehicle.rear_track_m) * 0.5
    pitch_scale = total_weight * road_contact.whole_vehicle.wheelbase_m * 0.5
    cfg = road_contact.config
    return QuasiStaticSolverConfig(
        coordinate_scales=(0.005, 0.005, 0.005),
        residual_scales=(total_weight, roll_scale, pitch_scale),
        lower_bounds=(-cfg.body_z_limit_m, -cfg.body_roll_limit_rad, -cfg.body_pitch_limit_rad),
        upper_bounds=(cfg.body_z_limit_m, cfg.body_roll_limit_rad, cfg.body_pitch_limit_rad),
        residual_absolute_tolerance=1.0e-10,
        residual_relative_tolerance=1.0e-10,
        max_iterations=30,
        finite_difference_relative_step=2.0e-4,
        finite_difference_min_step=1.0e-7,
        line_search_reduction=0.5,
        line_search_max_trials=16,
        minimum_reciprocal_pivot_ratio=1.0e-11,
        pivot_absolute_tolerance=1.0e-14,
    )



def load_wufr_static_equilibrium_provider(
    *,
    source_path: str | Path,
    road_contact_source_path: str | Path,
    suspension_geometry_path: str | Path,
    wheel_profile_path: str | Path,
    steering_geometry_path: str | Path,
    whole_vehicle_path: str | Path,
    gravity_path: str | Path,
    spring_package_path: str | Path,
    zbar_fixture_path: str | Path,
    road_contact_config=None,
    rocker_derivative: RockerWheelDerivativeConfig | None = None,
    quasi_static_config: QuasiStaticSolverConfig | None = None,
    config: WUFRStaticEquilibriumConfig | None = None,
) -> WUFRStaticEquilibriumProvider:
    source = load_wufr_static_equilibrium_source(source_path)
    road_contact = load_wufr_road_contact_provider(
        source_path=road_contact_source_path,
        suspension_geometry_path=suspension_geometry_path,
        wheel_profile_path=wheel_profile_path,
        steering_geometry_path=steering_geometry_path,
        whole_vehicle_path=whole_vehicle_path,
        config=road_contact_config,
    )
    gravity = load_wufr_static_gravity_allocation(gravity_path)
    spring_package = load_wufr27_spring_package(spring_package_path)
    front_fixture = load_wufr_zbar_fixture(zbar_fixture_path, "front")
    rear_fixture = load_wufr_zbar_fixture(zbar_fixture_path, "rear")
    identities = (
        road_contact.source.configuration_id,
        gravity.configuration_id,
        spring_package.configuration_id,
        front_fixture.configuration_id,
        rear_fixture.configuration_id,
    )
    if any(value != source.configuration_id for value in identities):
        raise WUFRStaticEquilibriumError(
            WUFRStaticEquilibriumFailureCode.SOURCE_MISMATCH,
            "Road contact, gravity, spring, Z-bar, and composition configuration IDs must match",
        )
    derivative = rocker_derivative or RockerWheelDerivativeConfig(
        step_m=1.0e-4,
        second_step_m=5.0e-5,
        agreement_tolerance_rad_per_m=5.0e-2,
    )
    physical_solver = road_contact.config.physical_state_solver
    solver = quasi_static_config or default_wufr_quasi_static_config(road_contact, gravity)
    return WUFRStaticEquilibriumProvider(
        source=source,
        road_contact=road_contact,
        gravity=gravity,
        spring_package=spring_package,
        front_zbar_fixture=front_fixture,
        rear_zbar_fixture=rear_fixture,
        physical_solver=physical_solver,
        rocker_derivative=derivative,
        quasi_static_config=solver,
        config=config or WUFRStaticEquilibriumConfig(),
    )



def _solve_axle(
    provider: WUFRStaticEquilibriumProvider,
    axle: str,
    z_left: float,
    z_right: float,
    setting: int,
) -> ZBarWheelStateResult:
    geometry = provider.road_contact.suspension_geometry
    profile = provider.road_contact.wheel_profile
    fixture = provider.front_zbar_fixture if axle == "front" else provider.rear_zbar_fixture
    return solve_wufr_zbar_wheel_state(
        fixture,
        geometry.corner(axle, "left"),
        geometry.corner(axle, "right"),
        build_nominal_wheel_reference(profile, axle, "left"),
        build_nominal_wheel_reference(profile, axle, "right"),
        z_left,
        z_right,
        provider.physical_solver,
        setting=setting,
        derivative_config=provider.rocker_derivative,
        geometry_id=geometry.geometry_id,
        configuration_id=provider.source.configuration_id,
        source_authority=geometry.authority,
        with_wheel_jacobian=True,
    )



def evaluate_wufr_suspension_composition(
    provider: WUFRStaticEquilibriumProvider,
    wheel_coordinates_m: Sequence[float],
    *,
    front_arb_setting: int,
    rear_arb_setting: int,
) -> WUFRSuspensionCompositionResult:
    z = tuple(float(value) for value in wheel_coordinates_m)
    if len(z) != 4 or not _finite(z):
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            failure_code=WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
            message="Four finite physical wheel coordinates are required",
        )
    if not _valid_setting(front_arb_setting) or not _valid_setting(rear_arb_setting):
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            failure_code=WUFRStaticEquilibriumFailureCode.INVALID_ARB_SETTING,
            message="Front and rear ARB settings must be explicit integers in 1..5",
        )
    front = _solve_axle(provider, "front", z[0], z[1], front_arb_setting)
    rear = _solve_axle(provider, "rear", z[2], z[3], rear_arb_setting)
    if not front.ok or not rear.ok:
        failed = front if not front.ok else rear
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            front_arb_state=front,
            rear_arb_state=rear,
            failure_code=WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message=failed.message or "WUFR Z-bar physical-wheel-coordinate provider failed",
        )

    maps = (front.left_map, front.right_map, rear.left_map, rear.right_map)
    if any(item is None or item.actuation_state is None for item in maps):
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            front_arb_state=front,
            rear_arb_state=rear,
            failure_code=WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message="Successful Z-bar states must retain all four source-owned actuation states",
        )

    definitions = (
        provider.spring_package.front,
        provider.spring_package.front,
        provider.spring_package.rear,
        provider.spring_package.rear,
    )
    spring_states = tuple(
        evaluate_spring_from_actuation(
            definition,
            provider.spring_package.reference,
            mapping.actuation_state,  # type: ignore[union-attr]
        )
        for definition, mapping in zip(definitions, maps)
    )
    failed_spring = next((item for item in spring_states if not item.ok), None)
    if failed_spring is not None:
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            spring_states=spring_states,
            front_arb_state=front,
            rear_arb_state=rear,
            failure_code=WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message=failed_spring.message or "WUFR spring provider failed",
        )
    if any(
        not item.generalized_force_available
        or len(item.generalized_force) != 1
        or item.stored_energy_J is None
        for item in spring_states
    ):
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            spring_states=spring_states,
            front_arb_state=front,
            rear_arb_state=rear,
            failure_code=WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message="Each spring state must provide one signed physical-wheel generalized force and energy",
        )
    if (
        len(front.generalized_wheel_force_N) != 2
        or len(rear.generalized_wheel_force_N) != 2
        or front.force is None
        or rear.force is None
        or front.force.stored_energy_J is None
        or rear.force.stored_energy_J is None
    ):
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            spring_states=spring_states,
            front_arb_state=front,
            rear_arb_state=rear,
            failure_code=WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message="Front/rear Z-bar states must provide two generalized forces and stored energy",
        )

    q_spring = tuple(float(item.generalized_force[0]) for item in spring_states)
    q_arb = tuple((*front.generalized_wheel_force_N, *rear.generalized_wheel_force_N))
    q_total = tuple(q_spring[i] + q_arb[i] for i in range(4))
    spring_energy = sum(float(item.stored_energy_J) for item in spring_states)
    arb_energy = float(front.force.stored_energy_J) + float(rear.force.stored_energy_J)
    if not _finite((*q_spring, *q_arb, *q_total, spring_energy, arb_energy)):
        return WUFRSuspensionCompositionResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            z,  # type: ignore[arg-type]
            front_arb_setting,
            rear_arb_setting,
            spring_states=spring_states,
            front_arb_state=front,
            rear_arb_state=rear,
            failure_code=WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
            message="Composed suspension force or energy is nonfinite",
        )
    return WUFRSuspensionCompositionResult(
        WUFRStaticEquilibriumStatus.SUCCESS,
        z,  # type: ignore[arg-type]
        front_arb_setting,
        rear_arb_setting,
        generalized_spring_force_N=q_spring,  # type: ignore[arg-type]
        generalized_arb_force_N=q_arb,  # type: ignore[arg-type]
        generalized_suspension_force_N=q_total,  # type: ignore[arg-type]
        spring_energy_J=spring_energy,
        arb_energy_J=arb_energy,
        stored_energy_J=spring_energy + arb_energy,
        spring_states=spring_states,
        front_arb_state=front,
        rear_arb_state=rear,
    )



def _compatibility_state(
    provider: WUFRStaticEquilibriumProvider,
    q_body: Sequence[float],
) -> CompatibilityState:
    try:
        pose = _pose_from_q(provider, q_body)
        compatibility = solve_road_compatibility(provider.road_contact, pose)
        if not compatibility.ok or compatibility.wheel_coordinates_m is None:
            return CompatibilityState(
                QuasiStaticStatus.FAILURE,
                source_id=provider.road_contact.source.record_id,
                configuration_id=provider.source.configuration_id,
                failure_code=QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
                message=compatibility.message or "WUFR road compatibility failed",
            )
        jacobian = evaluate_body_to_wheel_jacobian(provider.road_contact, pose)
        if not jacobian.ok or jacobian.jacobian is None:
            return CompatibilityState(
                QuasiStaticStatus.FAILURE,
                source_id=provider.road_contact.source.record_id,
                configuration_id=provider.source.configuration_id,
                failure_code=QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
                message=jacobian.message or "WUFR road-compatible body Jacobian failed",
            )
        return CompatibilityState(
            QuasiStaticStatus.SUCCESS,
            wheel_coordinates=compatibility.wheel_coordinates_m,
            J_wb=jacobian.jacobian,
            wheel_coordinate_order=CORNER_ORDER,
            wheel_coordinate_units=WHEEL_UNITS,
            source_id=provider.road_contact.source.record_id,
            configuration_id=provider.source.configuration_id,
        )
    except Exception as exc:
        return CompatibilityState(
            QuasiStaticStatus.FAILURE,
            source_id=provider.road_contact.source.record_id,
            configuration_id=provider.source.configuration_id,
            failure_code=QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
            message=f"WUFR compatibility adapter raised {type(exc).__name__}: {exc}",
        )



def _suspension_state(
    provider: WUFRStaticEquilibriumProvider,
    wheel_coordinates_m: Sequence[float],
    front_setting: int,
    rear_setting: int,
) -> SuspensionGeneralizedForceState:
    result = evaluate_wufr_suspension_composition(
        provider,
        wheel_coordinates_m,
        front_arb_setting=front_setting,
        rear_arb_setting=rear_setting,
    )
    if not result.ok:
        return SuspensionGeneralizedForceState(
            QuasiStaticStatus.FAILURE,
            coordinate_order=CORNER_ORDER,
            coordinate_units=WHEEL_UNITS,
            source_id=provider.source.record_id,
            configuration_id=provider.source.configuration_id,
            failure_code=QuasiStaticFailureCode.SUSPENSION_PROVIDER_FAILURE,
            message=result.message,
        )
    return SuspensionGeneralizedForceState(
        QuasiStaticStatus.SUCCESS,
        generalized_wheel_force=result.generalized_suspension_force_N,
        stored_energy_J=result.stored_energy_J,
        coordinate_order=CORNER_ORDER,
        coordinate_units=WHEEL_UNITS,
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
    )



def _body_external_state(
    provider: WUFRStaticEquilibriumProvider,
    q_body: Sequence[float],
) -> BodyExternalGeneralizedForceState:
    try:
        pose = _pose_from_q(provider, q_body)
        generalized = provider.gravity.sprung_body_generalized_gravity(pose)
        point_body = provider.gravity.sprung_body_point_reference(
            body_frame_id=pose.body_frame_id,
            body_origin_id=pose.body_origin_id,
        )
        point_road = transport_body_fixed_point(point_body, pose)
        potential = provider.gravity.sprung.mass_kg * provider.gravity.g_mps2 * point_road.position_m[2]
        return BodyExternalGeneralizedForceState(
            QuasiStaticStatus.SUCCESS,
            generalized_force=generalized.generalized_force,
            potential_energy_J=potential,
            coordinate_order=BODY_ORDER,
            coordinate_units=BODY_UNITS,
            source_id=provider.gravity.record_id,
            configuration_id=provider.source.configuration_id,
        )
    except Exception as exc:
        return BodyExternalGeneralizedForceState(
            QuasiStaticStatus.FAILURE,
            coordinate_order=BODY_ORDER,
            coordinate_units=BODY_UNITS,
            source_id=provider.gravity.record_id,
            configuration_id=provider.source.configuration_id,
            failure_code=QuasiStaticFailureCode.BODY_EXTERNAL_PROVIDER_FAILURE,
            message=f"WUFR sprung-gravity adapter raised {type(exc).__name__}: {exc}",
        )



def evaluate_wufr_physical_closure(
    provider: WUFRStaticEquilibriumProvider,
    pose: BodyPose,
    road_contact: WUFRRoadContactEvaluation,
    contact: ContactRecoveryResult,
) -> WUFRPhysicalClosureResult:
    if (
        not road_contact.ok
        or not contact.ok
        or len(road_contact.compatibility.roots) != 4
        or len(contact.normal_reaction_N) != 4
    ):
        return WUFRPhysicalClosureResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            failure_code=WUFRStaticEquilibriumFailureCode.PHYSICAL_CLOSURE_FAILURE,
            message="Converged road/contact states are required for physical closure",
        )
    road = provider.road_contact.road_plane(pose)
    reference = PointReference(
        point_id="wufr_static_equilibrium_road_origin",
        frame_id=road.frame_id,
        origin_id=road.origin_id,
        position_m=(0.0, 0.0, 0.0),
        role="physical_wrench_closure_reference",
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
        authority=REQUIRED_AUTHORIZATION_ID,
        fixed_role="road_fixed",
    )
    wrenches: list[AppliedWrench] = []
    for root, reaction in zip(road_contact.compatibility.roots, contact.normal_reaction_N):
        if root.state is None:
            return WUFRPhysicalClosureResult(
                WUFRStaticEquilibriumStatus.FAILURE,
                failure_code=WUFRStaticEquilibriumFailureCode.PHYSICAL_CLOSURE_FAILURE,
                message="Every road root must retain its exact contact and wheel-center points",
            )
        force = tuple(float(reaction) * component for component in road.normal)
        wrenches.append(
            AppliedWrench(
                wrench_id=f"{root.corner_id}_road_normal_reaction",
                frame_id=road.frame_id,
                origin_id=road.origin_id,
                application_point=root.state.contact_road,
                force_N=force,  # type: ignore[arg-type]
                source_id=provider.source.record_id,
                authority="AUTH-VEH-0009 recovered road reaction",
            )
        )
    sprung_body = provider.gravity.sprung_body_point_reference(
        body_frame_id=pose.body_frame_id,
        body_origin_id=pose.body_origin_id,
    )
    sprung_road = transport_body_fixed_point(sprung_body, pose)
    wrenches.append(
        AppliedWrench(
            wrench_id="sprung_body_gravity",
            frame_id=road.frame_id,
            origin_id=road.origin_id,
            application_point=sprung_road,
            force_N=provider.gravity.sprung.force_N(provider.gravity.g_mps2),
            source_id=provider.gravity.record_id,
            authority="AUTH-VEH-0005 sprung gravity",
        )
    )
    masses = {item.corner_id: item for item in provider.gravity.unsprung}
    for root in road_contact.compatibility.roots:
        if root.state is None or root.corner_id not in masses:
            return WUFRPhysicalClosureResult(
                WUFRStaticEquilibriumStatus.FAILURE,
                failure_code=WUFRStaticEquilibriumFailureCode.PHYSICAL_CLOSURE_FAILURE,
                message="Every corner requires its source-owned unsprung gravity mass and current wheel center",
            )
        mass = masses[root.corner_id]
        wrenches.append(
            AppliedWrench(
                wrench_id=f"{root.corner_id}_unsprung_gravity",
                frame_id=road.frame_id,
                origin_id=road.origin_id,
                application_point=root.state.wheel_center_road,
                force_N=mass.force_N(provider.gravity.g_mps2),
                source_id=provider.gravity.record_id,
                authority="AUTH-VEH-0005 prototype unsprung gravity",
            )
        )
    resultant = assemble_wrenches(wrenches, reference)
    force_residual = max(abs(value) for value in resultant.resultant_force_N)
    moment_residual = max(abs(value) for value in resultant.resultant_moment_Nm)
    if (
        force_residual > provider.config.physical_force_residual_tolerance_N
        or moment_residual > provider.config.physical_moment_residual_tolerance_Nm
    ):
        return WUFRPhysicalClosureResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            resultant=resultant,
            maximum_force_residual_N=force_residual,
            maximum_moment_residual_Nm=moment_residual,
            failure_code=WUFRStaticEquilibriumFailureCode.PHYSICAL_CLOSURE_FAILURE,
            message=(
                "Independent road-frame wrench closure exceeds AUTH-VEH-0009 tolerance: "
                f"force={force_residual:.6g} N, moment={moment_residual:.6g} N*m"
            ),
        )
    return WUFRPhysicalClosureResult(
        WUFRStaticEquilibriumStatus.SUCCESS,
        resultant=resultant,
        maximum_force_residual_N=force_residual,
        maximum_moment_residual_Nm=moment_residual,
    )



def solve_wufr_static_equilibrium(
    provider: WUFRStaticEquilibriumProvider,
    *,
    front_arb_setting: int,
    rear_arb_setting: int,
    initial_q_body: Sequence[float] = (0.0, 0.0, 0.0),
) -> WUFRStaticEquilibriumResult:
    if not _valid_setting(front_arb_setting) or not _valid_setting(rear_arb_setting):
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            failure_code=WUFRStaticEquilibriumFailureCode.INVALID_ARB_SETTING,
            message="Front and rear ARB settings are required explicit integer inputs in 1..5",
        )
    q0 = tuple(float(value) for value in initial_q_body)
    if len(q0) != 3 or not _finite(q0):
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            failure_code=WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
            message="Initial body state must contain three finite coordinates",
        )

    compatibility_provider = lambda q: _compatibility_state(provider, q)
    suspension_provider = lambda z: _suspension_state(provider, z, front_arb_setting, rear_arb_setting)
    body_external_provider = lambda q: _body_external_state(provider, q)
    solve = solve_quasi_static_equilibrium(
        q0,
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        config=provider.quasi_static_config,
    )
    if not solve.ok:
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            failure_code=WUFRStaticEquilibriumFailureCode.EQUILIBRIUM_FAILURE,
            message=solve.message or "WUFR reduced quasi-static equilibrium failed",
        )

    pose = _pose_from_q(provider, solve.q_body)
    road_contact = evaluate_wufr_road_contact(provider.road_contact, pose, provider.gravity)
    if (
        not road_contact.ok
        or road_contact.compatibility.wheel_coordinates_m is None
        or any(item.value is None for item in road_contact.contact_coefficients)
        or any(item.value is None for item in road_contact.unsprung_gravity_forces)
    ):
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            road_contact=road_contact,
            failure_code=WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
            message=road_contact.message or "Final WUFR road/contact evaluation failed",
        )
    suspension = evaluate_wufr_suspension_composition(
        provider,
        road_contact.compatibility.wheel_coordinates_m,
        front_arb_setting=front_arb_setting,
        rear_arb_setting=rear_arb_setting,
    )
    if not suspension.ok:
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            failure_code=WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message=suspension.message,
        )
    suspension_state = SuspensionGeneralizedForceState(
        QuasiStaticStatus.SUCCESS,
        generalized_wheel_force=suspension.generalized_suspension_force_N,
        stored_energy_J=suspension.stored_energy_J,
        coordinate_order=CORNER_ORDER,
        coordinate_units=WHEEL_UNITS,
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
    )
    contact = recover_active_contact_normal_reactions(
        suspension_state,
        wheel_external_generalized_force=tuple(
            float(item.value) for item in road_contact.unsprung_gravity_forces
        ),
        contact_coefficients=tuple(float(item.value) for item in road_contact.contact_coefficients),
    )
    if not contact.ok or any(
        abs(value) > provider.config.wheel_equilibrium_residual_tolerance_N
        for value in contact.wheel_equilibrium_residual
    ):
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            contact_recovery=contact,
            failure_code=WUFRStaticEquilibriumFailureCode.CONTACT_RECOVERY_FAILURE,
            message=contact.message or "Wheel/contact equilibrium residual exceeds tolerance",
        )

    energy = check_total_potential_gradient(
        solve.q_body,
        body_coordinate_order=BODY_ORDER,
        body_coordinate_units=BODY_UNITS,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        config=provider.quasi_static_config,
        relative_step_multipliers=provider.config.energy_gradient_step_multipliers,
        absolute_tolerance=provider.config.energy_gradient_absolute_tolerance,
    )
    if not energy.ok:
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            contact_recovery=contact,
            energy_gradient=energy,
            failure_code=WUFRStaticEquilibriumFailureCode.ENERGY_GRADIENT_FAILURE,
            message=energy.message,
        )

    closure = evaluate_wufr_physical_closure(provider, pose, road_contact, contact)
    if not closure.ok:
        return WUFRStaticEquilibriumResult(
            WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            contact_recovery=contact,
            energy_gradient=energy,
            physical_closure=closure,
            failure_code=WUFRStaticEquilibriumFailureCode.PHYSICAL_CLOSURE_FAILURE,
            message=closure.message,
        )
    return WUFRStaticEquilibriumResult(
        WUFRStaticEquilibriumStatus.SUCCESS,
        front_arb_setting,
        rear_arb_setting,
        solve=solve,
        suspension=suspension,
        road_contact=road_contact,
        contact_recovery=contact,
        energy_gradient=energy,
        physical_closure=closure,
        complete_static_road_reaction=True,
        installed_as_built_authority=False,
        historical_scale_reconstruction_used=False,
        message="WUFR uncorrelated design-intent static-gravity equilibrium converged",
    )
