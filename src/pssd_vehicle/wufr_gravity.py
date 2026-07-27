"""WUFR driver/no-fuel static-gravity mass allocation provider.

Authorized by AUTH-VEH-0005.  The provider is deliberately source-driven: it
loads the reviewed total driver/no-fuel design reference, the measured 10 kg
front / 10 kg rear unsprung axle totals, and ASM-VEH-0003's explicit 5 kg per
corner prototype allocation.  It derives the sprung body by mass/first-moment
subtraction and returns physical gravity point loads.

It does not define the road-compatible wheel map, suspension equilibrium,
road reactions, load transfer, or maneuver unsprung inertia.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Sequence

from .force_coordinates import BodyPose, GeneralizedForceResult, PointReference, analytical_generalized_force


Vector3 = tuple[float, float, float]
CORNER_ORDER = ("front_left", "front_right", "rear_left", "rear_right")
REQUIRED_RECORD_ID = "WUFR27_STATIC_GRAVITY_ALLOCATION_V0"
REQUIRED_ASSUMPTION_ID = "ASM-VEH-0003"


class WUFRGravityStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class WUFRGravityFailureCode(str, Enum):
    SOURCE_MISMATCH = "source_mismatch"
    ASSUMPTION_MISMATCH = "assumption_mismatch"
    NONFINITE_INPUT = "nonfinite_input"
    INVALID_MASS = "invalid_mass"
    AXLE_ALLOCATION_MISMATCH = "axle_allocation_mismatch"
    FIRST_MOMENT_MISMATCH = "first_moment_mismatch"
    AUTHORITY_EXCEEDED = "authority_exceeded"


class WUFRGravityError(ValueError):
    def __init__(self, code: WUFRGravityFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GravityPointMass:
    point_id: str
    corner_id: str | None
    mass_kg: float
    source_position_m: Vector3
    body_position_m: Vector3 | None
    source_id: str
    configuration_id: str
    assumption_id: str
    authority: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.mass_kg) or self.mass_kg <= 0.0:
            raise WUFRGravityError(WUFRGravityFailureCode.INVALID_MASS, "Point mass must be finite and positive")
        if len(self.source_position_m) != 3 or not all(math.isfinite(v) for v in self.source_position_m):
            raise WUFRGravityError(WUFRGravityFailureCode.NONFINITE_INPUT, "Source point must be a finite 3-vector")
        if self.body_position_m is not None and (
            len(self.body_position_m) != 3 or not all(math.isfinite(v) for v in self.body_position_m)
        ):
            raise WUFRGravityError(WUFRGravityFailureCode.NONFINITE_INPUT, "Body point must be a finite 3-vector")
        if not self.source_id or not self.configuration_id or not self.assumption_id or not self.authority:
            raise WUFRGravityError(WUFRGravityFailureCode.SOURCE_MISMATCH, "Gravity point provenance is required")

    def force_N(self, g_mps2: float) -> Vector3:
        if not math.isfinite(g_mps2) or g_mps2 <= 0.0:
            raise WUFRGravityError(WUFRGravityFailureCode.NONFINITE_INPUT, "Gravity acceleration must be finite and positive")
        return (0.0, 0.0, -self.mass_kg * g_mps2)


@dataclass(frozen=True)
class WUFRStaticGravityAllocation:
    record_id: str
    configuration_id: str
    state_id: str
    assumption_id: str
    total_mass_kg: float
    total_cg_source_m: Vector3
    sprung: GravityPointMass
    unsprung: tuple[GravityPointMass, GravityPointMass, GravityPointMass, GravityPointMass]
    g_mps2: float
    source_authority: str
    installed_as_built_authority: bool
    maneuver_unsprung_inertia_authority: bool

    @property
    def status(self) -> WUFRGravityStatus:
        return WUFRGravityStatus.SUCCESS

    @property
    def total_unsprung_mass_kg(self) -> float:
        return sum(item.mass_kg for item in self.unsprung)

    @property
    def reconstructed_total_mass_kg(self) -> float:
        return self.sprung.mass_kg + self.total_unsprung_mass_kg

    def first_moment_residual_kg_m(self) -> Vector3:
        return tuple(
            self.sprung.mass_kg * self.sprung.source_position_m[axis]
            + sum(item.mass_kg * item.source_position_m[axis] for item in self.unsprung)
            - self.total_mass_kg * self.total_cg_source_m[axis]
            for axis in range(3)
        )  # type: ignore[return-value]

    def sprung_body_point_reference(
        self,
        *,
        body_frame_id: str = "WUFR27_BODY_DRIVER_NO_FUEL_REFERENCE",
        body_origin_id: str = "WUFR27_CG_DRIVER_NO_FUEL_REFERENCE",
    ) -> PointReference:
        if self.sprung.body_position_m is None:
            raise WUFRGravityError(WUFRGravityFailureCode.SOURCE_MISMATCH, "Sprung body-position offset is unavailable")
        return PointReference(
            point_id=self.sprung.point_id,
            frame_id=body_frame_id,
            origin_id=body_origin_id,
            position_m=self.sprung.body_position_m,
            role="sprung_body_gravity_application_point",
            source_id=self.record_id,
            configuration_id=self.configuration_id,
            authority=self.source_authority,
            fixed_role="body_fixed",
            provenance=(("assumption_id", self.assumption_id), ("state_id", self.state_id)),
        )

    def sprung_body_generalized_gravity(self, pose: BodyPose) -> GeneralizedForceResult:
        """Map the derived sprung-body gravity point force through MOD-VEH-0003."""
        point = self.sprung_body_point_reference(
            body_frame_id=pose.body_frame_id,
            body_origin_id=pose.body_origin_id,
        )
        return analytical_generalized_force(point, pose, force_N=self.sprung.force_N(self.g_mps2))

    def require_static_rnd_authority(self, *, installed_as_built: bool = False, maneuver_inertia: bool = False) -> None:
        if installed_as_built and not self.installed_as_built_authority:
            raise WUFRGravityError(
                WUFRGravityFailureCode.AUTHORITY_EXCEEDED,
                "ASM-VEH-0003 does not provide installed/as-built mass authority",
            )
        if maneuver_inertia and not self.maneuver_unsprung_inertia_authority:
            raise WUFRGravityError(
                WUFRGravityFailureCode.AUTHORITY_EXCEEDED,
                "Wheel-center prototype lumps are not maneuver unsprung inertia/CG authority",
            )


def _vector3(values: Sequence[float], name: str) -> Vector3:
    if len(values) != 3:
        raise WUFRGravityError(WUFRGravityFailureCode.NONFINITE_INPUT, f"{name} must have three components")
    result = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in result):
        raise WUFRGravityError(WUFRGravityFailureCode.NONFINITE_INPUT, f"{name} must be finite")
    return result  # type: ignore[return-value]


def _derive_sprung_cg(
    total_mass_kg: float,
    total_cg: Vector3,
    unsprung_masses: Sequence[float],
    unsprung_points: Sequence[Vector3],
) -> tuple[float, Vector3]:
    sprung_mass = total_mass_kg - sum(unsprung_masses)
    if not math.isfinite(sprung_mass) or sprung_mass <= 0.0:
        raise WUFRGravityError(WUFRGravityFailureCode.INVALID_MASS, "Derived sprung mass must be positive")
    sprung_cg = tuple(
        (
            total_mass_kg * total_cg[axis]
            - sum(mass * point[axis] for mass, point in zip(unsprung_masses, unsprung_points))
        )
        / sprung_mass
        for axis in range(3)
    )
    return sprung_mass, sprung_cg  # type: ignore[return-value]


def load_wufr_static_gravity_allocation(path: str | Path) -> WUFRStaticGravityAllocation:
    """Load and independently validate the AUTH-VEH-0005 frozen source packet."""
    with Path(path).open("rb") as stream:
        document = tomllib.load(stream)

    record_id = str(document.get("record_id", ""))
    configuration_id = str(document.get("configuration_id", ""))
    state_id = str(document.get("state_id", ""))
    authority = str(document.get("record_authority", ""))
    if record_id != REQUIRED_RECORD_ID or not configuration_id or not state_id or not authority:
        raise WUFRGravityError(WUFRGravityFailureCode.SOURCE_MISMATCH, "Static-gravity source identity does not match AUTH-VEH-0005")

    source = document["source"]
    allocation = document["prototype_unsprung_allocation"]
    derived = document["derived_sprung_body"]
    gravity = document["gravity"]
    boundaries = document["authority_boundaries"]

    assumption_id = str(source.get("assumption_id", ""))
    if assumption_id != REQUIRED_ASSUMPTION_ID:
        raise WUFRGravityError(WUFRGravityFailureCode.ASSUMPTION_MISMATCH, "ASM-VEH-0003 is required")

    lb_to_kg = float(source["lb_to_kg"])
    total_lb = float(source["reviewed_total_scale_lb"])
    total_mass = total_lb * lb_to_kg
    if not all(math.isfinite(v) and v > 0.0 for v in (lb_to_kg, total_lb, total_mass)):
        raise WUFRGravityError(WUFRGravityFailureCode.INVALID_MASS, "Total scale conversion must be finite and positive")
    if not math.isclose(total_mass, float(source["total_mass_kg"]), rel_tol=0.0, abs_tol=1.0e-12):
        raise WUFRGravityError(WUFRGravityFailureCode.SOURCE_MISMATCH, "Stored total mass does not match exact scale conversion")

    corner_order = tuple(str(v) for v in allocation["corner_order"])
    if corner_order != CORNER_ORDER:
        raise WUFRGravityError(WUFRGravityFailureCode.SOURCE_MISMATCH, "Corner order must be FL,FR,RL,RR")
    masses = tuple(float(v) for v in allocation["corner_mass_kg"])
    if len(masses) != 4 or not all(math.isfinite(v) and v > 0.0 for v in masses):
        raise WUFRGravityError(WUFRGravityFailureCode.INVALID_MASS, "Four positive finite corner masses are required")
    front_axle = float(source["reviewed_front_unsprung_axle_mass_kg"])
    rear_axle = float(source["reviewed_rear_unsprung_axle_mass_kg"])
    if not math.isclose(sum(masses[:2]), front_axle, abs_tol=1.0e-12) or not math.isclose(sum(masses[2:]), rear_axle, abs_tol=1.0e-12):
        raise WUFRGravityError(WUFRGravityFailureCode.AXLE_ALLOCATION_MISMATCH, "Corner masses do not reconcile measured axle totals")

    wheel_points = tuple(_vector3(point, f"{corner_order[i]} wheel point") for i, point in enumerate(allocation["nominal_wheel_center_source_m"]))
    if len(wheel_points) != 4:
        raise WUFRGravityError(WUFRGravityFailureCode.SOURCE_MISMATCH, "Four wheel-center points are required")
    total_cg = _vector3(derived["total_cg_source_m"], "total CG")
    sprung_mass, sprung_cg = _derive_sprung_cg(total_mass, total_cg, masses, wheel_points)
    stored_sprung_mass = float(derived["sprung_mass_kg"])
    stored_sprung_cg = _vector3(derived["sprung_cg_source_m"], "stored sprung CG")
    if not math.isclose(sprung_mass, stored_sprung_mass, rel_tol=0.0, abs_tol=1.0e-12) or any(
        not math.isclose(a, b, rel_tol=0.0, abs_tol=1.0e-12) for a, b in zip(sprung_cg, stored_sprung_cg)
    ):
        raise WUFRGravityError(WUFRGravityFailureCode.FIRST_MOMENT_MISMATCH, "Stored sprung decomposition does not match independent first-moment calculation")

    body_offset = tuple(sprung_cg[i] - total_cg[i] for i in range(3))
    stored_body_offset = _vector3(derived["sprung_cg_relative_to_total_cg_body_m"], "sprung body offset")
    if any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1.0e-12) for a, b in zip(body_offset, stored_body_offset)):
        raise WUFRGravityError(WUFRGravityFailureCode.FIRST_MOMENT_MISMATCH, "Stored sprung body offset is inconsistent")

    unsprung = tuple(
        GravityPointMass(
            point_id=f"{corner}_prototype_unsprung_cg",
            corner_id=corner,
            mass_kg=mass,
            source_position_m=point,
            body_position_m=None,
            source_id=record_id,
            configuration_id=configuration_id,
            assumption_id=assumption_id,
            authority="ASM-VEH-0003 prototype wheel-center lump",
        )
        for corner, mass, point in zip(corner_order, masses, wheel_points)
    )
    sprung = GravityPointMass(
        point_id="sprung_body_cg",
        corner_id=None,
        mass_kg=sprung_mass,
        source_position_m=sprung_cg,
        body_position_m=body_offset,  # body origin is the reviewed total-CG design reference
        source_id=record_id,
        configuration_id=configuration_id,
        assumption_id=assumption_id,
        authority="AUTH-VEH-0005 derived design-intent sprung body",
    )
    result = WUFRStaticGravityAllocation(
        record_id=record_id,
        configuration_id=configuration_id,
        state_id=state_id,
        assumption_id=assumption_id,
        total_mass_kg=total_mass,
        total_cg_source_m=total_cg,
        sprung=sprung,
        unsprung=unsprung,  # type: ignore[arg-type]
        g_mps2=float(gravity["g_mps2"]),
        source_authority=authority,
        installed_as_built_authority=bool(boundaries["installed_as_built_authority"]),
        maneuver_unsprung_inertia_authority=bool(boundaries["maneuver_unsprung_inertia_authority"]),
    )
    if not math.isclose(result.reconstructed_total_mass_kg, result.total_mass_kg, rel_tol=0.0, abs_tol=1.0e-12):
        raise WUFRGravityError(WUFRGravityFailureCode.FIRST_MOMENT_MISMATCH, "Mass recombination failed")
    if max(abs(v) for v in result.first_moment_residual_kg_m()) > 1.0e-11:
        raise WUFRGravityError(WUFRGravityFailureCode.FIRST_MOMENT_MISMATCH, "First-moment recombination failed")
    return result
