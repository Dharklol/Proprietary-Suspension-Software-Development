"""Coupled conservative anti-roll-bar energy and generalized-force provider.

Implements AUTH-SUSP-0005 / EQ-SUSP-0016 through EQ-SUSP-0018.

The provider keeps the elastic coordinate source-defined.  BENCH-SUSP-0011 uses
an explicit translational differential coordinate; the first WUFR adapter uses a
reviewer-selected reduced axle angular coordinate.  The WUFR ``K_phi`` values are
already reduced axle roll stiffness and must not receive a second motion-ratio
reduction.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Iterable, Sequence


class SuspensionAntiRollBarError(ValueError):
    """Raised for malformed ARB definitions, not ordinary unavailable states."""


class AntiRollBarStatus(str, Enum):
    SUCCESS = "success"
    NO_BAR = "no_bar"
    FAILURE = "failure"


class AntiRollBarFailureCode(str, Enum):
    NONFINITE_INPUT = "nonfinite_input"
    MISSING_BILATERAL_GEOMETRY_AUTHORITY = "missing_bilateral_geometry_authority"
    MECHANISM_CLOSURE_FAILURE = "mechanism_closure_failure"
    BRANCH_AMBIGUITY = "branch_ambiguity"
    MISSING_ZERO_PRELOAD_REFERENCE = "missing_zero_preload_reference"
    MISSING_STIFFNESS_AUTHORITY = "missing_stiffness_authority"
    CONSTITUTIVE_DOMAIN_EXCEEDED = "constitutive_domain_exceeded"
    JACOBIAN_UNAVAILABLE = "jacobian_unavailable"
    SOURCE_CONFIGURATION_MISMATCH = "source_configuration_mismatch"
    INVALID_ENERGY_LAW = "invalid_energy_law"


@dataclass(frozen=True)
class AntiRollBarDefinition:
    """Linear conservative ARB law in one explicitly named elastic coordinate.

    ``stiffness_action_per_coordinate`` is the slope of the action conjugate to
    the elastic coordinate.  Examples:

    - translational coordinate [m] -> action [N] -> stiffness [N/m];
    - angular coordinate [rad] -> action [N*m] -> stiffness [N*m/rad].

    Unit strings are provenance/contract metadata; this provider never silently
    converts an arbitrary coordinate between those classes.
    """

    arb_id: str
    axle: str
    stiffness_action_per_coordinate: float
    elastic_coordinate_unit: str
    elastic_action_unit: str
    source_id: str
    configuration_id: str
    assumption_ids: tuple[str, ...] = ()
    installed_as_built_authority: bool = False
    reduced_axle_level: bool = False
    source_stiffness_Nm_per_deg: float | None = None
    max_abs_deformation: float | None = None

    def __post_init__(self) -> None:
        if not self.arb_id or not self.axle or not self.source_id or not self.configuration_id:
            raise SuspensionAntiRollBarError("ARB identity, axle, source, and configuration are required")
        if not self.elastic_coordinate_unit or not self.elastic_action_unit:
            raise SuspensionAntiRollBarError("ARB elastic coordinate and action units are required")
        if not math.isfinite(self.stiffness_action_per_coordinate) or self.stiffness_action_per_coordinate <= 0.0:
            raise SuspensionAntiRollBarError("ARB stiffness must be finite and positive")
        if self.source_stiffness_Nm_per_deg is not None:
            if self.elastic_coordinate_unit != "rad" or self.elastic_action_unit != "N*m":
                raise SuspensionAntiRollBarError("N*m/deg source stiffness requires a radian / N*m reduced law")
            if not math.isfinite(self.source_stiffness_Nm_per_deg) or self.source_stiffness_Nm_per_deg <= 0.0:
                raise SuspensionAntiRollBarError("Source stiffness in N*m/deg must be finite and positive")
            expected = stiffness_Nm_per_deg_to_Nm_per_rad(self.source_stiffness_Nm_per_deg)
            if not math.isclose(self.stiffness_action_per_coordinate, expected, rel_tol=1.0e-12, abs_tol=1.0e-12):
                raise SuspensionAntiRollBarError("Stored SI ARB stiffness does not match the declared N*m/deg source value")
        if self.max_abs_deformation is not None:
            if not math.isfinite(self.max_abs_deformation) or self.max_abs_deformation <= 0.0:
                raise SuspensionAntiRollBarError("ARB deformation domain must be finite and positive when supplied")


@dataclass(frozen=True)
class AntiRollBarReference:
    reference_id: str
    configuration_id: str
    elastic_coordinate_unit: str
    zero_energy_coordinate: float = 0.0
    assumption_ids: tuple[str, ...] = ()
    installed_as_built_authority: bool = False

    def __post_init__(self) -> None:
        if not self.reference_id or not self.configuration_id or not self.elastic_coordinate_unit:
            raise SuspensionAntiRollBarError("ARB reference identity, configuration, and coordinate unit are required")
        if not math.isfinite(self.zero_energy_coordinate):
            raise SuspensionAntiRollBarError("ARB zero-energy reference coordinate must be finite")


@dataclass(frozen=True)
class AntiRollBarCoordinateResult:
    status: AntiRollBarStatus
    deformation: float | None = None
    current_coordinate: float | None = None
    reference_coordinate: float | None = None
    elastic_coordinate_unit: str = ""
    ds_dq: tuple[float, ...] = ()
    coordinate_order: tuple[str, ...] = ()
    coordinate_units: tuple[str, ...] = ()
    failure_code: AntiRollBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not AntiRollBarStatus.FAILURE


@dataclass(frozen=True)
class AntiRollBarConstitutiveResult:
    status: AntiRollBarStatus
    deformation: float | None = None
    elastic_action: float | None = None
    stored_energy_J: float | None = None
    tangent_stiffness: float | None = None
    elastic_coordinate_unit: str = ""
    elastic_action_unit: str = ""
    failure_code: AntiRollBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not AntiRollBarStatus.FAILURE


@dataclass(frozen=True)
class AntiRollBarStateResult:
    status: AntiRollBarStatus
    arb_id: str = ""
    axle: str = ""
    source_id: str = ""
    configuration_id: str = ""
    assumption_ids: tuple[str, ...] = ()
    enabled: bool = True
    reduced_axle_level: bool = False
    elastic_coordinate_unit: str = ""
    elastic_action_unit: str = ""
    current_coordinate: float | None = None
    reference_coordinate: float | None = None
    deformation: float | None = None
    elastic_action: float | None = None
    stored_energy_J: float | None = None
    tangent_stiffness: float | None = None
    coordinate_order: tuple[str, ...] = ()
    coordinate_units: tuple[str, ...] = ()
    ds_dq: tuple[float, ...] = ()
    generalized_force: tuple[float, ...] = ()
    generalized_force_available: bool = False
    installed_as_built_authority: bool = False
    failure_code: AntiRollBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not AntiRollBarStatus.FAILURE


@dataclass(frozen=True)
class AntiRollBarEnergyCheckResult:
    status: AntiRollBarStatus
    expected_generalized_force: float | None = None
    finite_difference_generalized_force: tuple[float, ...] = ()
    step_sizes: tuple[float, ...] = ()
    absolute_residuals: tuple[float, ...] = ()
    failure_code: AntiRollBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not AntiRollBarStatus.FAILURE


@dataclass(frozen=True)
class SymmetricDifferentialCoordinateResult:
    status: AntiRollBarStatus
    deformation_m: float | None = None
    ds_dz_left: float | None = None
    ds_dz_right: float | None = None
    failure_code: AntiRollBarFailureCode | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not AntiRollBarStatus.FAILURE


@dataclass(frozen=True)
class WufrAntiRollBarPackage:
    configuration_id: str
    source_record_id: str
    front: AntiRollBarDefinition
    rear: AntiRollBarDefinition
    reference: AntiRollBarReference
    source_front_stiffness_Nm_per_deg: float
    source_rear_stiffness_Nm_per_deg: float
    instron_status: str
    installed_as_built_authority: bool = False


def stiffness_Nm_per_deg_to_Nm_per_rad(value: float) -> float:
    """Convert a torque-per-degree slope to torque per radian."""
    if not math.isfinite(value):
        raise SuspensionAntiRollBarError("ARB stiffness conversion requires a finite value")
    return float(value) * 180.0 / math.pi


def symmetric_differential_coordinate(
    z_left_m: float,
    z_right_m: float,
    reference_offset_m: float = 0.0,
) -> SymmetricDifferentialCoordinateResult:
    """BENCH-SUSP-0011 map: s=z_L-z_R-s0 with J=[+1,-1].

    This is a synthetic limiting-case map only.  It does not infer WUFR Z-bar
    topology or an installed wheel-to-bar relationship.
    """
    if not all(math.isfinite(value) for value in (z_left_m, z_right_m, reference_offset_m)):
        return SymmetricDifferentialCoordinateResult(
            status=AntiRollBarStatus.FAILURE,
            failure_code=AntiRollBarFailureCode.NONFINITE_INPUT,
            message="Synthetic bilateral coordinates and reference offset must be finite",
        )
    return SymmetricDifferentialCoordinateResult(
        status=AntiRollBarStatus.SUCCESS,
        deformation_m=z_left_m - z_right_m - reference_offset_m,
        ds_dz_left=1.0,
        ds_dz_right=-1.0,
    )


def anti_roll_bar_coordinate(
    current_coordinate: float,
    reference: AntiRollBarReference,
    *,
    ds_dq: float | Iterable[float] | None = None,
    coordinate_order: Sequence[str] = (),
    coordinate_units: Sequence[str] = (),
) -> AntiRollBarCoordinateResult:
    """EQ-SUSP-0016: signed elastic deformation from an explicit reference."""
    if not math.isfinite(current_coordinate):
        return AntiRollBarCoordinateResult(
            status=AntiRollBarStatus.FAILURE,
            current_coordinate=current_coordinate,
            reference_coordinate=reference.zero_energy_coordinate,
            elastic_coordinate_unit=reference.elastic_coordinate_unit,
            failure_code=AntiRollBarFailureCode.NONFINITE_INPUT,
            message="ARB elastic coordinate must be finite",
        )
    derivatives: tuple[float, ...] = ()
    if ds_dq is not None:
        derivatives = (
            (float(ds_dq),)
            if isinstance(ds_dq, (int, float))
            else tuple(float(value) for value in ds_dq)
        )
        if not derivatives or not all(math.isfinite(value) for value in derivatives):
            return AntiRollBarCoordinateResult(
                status=AntiRollBarStatus.FAILURE,
                current_coordinate=current_coordinate,
                reference_coordinate=reference.zero_energy_coordinate,
                elastic_coordinate_unit=reference.elastic_coordinate_unit,
                ds_dq=derivatives,
                failure_code=AntiRollBarFailureCode.JACOBIAN_UNAVAILABLE,
                message="ARB deformation Jacobian must contain finite components",
            )
    order = tuple(coordinate_order)
    units = tuple(coordinate_units)
    if order and len(order) != len(derivatives):
        return AntiRollBarCoordinateResult(
            status=AntiRollBarStatus.FAILURE,
            current_coordinate=current_coordinate,
            reference_coordinate=reference.zero_energy_coordinate,
            elastic_coordinate_unit=reference.elastic_coordinate_unit,
            ds_dq=derivatives,
            coordinate_order=order,
            coordinate_units=units,
            failure_code=AntiRollBarFailureCode.JACOBIAN_UNAVAILABLE,
            message="Coordinate order length must match ds/dq length",
        )
    if units and len(units) != len(derivatives):
        return AntiRollBarCoordinateResult(
            status=AntiRollBarStatus.FAILURE,
            current_coordinate=current_coordinate,
            reference_coordinate=reference.zero_energy_coordinate,
            elastic_coordinate_unit=reference.elastic_coordinate_unit,
            ds_dq=derivatives,
            coordinate_order=order,
            coordinate_units=units,
            failure_code=AntiRollBarFailureCode.JACOBIAN_UNAVAILABLE,
            message="Coordinate units length must match ds/dq length",
        )
    return AntiRollBarCoordinateResult(
        status=AntiRollBarStatus.SUCCESS,
        deformation=current_coordinate - reference.zero_energy_coordinate,
        current_coordinate=current_coordinate,
        reference_coordinate=reference.zero_energy_coordinate,
        elastic_coordinate_unit=reference.elastic_coordinate_unit,
        ds_dq=derivatives,
        coordinate_order=order,
        coordinate_units=units,
    )


def evaluate_anti_roll_bar_law(
    definition: AntiRollBarDefinition,
    deformation: float,
) -> AntiRollBarConstitutiveResult:
    """EQ-SUSP-0017: conservative linear action, energy, and tangent stiffness."""
    if not math.isfinite(deformation):
        return AntiRollBarConstitutiveResult(
            status=AntiRollBarStatus.FAILURE,
            deformation=deformation,
            elastic_coordinate_unit=definition.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit,
            failure_code=AntiRollBarFailureCode.NONFINITE_INPUT,
            message="ARB deformation must be finite",
        )
    if definition.max_abs_deformation is not None and abs(deformation) > definition.max_abs_deformation:
        return AntiRollBarConstitutiveResult(
            status=AntiRollBarStatus.FAILURE,
            deformation=deformation,
            elastic_coordinate_unit=definition.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit,
            failure_code=AntiRollBarFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED,
            message="ARB deformation exceeds the reviewed constitutive domain",
        )
    stiffness = definition.stiffness_action_per_coordinate
    action = stiffness * deformation
    energy = 0.5 * stiffness * deformation * deformation
    if not all(math.isfinite(value) for value in (action, energy, stiffness)) or energy < 0.0:
        return AntiRollBarConstitutiveResult(
            status=AntiRollBarStatus.FAILURE,
            deformation=deformation,
            elastic_coordinate_unit=definition.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit,
            failure_code=AntiRollBarFailureCode.INVALID_ENERGY_LAW,
            message="ARB constitutive evaluation produced a nonfinite/nonconservative state",
        )
    return AntiRollBarConstitutiveResult(
        status=AntiRollBarStatus.SUCCESS,
        deformation=deformation,
        elastic_action=action,
        stored_energy_J=energy,
        tangent_stiffness=stiffness,
        elastic_coordinate_unit=definition.elastic_coordinate_unit,
        elastic_action_unit=definition.elastic_action_unit,
    )


def generalized_anti_roll_bar_force(
    elastic_action: float,
    ds_dq: float | Iterable[float],
    *,
    coordinate_order: Sequence[str] = (),
    coordinate_units: Sequence[str] = (),
) -> tuple[AntiRollBarStatus, tuple[float, ...], AntiRollBarFailureCode | None, str]:
    """EQ-SUSP-0018: Q_ARB = -(ds/dq)^T * a_ARB."""
    derivatives = (
        (float(ds_dq),)
        if isinstance(ds_dq, (int, float))
        else tuple(float(value) for value in ds_dq)
    )
    order = tuple(coordinate_order)
    units = tuple(coordinate_units)
    if not math.isfinite(elastic_action) or not derivatives or not all(math.isfinite(value) for value in derivatives):
        return (
            AntiRollBarStatus.FAILURE,
            (),
            AntiRollBarFailureCode.JACOBIAN_UNAVAILABLE,
            "ARB action and ds/dq must be finite, with at least one derivative component",
        )
    if order and len(order) != len(derivatives):
        return AntiRollBarStatus.FAILURE, (), AntiRollBarFailureCode.JACOBIAN_UNAVAILABLE, "Coordinate order length must match ds/dq length"
    if units and len(units) != len(derivatives):
        return AntiRollBarStatus.FAILURE, (), AntiRollBarFailureCode.JACOBIAN_UNAVAILABLE, "Coordinate units length must match ds/dq length"
    return AntiRollBarStatus.SUCCESS, tuple(-elastic_action * value for value in derivatives), None, ""


def evaluate_anti_roll_bar(
    definition: AntiRollBarDefinition | None,
    reference: AntiRollBarReference,
    current_coordinate: float,
    *,
    enabled: bool = True,
    ds_dq: float | Iterable[float] | None = None,
    coordinate_order: Sequence[str] = (),
    coordinate_units: Sequence[str] = (),
    disabled_arb_id: str = "",
    disabled_axle: str = "",
    disabled_source_id: str = "",
) -> AntiRollBarStateResult:
    """Compose EQ-SUSP-0016/0017/0018 for one ARB elastic state."""
    if not enabled:
        order = tuple(coordinate_order)
        return AntiRollBarStateResult(
            status=AntiRollBarStatus.NO_BAR,
            arb_id=definition.arb_id if definition else disabled_arb_id,
            axle=definition.axle if definition else disabled_axle,
            source_id=definition.source_id if definition else disabled_source_id,
            configuration_id=definition.configuration_id if definition else reference.configuration_id,
            assumption_ids=tuple(dict.fromkeys((*(definition.assumption_ids if definition else ()), *reference.assumption_ids))),
            enabled=False,
            reduced_axle_level=definition.reduced_axle_level if definition else False,
            elastic_coordinate_unit=definition.elastic_coordinate_unit if definition else reference.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit if definition else "",
            current_coordinate=current_coordinate if math.isfinite(current_coordinate) else None,
            reference_coordinate=reference.zero_energy_coordinate,
            deformation=0.0,
            elastic_action=0.0,
            stored_energy_J=0.0,
            tangent_stiffness=0.0,
            coordinate_order=order,
            coordinate_units=tuple(coordinate_units),
            generalized_force=tuple(0.0 for _ in order),
            generalized_force_available=bool(order),
            installed_as_built_authority=False,
            message="Anti-roll bar explicitly disabled by configuration; returned zero action with provenance",
        )
    if definition is None:
        return AntiRollBarStateResult(
            status=AntiRollBarStatus.FAILURE,
            configuration_id=reference.configuration_id,
            elastic_coordinate_unit=reference.elastic_coordinate_unit,
            reference_coordinate=reference.zero_energy_coordinate,
            failure_code=AntiRollBarFailureCode.MISSING_STIFFNESS_AUTHORITY,
            message="Enabled anti-roll bar requires a reviewed constitutive definition",
        )
    if definition.configuration_id != reference.configuration_id or definition.elastic_coordinate_unit != reference.elastic_coordinate_unit:
        return AntiRollBarStateResult(
            status=AntiRollBarStatus.FAILURE,
            arb_id=definition.arb_id,
            axle=definition.axle,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=definition.assumption_ids,
            reduced_axle_level=definition.reduced_axle_level,
            elastic_coordinate_unit=definition.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit,
            failure_code=AntiRollBarFailureCode.SOURCE_CONFIGURATION_MISMATCH,
            message="ARB definition and zero-energy reference configuration/unit identities do not match",
        )

    assumptions = tuple(dict.fromkeys((*definition.assumption_ids, *reference.assumption_ids)))
    coordinate = anti_roll_bar_coordinate(
        current_coordinate,
        reference,
        ds_dq=ds_dq,
        coordinate_order=coordinate_order,
        coordinate_units=coordinate_units,
    )
    if not coordinate.ok or coordinate.deformation is None:
        return AntiRollBarStateResult(
            status=AntiRollBarStatus.FAILURE,
            arb_id=definition.arb_id,
            axle=definition.axle,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=assumptions,
            reduced_axle_level=definition.reduced_axle_level,
            elastic_coordinate_unit=definition.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit,
            current_coordinate=current_coordinate,
            reference_coordinate=reference.zero_energy_coordinate,
            failure_code=coordinate.failure_code,
            message=coordinate.message,
        )

    constitutive = evaluate_anti_roll_bar_law(definition, coordinate.deformation)
    if not constitutive.ok:
        return AntiRollBarStateResult(
            status=AntiRollBarStatus.FAILURE,
            arb_id=definition.arb_id,
            axle=definition.axle,
            source_id=definition.source_id,
            configuration_id=definition.configuration_id,
            assumption_ids=assumptions,
            reduced_axle_level=definition.reduced_axle_level,
            elastic_coordinate_unit=definition.elastic_coordinate_unit,
            elastic_action_unit=definition.elastic_action_unit,
            current_coordinate=current_coordinate,
            reference_coordinate=reference.zero_energy_coordinate,
            deformation=coordinate.deformation,
            failure_code=constitutive.failure_code,
            message=constitutive.message,
        )

    generalized: tuple[float, ...] = ()
    generalized_available = False
    if coordinate.ds_dq and constitutive.elastic_action is not None:
        q_status, generalized, q_failure, q_message = generalized_anti_roll_bar_force(
            constitutive.elastic_action,
            coordinate.ds_dq,
            coordinate_order=coordinate.coordinate_order,
            coordinate_units=coordinate.coordinate_units,
        )
        if q_status is AntiRollBarStatus.FAILURE:
            return AntiRollBarStateResult(
                status=AntiRollBarStatus.FAILURE,
                arb_id=definition.arb_id,
                axle=definition.axle,
                source_id=definition.source_id,
                configuration_id=definition.configuration_id,
                assumption_ids=assumptions,
                reduced_axle_level=definition.reduced_axle_level,
                elastic_coordinate_unit=definition.elastic_coordinate_unit,
                elastic_action_unit=definition.elastic_action_unit,
                current_coordinate=current_coordinate,
                reference_coordinate=reference.zero_energy_coordinate,
                deformation=coordinate.deformation,
                elastic_action=constitutive.elastic_action,
                stored_energy_J=constitutive.stored_energy_J,
                tangent_stiffness=constitutive.tangent_stiffness,
                failure_code=q_failure,
                message=q_message,
            )
        generalized_available = True

    return AntiRollBarStateResult(
        status=AntiRollBarStatus.SUCCESS,
        arb_id=definition.arb_id,
        axle=definition.axle,
        source_id=definition.source_id,
        configuration_id=definition.configuration_id,
        assumption_ids=assumptions,
        enabled=True,
        reduced_axle_level=definition.reduced_axle_level,
        elastic_coordinate_unit=definition.elastic_coordinate_unit,
        elastic_action_unit=definition.elastic_action_unit,
        current_coordinate=current_coordinate,
        reference_coordinate=reference.zero_energy_coordinate,
        deformation=coordinate.deformation,
        elastic_action=constitutive.elastic_action,
        stored_energy_J=constitutive.stored_energy_J,
        tangent_stiffness=constitutive.tangent_stiffness,
        coordinate_order=coordinate.coordinate_order,
        coordinate_units=coordinate.coordinate_units,
        ds_dq=coordinate.ds_dq,
        generalized_force=generalized,
        generalized_force_available=generalized_available,
        installed_as_built_authority=definition.installed_as_built_authority and reference.installed_as_built_authority,
    )


def check_anti_roll_bar_energy_gradient(
    definition: AntiRollBarDefinition,
    reference: AntiRollBarReference,
    current_coordinate: float,
    ds_dq: float,
    *,
    step_sizes: Sequence[float] = (1.0e-6, 5.0e-7),
) -> AntiRollBarEnergyCheckResult:
    """Independent centered finite-difference check of EQ-SUSP-0018."""
    if (
        not math.isfinite(current_coordinate)
        or not math.isfinite(ds_dq)
        or not step_sizes
        or not all(math.isfinite(step) and step > 0.0 for step in step_sizes)
    ):
        return AntiRollBarEnergyCheckResult(
            status=AntiRollBarStatus.FAILURE,
            failure_code=AntiRollBarFailureCode.NONFINITE_INPUT,
            message="Energy-check state, derivative, and step sizes must be finite with positive steps",
        )
    center = evaluate_anti_roll_bar(definition, reference, current_coordinate)
    if not center.ok or center.elastic_action is None:
        return AntiRollBarEnergyCheckResult(
            status=AntiRollBarStatus.FAILURE,
            failure_code=center.failure_code,
            message=center.message or "Center ARB state is unavailable for energy check",
        )
    expected = -center.elastic_action * ds_dq
    finite_difference: list[float] = []
    residuals: list[float] = []
    for step in step_sizes:
        plus = evaluate_anti_roll_bar(definition, reference, current_coordinate + ds_dq * step)
        minus = evaluate_anti_roll_bar(definition, reference, current_coordinate - ds_dq * step)
        if not plus.ok or not minus.ok or plus.stored_energy_J is None or minus.stored_energy_J is None:
            failure = plus if not plus.ok else minus
            return AntiRollBarEnergyCheckResult(
                status=AntiRollBarStatus.FAILURE,
                expected_generalized_force=expected,
                finite_difference_generalized_force=tuple(finite_difference),
                step_sizes=tuple(float(value) for value in step_sizes),
                absolute_residuals=tuple(residuals),
                failure_code=failure.failure_code or AntiRollBarFailureCode.CONSTITUTIVE_DOMAIN_EXCEEDED,
                message=failure.message or "Energy-check perturbation left the reviewed ARB domain",
            )
        q_fd = -(plus.stored_energy_J - minus.stored_energy_J) / (2.0 * step)
        finite_difference.append(q_fd)
        residuals.append(abs(q_fd - expected))
    return AntiRollBarEnergyCheckResult(
        status=AntiRollBarStatus.SUCCESS,
        expected_generalized_force=expected,
        finite_difference_generalized_force=tuple(finite_difference),
        step_sizes=tuple(float(value) for value in step_sizes),
        absolute_residuals=tuple(residuals),
    )


def load_wufr27_anti_roll_bar_package(path: str | Path) -> WufrAntiRollBarPackage:
    """Load the frozen reviewer-selected WUFR27 reduced ARB source adapter."""
    source_path = Path(path)
    with source_path.open("rb") as stream:
        data = tomllib.load(stream)

    configuration_id = str(data["configuration_id"])
    source_record_id = str(data["record_id"])
    installed_authority = bool(data.get("installed_as_built_authority", False))
    source = data["historical_weight_transfer_script"]
    front_deg = float(source["front_effective_roll_stiffness_Nm_per_deg"])
    rear_deg = float(source["rear_effective_roll_stiffness_Nm_per_deg"])
    front_si = stiffness_Nm_per_deg_to_Nm_per_rad(front_deg)
    rear_si = stiffness_Nm_per_deg_to_Nm_per_rad(rear_deg)

    if not math.isclose(front_deg, float(source["observed_front_literal"]), rel_tol=0.0, abs_tol=1.0e-12):
        raise SuspensionAntiRollBarError("WUFR front selected ARB stiffness no longer matches the frozen MATLAB literal")
    if not math.isclose(rear_deg, float(source["observed_rear_literal"]), rel_tol=0.0, abs_tol=1.0e-12):
        raise SuspensionAntiRollBarError("WUFR rear selected ARB stiffness no longer matches the frozen MATLAB literal")
    if not math.isclose(front_si, float(source["front_effective_roll_stiffness_Nm_per_rad"]), rel_tol=1.0e-12, abs_tol=1.0e-12):
        raise SuspensionAntiRollBarError("WUFR front stored SI stiffness does not match explicit degree-to-radian conversion")
    if not math.isclose(rear_si, float(source["rear_effective_roll_stiffness_Nm_per_rad"]), rel_tol=1.0e-12, abs_tol=1.0e-12):
        raise SuspensionAntiRollBarError("WUFR rear stored SI stiffness does not match explicit degree-to-radian conversion")

    assumptions = ("ASM-SUSP-0003",)
    front = AntiRollBarDefinition(
        arb_id="WUFR27_FRONT_ARB_REDUCED_V0",
        axle="front",
        stiffness_action_per_coordinate=front_si,
        elastic_coordinate_unit="rad",
        elastic_action_unit="N*m",
        source_stiffness_Nm_per_deg=front_deg,
        source_id=source_record_id,
        configuration_id=configuration_id,
        assumption_ids=assumptions,
        installed_as_built_authority=installed_authority,
        reduced_axle_level=True,
    )
    rear = AntiRollBarDefinition(
        arb_id="WUFR27_REAR_ARB_REDUCED_V0",
        axle="rear",
        stiffness_action_per_coordinate=rear_si,
        elastic_coordinate_unit="rad",
        elastic_action_unit="N*m",
        source_stiffness_Nm_per_deg=rear_deg,
        source_id=source_record_id,
        configuration_id=configuration_id,
        assumption_ids=assumptions,
        installed_as_built_authority=installed_authority,
        reduced_axle_level=True,
    )
    reference = AntiRollBarReference(
        reference_id="WUFR27_ARB_ZERO_PRELOAD_REFERENCE_V0",
        configuration_id=configuration_id,
        elastic_coordinate_unit="rad",
        zero_energy_coordinate=0.0,
        assumption_ids=assumptions,
        installed_as_built_authority=False,
    )
    return WufrAntiRollBarPackage(
        configuration_id=configuration_id,
        source_record_id=source_record_id,
        front=front,
        rear=rear,
        reference=reference,
        source_front_stiffness_Nm_per_deg=front_deg,
        source_rear_stiffness_Nm_per_deg=rear_deg,
        instron_status=str(data["instron_corroboration"]["status"]),
        installed_as_built_authority=installed_authority,
    )
