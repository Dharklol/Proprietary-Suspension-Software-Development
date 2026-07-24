"""Provider-neutral vehicle operating-state exchange contract.

This module stores already-determined vehicle and wheel operating states.  It does
not calculate load transfer, aero, suspension motion, tire forces, or vehicle
equilibrium.  Upstream tools remain responsible for those calculations and must
preserve their authority, assumptions, and missing-data boundaries when exporting
states through this contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Iterable, Mapping


class VehicleStateError(ValueError):
    """Raised when a vehicle-state definition is incomplete or inconsistent."""


class WheelPosition(str, Enum):
    FRONT_LEFT = "front_left"
    FRONT_RIGHT = "front_right"
    REAR_LEFT = "rear_left"
    REAR_RIGHT = "rear_right"


class TurnDirection(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    STRAIGHT = "straight"
    UNSPECIFIED = "unspecified"


class VehicleStateRole(str, Enum):
    """How a supplied state may be used by downstream design workflows."""

    EVIDENCE_ONLY = "evidence_only"
    REPORT_ONLY = "report_only"
    DESIGN_INPUT = "design_input"


TIRE_OPERATING_POINT_FIELDS = (
    "normal_load_n",
    "inclination_deg",
    "pressure_kpa",
)

LATERAL_TIRE_DEMAND_FIELDS = TIRE_OPERATING_POINT_FIELDS + (
    "lateral_force_demand_n",
)

_OPTIONAL_WHEEL_FIELDS = {
    "normal_load_n",
    "inclination_deg",
    "pressure_kpa",
    "lateral_force_demand_n",
    "longitudinal_force_demand_n",
}


def _pairs(values: Mapping[object, object] | None) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted((str(key), str(value)) for key, value in (values or {}).items())
    )


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value)


@dataclass(frozen=True)
class WheelOperatingState:
    """One wheel's explicitly supplied operating quantities.

    Missing values remain ``None``.  They are never replaced with zero, a default
    setup value, or a value inferred from another wheel.
    """

    position: WheelPosition
    normal_load_n: float | None = None
    inclination_deg: float | None = None
    pressure_kpa: float | None = None
    lateral_force_demand_n: float | None = None
    longitudinal_force_demand_n: float | None = None
    missing_reasons: tuple[tuple[str, str], ...] = ()
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in _OPTIONAL_WHEEL_FIELDS:
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise VehicleStateError(
                    f"{self.position.value} {name} must be finite when supplied"
                )
        if self.normal_load_n is not None and self.normal_load_n < 0.0:
            raise VehicleStateError(
                f"{self.position.value} normal_load_n cannot be negative; "
                "wheel lift may be represented by zero, but negative source loads "
                "must be rejected rather than clipped"
            )
        if self.pressure_kpa is not None and self.pressure_kpa <= 0.0:
            raise VehicleStateError(
                f"{self.position.value} pressure_kpa must be positive when supplied"
            )

        reason_map = dict(self.missing_reasons)
        unknown = sorted(set(reason_map) - _OPTIONAL_WHEEL_FIELDS)
        if unknown:
            raise VehicleStateError(
                f"{self.position.value} has missing reasons for unknown fields: {unknown}"
            )
        contradictory = sorted(
            field_name
            for field_name in reason_map
            if getattr(self, field_name) is not None
        )
        if contradictory:
            raise VehicleStateError(
                f"{self.position.value} marks supplied fields missing: {contradictory}"
            )

    @property
    def missing_reason_map(self) -> dict[str, str]:
        return dict(self.missing_reasons)

    def missing_fields(self, required_fields: Iterable[str]) -> tuple[str, ...]:
        requested = tuple(str(name) for name in required_fields)
        unknown = sorted(set(requested) - _OPTIONAL_WHEEL_FIELDS)
        if unknown:
            raise VehicleStateError(f"Unknown wheel operating-state fields: {unknown}")
        return tuple(name for name in requested if getattr(self, name) is None)

    def completeness_record(self, required_fields: Iterable[str]) -> dict[str, str]:
        """Return missing fields and explicit source reasons where available."""

        reasons = self.missing_reason_map
        return {
            name: reasons.get(name, "not supplied by source")
            for name in self.missing_fields(required_fields)
        }


@dataclass(frozen=True)
class VehicleOperatingState:
    """One named vehicle state with exactly four wheel records."""

    state_id: str
    role: VehicleStateRole
    turn_direction: TurnDirection
    ax_g: float
    ay_g: float
    speed_mps: float
    wheels: tuple[WheelOperatingState, ...]
    state_weight: float = 0.0
    suspension_pose_state_id: str = ""
    authority: str = ""
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id:
            raise VehicleStateError("Vehicle operating state requires state_id")
        if not all(math.isfinite(value) for value in (self.ax_g, self.ay_g, self.speed_mps)):
            raise VehicleStateError("Vehicle acceleration and speed values must be finite")
        if self.speed_mps < 0.0:
            raise VehicleStateError("speed_mps cannot be negative")
        if not math.isfinite(self.state_weight) or self.state_weight < 0.0:
            raise VehicleStateError("state_weight must be finite and nonnegative")
        if self.role is VehicleStateRole.DESIGN_INPUT and self.state_weight <= 0.0:
            raise VehicleStateError("design_input states require a positive state_weight")
        if self.role is not VehicleStateRole.DESIGN_INPUT and self.state_weight != 0.0:
            raise VehicleStateError(
                "evidence_only/report_only states must use state_weight=0 so evidence "
                "cannot silently become a design objective"
            )

        positions = [wheel.position for wheel in self.wheels]
        expected = set(WheelPosition)
        if len(positions) != 4 or set(positions) != expected:
            raise VehicleStateError(
                "Vehicle operating state requires exactly one front_left, front_right, "
                "rear_left, and rear_right wheel record"
            )

    @property
    def wheel_map(self) -> dict[WheelPosition, WheelOperatingState]:
        return {wheel.position: wheel for wheel in self.wheels}

    def wheel(self, position: WheelPosition | str) -> WheelOperatingState:
        key = position if isinstance(position, WheelPosition) else WheelPosition(position)
        return self.wheel_map[key]

    @property
    def total_normal_load_n(self) -> float | None:
        values = [wheel.normal_load_n for wheel in self.wheels]
        if any(value is None for value in values):
            return None
        return sum(float(value) for value in values if value is not None)

    def missing_front_fields(self, required_fields: Iterable[str]) -> dict[str, dict[str, str]]:
        return {
            position.value: self.wheel(position).completeness_record(required_fields)
            for position in (WheelPosition.FRONT_LEFT, WheelPosition.FRONT_RIGHT)
        }


@dataclass(frozen=True)
class VehicleOperatingStateSet:
    """Source-preserving collection of explicit vehicle operating states."""

    state_set_id: str
    version: str
    source_type: str
    authority: str
    source_path: str
    source_revision: str
    canonical_body_axes: str
    lateral_acceleration_convention: str
    states: tuple[VehicleOperatingState, ...]
    provenance: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        required_text = {
            "state_set_id": self.state_set_id,
            "version": self.version,
            "source_type": self.source_type,
            "authority": self.authority,
            "source_path": self.source_path,
            "source_revision": self.source_revision,
            "canonical_body_axes": self.canonical_body_axes,
            "lateral_acceleration_convention": self.lateral_acceleration_convention,
        }
        missing = sorted(name for name, value in required_text.items() if not value)
        if missing:
            raise VehicleStateError(f"Vehicle operating-state set is missing: {missing}")
        if not self.states:
            raise VehicleStateError("Vehicle operating-state set requires at least one state")
        ids = [state.state_id for state in self.states]
        if len(ids) != len(set(ids)):
            raise VehicleStateError("Vehicle operating-state set contains duplicate state IDs")

    @property
    def state_map(self) -> dict[str, VehicleOperatingState]:
        return {state.state_id: state for state in self.states}

    def state(self, state_id: str) -> VehicleOperatingState:
        try:
            return self.state_map[state_id]
        except KeyError as exc:
            raise VehicleStateError(f"Unknown vehicle operating state {state_id!r}") from exc


def _load_wheel(table: Mapping[str, object]) -> WheelOperatingState:
    return WheelOperatingState(
        position=WheelPosition(str(table.get("position", ""))),
        normal_load_n=_optional_float(table.get("normal_load_n")),
        inclination_deg=_optional_float(table.get("inclination_deg")),
        pressure_kpa=_optional_float(table.get("pressure_kpa")),
        lateral_force_demand_n=_optional_float(table.get("lateral_force_demand_n")),
        longitudinal_force_demand_n=_optional_float(table.get("longitudinal_force_demand_n")),
        missing_reasons=_pairs(table.get("missing_reasons") if isinstance(table.get("missing_reasons"), dict) else None),
        provenance=_pairs(table.get("provenance") if isinstance(table.get("provenance"), dict) else None),
    )


def load_vehicle_operating_state_set(path: str | Path) -> VehicleOperatingStateSet:
    """Load an explicit source table without calculating or filling missing physics."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type", "")) != "explicit_vehicle_operating_states":
        raise VehicleStateError("source_type must be explicit_vehicle_operating_states")

    states: list[VehicleOperatingState] = []
    for table in document.get("states", []):
        if not isinstance(table, dict):
            raise VehicleStateError("Each vehicle state must be a TOML table")
        wheels_raw = table.get("wheels", [])
        if not isinstance(wheels_raw, list):
            raise VehicleStateError(f"State {table.get('id', '')!r} wheels must be an array")
        states.append(
            VehicleOperatingState(
                state_id=str(table.get("id", "")),
                role=VehicleStateRole(str(table.get("role", ""))),
                turn_direction=TurnDirection(str(table.get("turn_direction", "unspecified"))),
                ax_g=float(table.get("ax_g", 0.0)),
                ay_g=float(table.get("ay_g", 0.0)),
                speed_mps=float(table.get("speed_mps", 0.0)),
                wheels=tuple(_load_wheel(item) for item in wheels_raw),
                state_weight=float(table.get("state_weight", 0.0)),
                suspension_pose_state_id=str(table.get("suspension_pose_state_id", "")),
                authority=str(table.get("authority", document.get("authority", ""))),
                provenance=_pairs(
                    table.get("provenance") if isinstance(table.get("provenance"), dict) else None
                ),
            )
        )

    source = document.get("source", {})
    source_dict = source if isinstance(source, dict) else {}
    return VehicleOperatingStateSet(
        state_set_id=str(document.get("state_set_id", "")),
        version=str(document.get("version", "")),
        source_type=str(document.get("source_type", "")),
        authority=str(document.get("authority", "")),
        source_path=str(document.get("source_path", source_path)),
        source_revision=str(document.get("source_revision", "")),
        canonical_body_axes=str(document.get("canonical_body_axes", "")),
        lateral_acceleration_convention=str(
            document.get("lateral_acceleration_convention", "")
        ),
        states=tuple(states),
        provenance=_pairs(source_dict),
    )
