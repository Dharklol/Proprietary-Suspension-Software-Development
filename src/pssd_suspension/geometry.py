"""Source-preserving suspension geometry contract.

This module contains no suspension kinematics equations.  It converts explicitly
identified source hardpoints into the canonical project orientation and preserves
both source and canonical coordinates so a later solver can consume reviewed
geometry without reinterpreting vendor axes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Mapping

Point3 = tuple[float, float, float]
Mat3 = tuple[Point3, Point3, Point3]

CANONICAL_AXES = "+x forward, +y vehicle left, +z upward; right-handed"


class SuspensionGeometryError(ValueError):
    """Raised when a suspension geometry source violates the exchange contract."""


class Axle(str, Enum):
    FRONT = "front"
    REAR = "rear"


class Side(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class ToeLinkRole(str, Enum):
    """Role of the source's chassis-to-upright lateral link."""

    STEERING_TIE_ROD = "steering_tie_rod"
    CHASSIS_LOCATING_TOE_LINK = "chassis_locating_toe_link"


class ActuationAttachment(str, Enum):
    UPPER_ARM = "upper_arm"
    LOWER_ARM = "lower_arm"


def _point3(value: object, *, name: str) -> Point3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SuspensionGeometryError(f"{name} must contain exactly three values")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise SuspensionGeometryError(f"{name} must contain finite values")
    return result  # type: ignore[return-value]


def _mat3(value: object, *, name: str) -> Mat3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SuspensionGeometryError(f"{name} must contain exactly three rows")
    return tuple(_point3(row, name=f"{name} row") for row in value)  # type: ignore[return-value]


def _mat_vec(matrix: Mat3, vector: Point3) -> Point3:
    return tuple(sum(row[i] * vector[i] for i in range(3)) for row in matrix)  # type: ignore[return-value]


def _require_text(mapping: Mapping[str, object], key: str, *, context: str) -> str:
    value = str(mapping.get(key, ""))
    if not value:
        raise SuspensionGeometryError(f"{context} requires {key}")
    return value


@dataclass(frozen=True)
class SourceIdentity:
    catalog_id: str
    provider: str
    file_name: str
    file_id: str
    file_version_id: str
    provider_sha1: str
    source_frame_id: str
    extraction_method: str
    raw_byte_sha256_state: str

    def __post_init__(self) -> None:
        for field_name in (
            "catalog_id",
            "provider",
            "file_name",
            "file_id",
            "file_version_id",
            "provider_sha1",
            "source_frame_id",
            "extraction_method",
            "raw_byte_sha256_state",
        ):
            if not getattr(self, field_name):
                raise SuspensionGeometryError(f"Source identity requires {field_name}")


@dataclass(frozen=True)
class SuspensionPoint:
    """One hardpoint with source coordinates and canonical coordinates."""

    source_name: str
    source_position_mm: Point3
    position_m: Point3


@dataclass(frozen=True)
class DoubleWishboneGeometry:
    lower_fore_inboard: SuspensionPoint
    lower_aft_inboard: SuspensionPoint
    upper_fore_inboard: SuspensionPoint
    upper_aft_inboard: SuspensionPoint
    lower_upright: SuspensionPoint
    upper_upright: SuspensionPoint

    @property
    def steering_or_kingpin_axis_points(self) -> tuple[Point3, Point3]:
        return (self.lower_upright.position_m, self.upper_upright.position_m)


@dataclass(frozen=True)
class ToeLinkGeometry:
    inboard: SuspensionPoint
    outboard: SuspensionPoint
    role: ToeLinkRole


@dataclass(frozen=True)
class ActuationGeometry:
    outboard_attachment: SuspensionPoint
    chassis_attachment: SuspensionPoint
    rocker_axis_reference: SuspensionPoint
    rocker_pivot: SuspensionPoint
    rocker_rod_point: SuspensionPoint
    rocker_coil_point: SuspensionPoint
    attachment: ActuationAttachment


@dataclass(frozen=True)
class WheelSetup:
    half_track_m: float
    longitudinal_offset_m: float
    lateral_offset_m: float
    vertical_offset_m: float
    static_camber_deg: float
    static_toe_deg: float
    rim_diameter_m: float
    tire_diameter_m: float
    tire_width_m: float

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in self.__dict__.values())
        if not all(math.isfinite(value) for value in values):
            raise SuspensionGeometryError("Wheel setup values must be finite")
        if self.half_track_m <= 0.0 or self.rim_diameter_m <= 0.0 or self.tire_diameter_m <= 0.0:
            raise SuspensionGeometryError("Wheel half-track and diameters must be positive")
        if self.tire_width_m <= 0.0:
            raise SuspensionGeometryError("Tire width must be positive")


@dataclass(frozen=True)
class SuspensionCornerGeometry:
    axle: Axle
    side: Side
    wishbone: DoubleWishboneGeometry
    toe_link: ToeLinkGeometry
    actuation: ActuationGeometry
    wheel_setup: WheelSetup


@dataclass(frozen=True)
class SuspensionGeometrySet:
    """Nominal source geometry for four corners in axle-local canonical orientation.

    Front and rear coordinates retain their source suspension-reference origins.
    ``reference_distance_m`` is stored separately; this contract does not silently
    translate rear hardpoints into a whole-vehicle origin.
    """

    geometry_id: str
    version: str
    authority: str
    source: SourceIdentity
    canonical_axes: str
    reference_distance_m: float
    corners: tuple[SuspensionCornerGeometry, ...]
    wheel_center_rule: str

    def __post_init__(self) -> None:
        for field_name in ("geometry_id", "version", "authority", "canonical_axes", "wheel_center_rule"):
            if not getattr(self, field_name):
                raise SuspensionGeometryError(f"Suspension geometry set requires {field_name}")
        if not math.isfinite(self.reference_distance_m) or self.reference_distance_m <= 0.0:
            raise SuspensionGeometryError("reference_distance_m must be finite and positive")
        keys = [(corner.axle, corner.side) for corner in self.corners]
        expected = {(axle, side) for axle in Axle for side in Side}
        if len(keys) != 4 or set(keys) != expected:
            raise SuspensionGeometryError("Geometry set requires exactly one corner for each axle/side")

    @property
    def corner_map(self) -> dict[tuple[Axle, Side], SuspensionCornerGeometry]:
        return {(corner.axle, corner.side): corner for corner in self.corners}

    def corner(self, axle: Axle | str, side: Side | str) -> SuspensionCornerGeometry:
        axle_key = axle if isinstance(axle, Axle) else Axle(axle)
        side_key = side if isinstance(side, Side) else Side(side)
        return self.corner_map[(axle_key, side_key)]


def _source_point(
    name: str,
    raw_value: object,
    *,
    matrix: Mat3,
    scale_to_m: float,
) -> SuspensionPoint:
    source_mm = _point3(raw_value, name=name)
    oriented = _mat_vec(matrix, source_mm)
    position_m = tuple(scale_to_m * value for value in oriented)
    return SuspensionPoint(
        source_name=name,
        source_position_mm=source_mm,
        position_m=position_m,  # type: ignore[arg-type]
    )


def _wheel_setup(table: Mapping[str, object]) -> WheelSetup:
    def mm(key: str) -> float:
        return 0.001 * float(table[key])

    return WheelSetup(
        half_track_m=mm("half_track_mm"),
        longitudinal_offset_m=mm("longitudinal_offset_mm"),
        lateral_offset_m=mm("lateral_offset_mm"),
        vertical_offset_m=mm("vertical_offset_mm"),
        static_camber_deg=float(table["static_camber_deg"]),
        static_toe_deg=float(table["static_toe_deg"]),
        rim_diameter_m=mm("rim_diameter_mm"),
        tire_diameter_m=mm("tire_diameter_mm"),
        tire_width_m=mm("tire_width_mm"),
    )


def load_optimumk_geometry_snapshot(path: str | Path) -> SuspensionGeometrySet:
    """Load the frozen WUFR OptimumK hardpoint snapshot.

    Conversion is limited to the transform explicitly declared in the snapshot.
    No symmetry, wheel-center, full-vehicle-origin, steering, or kinematic-state
    inference is performed by this loader.
    """

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)

    source_table = document.get("source")
    transform_table = document.get("transform")
    if not isinstance(source_table, dict) or not isinstance(transform_table, dict):
        raise SuspensionGeometryError("Snapshot requires [source] and [transform] tables")

    matrix = _mat3(transform_table.get("source_to_canonical_matrix"), name="source_to_canonical_matrix")
    scale_to_m = float(transform_table.get("source_length_scale_to_m", math.nan))
    if not math.isfinite(scale_to_m) or scale_to_m <= 0.0:
        raise SuspensionGeometryError("source_length_scale_to_m must be finite and positive")

    source = SourceIdentity(
        catalog_id=_require_text(source_table, "catalog_id", context="source"),
        provider=_require_text(source_table, "provider", context="source"),
        file_name=_require_text(source_table, "file_name", context="source"),
        file_id=_require_text(source_table, "file_id", context="source"),
        file_version_id=_require_text(source_table, "file_version_id", context="source"),
        provider_sha1=_require_text(source_table, "provider_sha1", context="source"),
        source_frame_id=_require_text(source_table, "source_frame_id", context="source"),
        extraction_method=_require_text(source_table, "extraction_method", context="source"),
        raw_byte_sha256_state=_require_text(source_table, "raw_byte_sha256_state", context="source"),
    )

    corners: list[SuspensionCornerGeometry] = []
    required_wishbone = {
        "CHAS_LowFor": "lower_fore_inboard",
        "CHAS_LowAft": "lower_aft_inboard",
        "CHAS_UppFor": "upper_fore_inboard",
        "CHAS_UppAft": "upper_aft_inboard",
        "UPRI_LowPnt": "lower_upright",
        "UPRI_UppPnt": "upper_upright",
    }
    required_actuation = (
        "NSMA_PPAttPnt_L",
        "CHAS_AttPnt_L",
        "CHAS_RocAxi_L",
        "CHAS_RocPiv_L",
        "ROCK_RodPnt_L",
        "ROCK_CoiPnt_L",
    )

    for axle in Axle:
        axle_table = document.get(axle.value)
        if not isinstance(axle_table, dict):
            raise SuspensionGeometryError(f"Snapshot requires [{axle.value}] table")
        role = ToeLinkRole(str(axle_table.get("toe_link_role", "")))
        attachment = ActuationAttachment(str(axle_table.get("actuation_attachment", "")))
        wheel_table = axle_table.get("wheel_setup")
        if not isinstance(wheel_table, dict):
            raise SuspensionGeometryError(f"{axle.value} requires wheel_setup")
        setup = _wheel_setup(wheel_table)

        for side in Side:
            side_table = axle_table.get(side.value)
            if not isinstance(side_table, dict):
                raise SuspensionGeometryError(f"{axle.value}.{side.value} table is required")
            points_table = side_table.get("points")
            actuation_table = side_table.get("actuation_points")
            if not isinstance(points_table, dict) or not isinstance(actuation_table, dict):
                raise SuspensionGeometryError(
                    f"{axle.value}.{side.value} requires points and actuation_points"
                )

            points = {
                name: _source_point(
                    name,
                    points_table[name],
                    matrix=matrix,
                    scale_to_m=scale_to_m,
                )
                for name in (*required_wishbone.keys(), "CHAS_TiePnt", "UPRI_TiePnt")
            }
            actuation_points = {
                name: _source_point(
                    name,
                    actuation_table[name],
                    matrix=matrix,
                    scale_to_m=scale_to_m,
                )
                for name in required_actuation
            }
            wishbone_kwargs = {
                field_name: points[source_name]
                for source_name, field_name in required_wishbone.items()
            }
            corners.append(
                SuspensionCornerGeometry(
                    axle=axle,
                    side=side,
                    wishbone=DoubleWishboneGeometry(**wishbone_kwargs),
                    toe_link=ToeLinkGeometry(
                        inboard=points["CHAS_TiePnt"],
                        outboard=points["UPRI_TiePnt"],
                        role=role,
                    ),
                    actuation=ActuationGeometry(
                        outboard_attachment=actuation_points["NSMA_PPAttPnt_L"],
                        chassis_attachment=actuation_points["CHAS_AttPnt_L"],
                        rocker_axis_reference=actuation_points["CHAS_RocAxi_L"],
                        rocker_pivot=actuation_points["CHAS_RocPiv_L"],
                        rocker_rod_point=actuation_points["ROCK_RodPnt_L"],
                        rocker_coil_point=actuation_points["ROCK_CoiPnt_L"],
                        attachment=attachment,
                    ),
                    wheel_setup=setup,
                )
            )

    return SuspensionGeometrySet(
        geometry_id=str(document.get("snapshot_id", "")),
        version=str(document.get("version", "")),
        authority=str(document.get("authority", "")),
        source=source,
        canonical_axes=str(transform_table.get("canonical_axes", "")),
        reference_distance_m=0.001 * float(document.get("reference_distance_mm", math.nan)),
        corners=tuple(corners),
        wheel_center_rule=str(document.get("wheel_center_rule", "")),
    )
