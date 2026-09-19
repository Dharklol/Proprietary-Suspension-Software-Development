"""Small notebook-facing vehicle reference assembled from reviewed WUFR providers.

This module deliberately does not create a second vehicle-data source. It loads
existing reviewed source records through their production provider loaders, checks
that those sources are mutually compatible, and exposes a compact read-only view
for education notebooks and other high-level consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tomllib

from .force_coordinates import WUFRWholeVehicleAdapter, load_wufr_whole_vehicle_adapter
from .wufr_gravity import (
    CORNER_ORDER as WUFR_GRAVITY_CORNER_ORDER,
    WUFRStaticGravityAllocation,
    load_wufr_static_gravity_allocation,
)


Vector3 = tuple[float, float, float]


class VehicleReferenceError(ValueError):
    """Raised when a notebook source selector is incomplete or inconsistent."""


@dataclass(frozen=True)
class VehicleReferenceGeometry:
    """Reviewed design-reference dimensions exposed in SI units."""

    wheelbase_m: float
    front_track_m: float
    rear_track_m: float
    cg_to_front_axle_m: float
    cg_to_rear_axle_m: float

    def __post_init__(self) -> None:
        values = (
            self.wheelbase_m,
            self.front_track_m,
            self.rear_track_m,
            self.cg_to_front_axle_m,
            self.cg_to_rear_axle_m,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise VehicleReferenceError("Vehicle reference geometry must be finite and positive")
        if not math.isclose(
            self.cg_to_front_axle_m + self.cg_to_rear_axle_m,
            self.wheelbase_m,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise VehicleReferenceError("CG-to-axle distances must sum to wheelbase")


@dataclass(frozen=True)
class VehicleReferenceCG:
    """Total-CG design reference in the reviewed suspension-CAD source frame."""

    source_position_m: Vector3

    def __post_init__(self) -> None:
        if len(self.source_position_m) != 3 or not all(
            math.isfinite(value) for value in self.source_position_m
        ):
            raise VehicleReferenceError("CG source position must be a finite three-vector")

    @property
    def height_above_nominal_road_m(self) -> float:
        return self.source_position_m[2]


@dataclass(frozen=True)
class VehicleReferenceScaleState:
    """Reviewed four-corner scale state used by the education reference."""

    corner_order: tuple[str, str, str, str]
    corner_load_lb: tuple[float, float, float, float]
    total_load_lb: float

    def __post_init__(self) -> None:
        if len(self.corner_order) != 4 or len(self.corner_load_lb) != 4:
            raise VehicleReferenceError("Scale state requires four ordered corner readings")
        if not all(math.isfinite(value) and value > 0.0 for value in self.corner_load_lb):
            raise VehicleReferenceError("Scale readings must be finite and positive")
        if not math.isfinite(self.total_load_lb) or self.total_load_lb <= 0.0:
            raise VehicleReferenceError("Total scale reading must be finite and positive")
        if not math.isclose(
            sum(self.corner_load_lb),
            self.total_load_lb,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise VehicleReferenceError("Corner scale readings must sum to the total")

    @property
    def front_axle_load_lb(self) -> float:
        return self.corner_load_lb[0] + self.corner_load_lb[1]

    @property
    def rear_axle_load_lb(self) -> float:
        return self.corner_load_lb[2] + self.corner_load_lb[3]

    @property
    def front_fraction(self) -> float:
        return self.front_axle_load_lb / self.total_load_lb

    @property
    def rear_fraction(self) -> float:
        return self.rear_axle_load_lb / self.total_load_lb


@dataclass(frozen=True)
class VehicleReference:
    """Compact education-facing view over existing reviewed vehicle providers."""

    selector_id: str
    vehicle_revision: str
    source_configuration_id: str
    state_id: str
    total_mass_kg: float
    g_mps2: float
    geometry: VehicleReferenceGeometry
    cg: VehicleReferenceCG
    scale_state: VehicleReferenceScaleState
    whole_vehicle_adapter_id: str
    gravity_record_id: str
    authority: tuple[str, str]

    def __post_init__(self) -> None:
        if not self.selector_id or not self.vehicle_revision or not self.source_configuration_id:
            raise VehicleReferenceError("Vehicle reference identity fields must be non-empty")
        if not math.isfinite(self.total_mass_kg) or self.total_mass_kg <= 0.0:
            raise VehicleReferenceError("Total mass must be finite and positive")
        if not math.isfinite(self.g_mps2) or self.g_mps2 <= 0.0:
            raise VehicleReferenceError("Gravity acceleration must be finite and positive")
        if any(not item.strip() for item in self.authority):
            raise VehicleReferenceError("Underlying source authority must be preserved")

    @property
    def total_weight_N(self) -> float:
        """Return the reference-state total gravity force magnitude."""

        return self.total_mass_kg * self.g_mps2


def _resolve_declared_path(selector_path: Path, declared_path: str) -> Path:
    candidate = Path(declared_path)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    for ancestor in (selector_path.parent, *selector_path.parents):
        resolved = ancestor / candidate
        if resolved.is_file():
            return resolved
    raise FileNotFoundError(
        f"Cannot resolve education source {declared_path!r} from {selector_path}"
    )


def _require_expected_source_ids(
    *,
    document: dict,
    whole_vehicle: WUFRWholeVehicleAdapter,
    gravity: WUFRStaticGravityAllocation,
) -> None:
    sources = document.get("sources")
    if not isinstance(sources, dict):
        raise VehicleReferenceError("Education selector requires a [sources] table")

    expected_whole = str(sources.get("whole_vehicle_adapter_id", ""))
    expected_gravity = str(sources.get("static_gravity_record_id", ""))
    if whole_vehicle.adapter_id != expected_whole:
        raise VehicleReferenceError(
            f"Whole-vehicle adapter mismatch: {whole_vehicle.adapter_id!r} != {expected_whole!r}"
        )
    if gravity.record_id != expected_gravity:
        raise VehicleReferenceError(
            f"Static-gravity record mismatch: {gravity.record_id!r} != {expected_gravity!r}"
        )


def _require_source_compatibility(
    *,
    document: dict,
    whole_vehicle: WUFRWholeVehicleAdapter,
    gravity: WUFRStaticGravityAllocation,
) -> None:
    authority = document.get("authority")
    if not isinstance(authority, dict):
        raise VehicleReferenceError("Education selector requires an [authority] table")
    source_configuration_id = str(authority.get("source_configuration_id", ""))
    if not source_configuration_id:
        raise VehicleReferenceError("source_configuration_id is required")

    if whole_vehicle.configuration_id != source_configuration_id:
        raise VehicleReferenceError(
            "Whole-vehicle source configuration does not match the selector authority"
        )
    if gravity.configuration_id != source_configuration_id:
        raise VehicleReferenceError(
            "Static-gravity source configuration does not match the selector authority"
        )
    if any(
        not math.isclose(a, b, rel_tol=0.0, abs_tol=1.0e-12)
        for a, b in zip(whole_vehicle.cg_source_position_m, gravity.total_cg_source_m)
    ):
        raise VehicleReferenceError(
            "Whole-vehicle and static-gravity providers do not share the same total-CG reference"
        )


def load_vehicle_reference(path: str | Path) -> VehicleReference:
    """Load the minimal WUFR education vehicle view without duplicating source values."""

    selector_path = Path(path).resolve()
    with selector_path.open("rb") as stream:
        document = tomllib.load(stream)

    selector_id = str(document.get("configuration_id", ""))
    vehicle_revision = str(document.get("vehicle_revision", ""))
    if not selector_id or not vehicle_revision:
        raise VehicleReferenceError(
            "Education selector requires configuration_id and vehicle_revision"
        )

    sources = document.get("sources")
    if not isinstance(sources, dict):
        raise VehicleReferenceError("Education selector requires a [sources] table")
    whole_path = _resolve_declared_path(
        selector_path, str(sources.get("whole_vehicle_path", ""))
    )
    gravity_path = _resolve_declared_path(
        selector_path, str(sources.get("static_gravity_path", ""))
    )

    whole_vehicle = load_wufr_whole_vehicle_adapter(whole_path)
    gravity = load_wufr_static_gravity_allocation(gravity_path)
    _require_expected_source_ids(
        document=document,
        whole_vehicle=whole_vehicle,
        gravity=gravity,
    )
    _require_source_compatibility(
        document=document,
        whole_vehicle=whole_vehicle,
        gravity=gravity,
    )

    geometry = VehicleReferenceGeometry(
        wheelbase_m=whole_vehicle.wheelbase_m,
        front_track_m=whole_vehicle.front_track_m,
        rear_track_m=whole_vehicle.rear_track_m,
        cg_to_front_axle_m=whole_vehicle.cg_to_front_axle_m,
        cg_to_rear_axle_m=whole_vehicle.cg_to_rear_axle_m,
    )
    cg = VehicleReferenceCG(source_position_m=whole_vehicle.cg_source_position_m)
    scale_state = VehicleReferenceScaleState(
        corner_order=WUFR_GRAVITY_CORNER_ORDER,
        corner_load_lb=gravity.reviewed_corner_scale_lb,
        total_load_lb=gravity.reviewed_total_scale_lb,
    )
    authority = document["authority"]
    return VehicleReference(
        selector_id=selector_id,
        vehicle_revision=vehicle_revision,
        source_configuration_id=str(authority["source_configuration_id"]),
        state_id=gravity.state_id,
        total_mass_kg=gravity.total_mass_kg,
        g_mps2=gravity.g_mps2,
        geometry=geometry,
        cg=cg,
        scale_state=scale_state,
        whole_vehicle_adapter_id=whole_vehicle.adapter_id,
        gravity_record_id=gravity.record_id,
        authority=(whole_vehicle.authority, gravity.source_authority),
    )
