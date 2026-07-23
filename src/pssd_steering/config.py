"""TOML loaders for frozen and inherited steering geometry configurations."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import math
import tomllib

from .core import AxisLine, RackGeometry, SteeringCorner, SteeringGeometry, subtract


def _tuple3(value) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"Expected a three-value TOML array, got {value!r}")
    return (float(value[0]), float(value[1]), float(value[2]))


def _axis_from_corner(table: dict) -> AxisLine:
    if "steering_axis_point" in table:
        return AxisLine(_tuple3(table["steering_axis_point"]), _tuple3(table["steering_axis_direction"]))
    lower = _tuple3(table["steering_axis_lower_point"])
    upper = _tuple3(table["steering_axis_upper_point"])
    return AxisLine(lower, subtract(upper, lower))


def _optional_direction(value) -> tuple[float, float, float] | None:
    if isinstance(value, list):
        return _tuple3(value)
    return None


def _resolve_inherited_path(reference_path: Path, declared_path: str) -> Path:
    candidate = Path(declared_path)
    if candidate.is_absolute():
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    for ancestor in (reference_path.parent, *reference_path.parents):
        resolved = ancestor / candidate
        if resolved.is_file():
            return resolved
    raise FileNotFoundError(
        f"Cannot resolve inherited steering configuration {declared_path!r} "
        f"from {reference_path}"
    )


def _load_direct_geometry(document: dict, source_path: Path) -> SteeringGeometry:
    geometry_id = str(document.get("geometry_id") or document.get("configuration_id"))
    version = str(document.get("version", "0"))
    rack_table = document["rack"]
    rack_axis = AxisLine(
        _tuple3(rack_table["axis_origin"]),
        _tuple3(rack_table["axis_direction"]),
    )
    branch_limit = rack_table.get("geometric_branch_limit_magnitude")
    rack = RackGeometry(
        axis=rack_axis,
        displacement_min=float(rack_table["operational_displacement_min"]),
        displacement_max=float(rack_table["operational_displacement_max"]),
        geometric_branch_limit_magnitude=(float(branch_limit) if branch_limit is not None else None),
        domain_role=str(rack_table.get("operational_domain_role", "reviewed")),
    )

    def corner(side: str) -> SteeringCorner:
        table = document[side]
        inner_key = f"{side}_inner_joint_at_center"
        inner = _tuple3(rack_table[inner_key])
        return SteeringCorner(
            side=side,
            steering_axis=_axis_from_corner(table),
            rack_inner_joint_at_center=inner,
            outer_tie_rod_joint_at_center=_tuple3(table["outer_tie_rod_joint_at_center"]),
            tie_rod_length=float(table["nominal_tie_rod_length"]),
            reference_upright_rotation=float(table.get("reference_branch_upright_rotation", 0.0)),
            mechanical_rotation_min=float(table.get("mechanical_angle_min", -1.0)),
            mechanical_rotation_max=float(table.get("mechanical_angle_max", 1.0)),
            wheel_forward_direction_at_center=_optional_direction(
                table.get("wheel_forward_direction_at_center")
            ),
            static_toe=(
                float(table["static_toe"])
                if isinstance(table.get("static_toe"), (int, float))
                and math.isfinite(float(table["static_toe"]))
                else None
            ),
            source_role=str(table.get("side_role", "direct")),
        )

    vehicle = document.get("vehicle", {})
    return SteeringGeometry(
        geometry_id=geometry_id,
        version=version,
        rack=rack,
        left=corner("left"),
        right=corner("right"),
        wheelbase=(float(vehicle["wheelbase"]) if "wheelbase" in vehicle else None),
        steering_axis_track=(
            float(vehicle["steering_axis_ground_intersection_track"])
            if "steering_axis_ground_intersection_track" in vehicle
            else None
        ),
        metadata={
            "source_path": str(source_path),
            "status": str(document.get("status", "unknown")),
        },
    )


def load_geometry(
    path: str | Path, *, _visited: frozenset[Path] | None = None
) -> SteeringGeometry:
    """Load a frozen, candidate, or explicitly inherited geometry.

    Inheritance is source-preserving: the referenced geometry is loaded without
    numerical overrides, then receives the inheriting configuration identity and
    provenance. Any numerical change requires a separate explicit configuration.
    """

    source_path = Path(path).resolve()
    visited = _visited or frozenset()
    if source_path in visited:
        raise ValueError(f"Steering configuration inheritance cycle at {source_path}")
    visited = visited | {source_path}

    with source_path.open("rb") as stream:
        document = tomllib.load(stream)

    if "rack" in document:
        return _load_direct_geometry(document, source_path)

    inheritance = document.get("inheritance")
    if not isinstance(inheritance, dict) or "source_path" not in inheritance:
        raise ValueError(
            f"Steering configuration {source_path} has neither direct geometry nor inheritance"
        )
    inherited_path = _resolve_inherited_path(source_path, str(inheritance["source_path"]))
    inherited = load_geometry(inherited_path, _visited=visited)
    geometry_id = str(document.get("geometry_id") or document.get("configuration_id"))
    if not geometry_id:
        raise ValueError(f"Inherited steering configuration {source_path} requires an id")
    metadata = dict(inherited.metadata)
    metadata.update(
        {
            "source_path": str(source_path),
            "status": str(document.get("status", "unknown")),
            "inherited_geometry_id": inherited.geometry_id,
            "inherited_geometry_version": inherited.version,
            "inherited_source_path": str(inherited_path),
            "inheritance_rule": str(inheritance.get("rule", "exact numerical inheritance")),
        }
    )
    return replace(
        inherited,
        geometry_id=geometry_id,
        version=str(document.get("version", "0")),
        metadata=metadata,
    )
