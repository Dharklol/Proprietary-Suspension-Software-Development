"""Canonical suspension-pose provider contract for steering studies.

The pose layer contains no suspension kinematics solver. A provider supplies the
rigid pose of each upright reference frame for a named suspension state while
leaving the steering degree of freedom unresolved. The existing MOD-STEER-0001
tie-rod closure solver remains responsible for the steering rotation required at
that suspension state.

This separation is deliberate: importing a pose that already includes tie-rod
steering rotation and then solving tie-rod closure again would double count bump
steer. Sources must therefore declare the steering-DOF rule explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
import tomllib

from ..core import (
    AxisLine,
    PositionResult,
    SteeringCorner,
    SteeringGeometry,
    Vec3,
    normalize,
    solve_corner_position,
)
from ..projection import WheelPlaneReference
from .geometry import GeneratedSteeringGeometry

Mat3 = tuple[Vec3, Vec3, Vec3]

STEERING_DOF_RULE = "upright_reference_pose_excludes_tie_rod_steering_rotation"


class PoseDefinitionError(ValueError):
    """Raised when a supplied suspension-pose definition violates the contract."""


def _vec3(value: object, *, name: str) -> Vec3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise PoseDefinitionError(f"{name} must contain three values")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise PoseDefinitionError(f"{name} must contain finite values")
    return result  # type: ignore[return-value]


def _mat3(value: object, *, name: str) -> Mat3:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise PoseDefinitionError(f"{name} must contain three rows")
    rows = tuple(_vec3(row, name=f"{name} row") for row in value)
    return rows  # type: ignore[return-value]


def _dot(a: Vec3, b: Vec3) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _mat_vec(matrix: Mat3, vector: Vec3) -> Vec3:
    return tuple(_dot(row, vector) for row in matrix)  # type: ignore[return-value]


def _determinant(matrix: Mat3) -> float:
    a, b, c = matrix
    return _dot(a, _cross(b, c))


@dataclass(frozen=True)
class RigidTransform:
    """Right-handed rigid transform from the nominal upright frame to one state."""

    rotation: Mat3
    translation_m: Vec3
    source_role: str = "provider_supplied"
    orthonormal_tolerance: float = 1.0e-10

    def __post_init__(self) -> None:
        rotation = _mat3(self.rotation, name="rotation")
        translation = _vec3(self.translation_m, name="translation_m")
        tolerance = float(self.orthonormal_tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise PoseDefinitionError("orthonormal_tolerance must be finite and positive")
        for index, row in enumerate(rotation):
            norm = math.sqrt(_dot(row, row))
            if abs(norm - 1.0) > tolerance:
                raise PoseDefinitionError(f"rotation row {index} is not unit length")
        if max(abs(_dot(rotation[i], rotation[j])) for i in range(3) for j in range(i)) > tolerance:
            raise PoseDefinitionError("rotation rows are not mutually orthogonal")
        determinant = _determinant(rotation)
        if abs(determinant - 1.0) > 10.0 * tolerance:
            raise PoseDefinitionError("rotation must be right-handed with determinant +1")
        object.__setattr__(self, "rotation", rotation)
        object.__setattr__(self, "translation_m", translation)
        object.__setattr__(self, "orthonormal_tolerance", tolerance)

    @classmethod
    def identity(cls, *, source_role: str = "identity") -> "RigidTransform":
        return cls(
            rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            translation_m=(0.0, 0.0, 0.0),
            source_role=source_role,
        )

    def is_identity(self, *, tolerance: float = 1.0e-12) -> bool:
        identity = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        return all(
            abs(actual - expected) <= tolerance
            for row, expected_row in zip(self.rotation, identity)
            for actual, expected in zip(row, expected_row)
        ) and all(abs(value) <= tolerance for value in self.translation_m)

    def apply_point(self, point: Vec3) -> Vec3:
        rotated = _mat_vec(self.rotation, _vec3(point, name="point"))
        return tuple(a + b for a, b in zip(rotated, self.translation_m))  # type: ignore[return-value]

    def apply_direction(self, direction: Vec3) -> Vec3:
        return normalize(_mat_vec(self.rotation, _vec3(direction, name="direction")))


@dataclass(frozen=True)
class PoseCoordinate:
    """One descriptive suspension-state coordinate supplied by the provider."""

    id: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.id:
            raise PoseDefinitionError("Pose coordinate id is required")
        if not self.unit:
            raise PoseDefinitionError(f"Pose coordinate {self.id!r} requires a unit")
        if not math.isfinite(self.value):
            raise PoseDefinitionError(f"Pose coordinate {self.id!r} must be finite")


@dataclass(frozen=True)
class SteeringPoseState:
    """Canonical zero-steer upright pose for one named suspension state."""

    state_id: str
    left_transform: RigidTransform
    right_transform: RigidTransform
    coordinates: tuple[PoseCoordinate, ...] = ()
    source_type: str = "synthetic"
    source_path: str = ""
    authority: str = "software_verification_only"
    steering_dof_rule: str = STEERING_DOF_RULE

    def __post_init__(self) -> None:
        if not self.state_id:
            raise PoseDefinitionError("state_id is required")
        if self.steering_dof_rule != STEERING_DOF_RULE:
            raise PoseDefinitionError(
                "Pose source must exclude tie-rod steering rotation; sources that already include "
                "bump-steer/toe response are validation evidence, not steering-evaluator inputs"
            )
        ids = [item.id for item in self.coordinates]
        if len(ids) != len(set(ids)):
            raise PoseDefinitionError(f"Pose state {self.state_id!r} has duplicate coordinates")

    @property
    def coordinate_map(self) -> dict[str, PoseCoordinate]:
        return {item.id: item for item in self.coordinates}

    @property
    def is_identity_pose(self) -> bool:
        return self.left_transform.is_identity() and self.right_transform.is_identity()


@dataclass(frozen=True)
class SuspensionPoseSet:
    """Provider-neutral collection of named suspension states."""

    pose_set_id: str
    version: str
    nominal_state_id: str
    states: tuple[SteeringPoseState, ...]
    source_path: str
    authority: str

    def __post_init__(self) -> None:
        if not self.pose_set_id:
            raise PoseDefinitionError("pose_set_id is required")
        ids = [item.state_id for item in self.states]
        if not ids or len(ids) != len(set(ids)):
            raise PoseDefinitionError("Pose set requires unique named states")
        if self.nominal_state_id not in ids:
            raise PoseDefinitionError("nominal_state_id must identify one supplied state")

    @property
    def state_map(self) -> dict[str, SteeringPoseState]:
        return {item.state_id: item for item in self.states}

    def state(self, state_id: str) -> SteeringPoseState:
        try:
            return self.state_map[state_id]
        except KeyError as exc:
            raise PoseDefinitionError(f"Unknown suspension pose state {state_id!r}") from exc


@dataclass(frozen=True)
class PosedSteeringGeometry:
    """One generated candidate expressed at a supplied suspension pose."""

    state: SteeringPoseState
    geometry: SteeringGeometry
    left_center_result: PositionResult
    right_center_result: PositionResult


def transform_wheel_plane(reference: WheelPlaneReference, transform: RigidTransform) -> WheelPlaneReference:
    """Rotate a nominal wheel-plane reference into the supplied zero-steer pose."""

    return WheelPlaneReference(
        side=reference.side,
        normal_at_center=transform.apply_direction(reference.normal_at_center),
        forward_at_center=transform.apply_direction(reference.forward_at_center),
        source_role=f"pose_transformed:{transform.source_role}:{reference.source_role}",
    )


def _transform_corner(corner: SteeringCorner, transform: RigidTransform, *, state_id: str) -> SteeringCorner:
    forward = corner.wheel_forward_direction_at_center
    transformed_forward = transform.apply_direction(forward) if forward is not None else None
    return replace(
        corner,
        steering_axis=AxisLine(
            point=transform.apply_point(corner.steering_axis.point),
            direction=transform.apply_direction(corner.steering_axis.direction),
        ),
        outer_tie_rod_joint_at_center=transform.apply_point(corner.outer_tie_rod_joint_at_center),
        wheel_forward_direction_at_center=transformed_forward,
        source_role=f"pose_state:{state_id}:{corner.source_role}",
    )


def apply_pose_state(
    generated: GeneratedSteeringGeometry,
    state: SteeringPoseState,
) -> PosedSteeringGeometry:
    """Apply one zero-steer suspension pose to an already generated candidate.

    Rack geometry and rack inner joints remain chassis-fixed. Upright-bound steering
    axes, outer tie-rod joints, and wheel-forward directions move rigidly with the
    provider transform. Tie-rod length remains the nominal generated length.

    The transformed geometry is intentionally *not* required to close at zero upright
    rotation. Center results are returned even when closure is infeasible so the
    operating-state evaluator can distinguish a valid pose definition from an
    infeasible steering mechanism state.
    """

    nominal = generated.geometry
    left = _transform_corner(nominal.left, state.left_transform, state_id=state.state_id)
    right = _transform_corner(nominal.right, state.right_transform, state_id=state.state_id)
    metadata = dict(nominal.metadata)
    metadata.update(
        {
            "suspension_pose_state_id": state.state_id,
            "suspension_pose_source_type": state.source_type,
            "suspension_pose_source_path": state.source_path,
            "suspension_pose_authority": state.authority,
            "suspension_pose_steering_dof_rule": state.steering_dof_rule,
            "suspension_pose_coordinates": ";".join(
                f"{item.id}={item.value:.17g} {item.unit}" for item in state.coordinates
            ),
            "steering_axis_track_role": (
                "nominal_identity_preserved"
                if state.is_identity_pose
                else "unavailable_at_non_nominal_pose_until_rederived"
            ),
        }
    )
    geometry = SteeringGeometry(
        geometry_id=f"{nominal.geometry_id}:POSE:{state.state_id}",
        version=nominal.version,
        rack=nominal.rack,
        left=left,
        right=right,
        wheelbase=nominal.wheelbase,
        steering_axis_track=(nominal.steering_axis_track if state.is_identity_pose else None),
        metadata=metadata,
    )

    left_center = solve_corner_position(geometry, "left", 0.0)
    right_center = solve_corner_position(geometry, "right", 0.0)
    return PosedSteeringGeometry(
        state=state,
        geometry=geometry,
        left_center_result=left_center,
        right_center_result=right_center,
    )


def load_pose_set(path: str | Path) -> SuspensionPoseSet:
    """Load a provider-neutral pose table from TOML."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    pose_set_id = str(document.get("pose_set_id", ""))
    version = str(document.get("version", "0"))
    nominal_state_id = str(document.get("nominal_state_id", ""))
    authority = str(document.get("authority", ""))
    steering_dof_rule = str(document.get("steering_dof_rule", ""))
    if steering_dof_rule != STEERING_DOF_RULE:
        raise PoseDefinitionError(
            f"Pose set {pose_set_id!r} must declare steering_dof_rule={STEERING_DOF_RULE!r}"
        )

    states: list[SteeringPoseState] = []
    for table in document.get("states", []):
        state_id = str(table.get("id", ""))
        coordinates = tuple(
            PoseCoordinate(
                id=str(item.get("id", "")),
                value=float(item.get("value")),
                unit=str(item.get("unit", "")),
            )
            for item in table.get("coordinates", [])
        )
        left_table = table.get("left_transform")
        right_table = table.get("right_transform")
        if not isinstance(left_table, dict) or not isinstance(right_table, dict):
            raise PoseDefinitionError(f"Pose state {state_id!r} requires left/right transforms")
        states.append(
            SteeringPoseState(
                state_id=state_id,
                left_transform=RigidTransform(
                    rotation=_mat3(left_table.get("rotation"), name=f"{state_id}.left.rotation"),
                    translation_m=_vec3(
                        left_table.get("translation_m"), name=f"{state_id}.left.translation_m"
                    ),
                    source_role=str(left_table.get("source_role", "provider_supplied")),
                ),
                right_transform=RigidTransform(
                    rotation=_mat3(right_table.get("rotation"), name=f"{state_id}.right.rotation"),
                    translation_m=_vec3(
                        right_table.get("translation_m"), name=f"{state_id}.right.translation_m"
                    ),
                    source_role=str(right_table.get("source_role", "provider_supplied")),
                ),
                coordinates=coordinates,
                source_type=str(table.get("source_type", document.get("source_type", "table"))),
                source_path=str(table.get("source_path", source_path)),
                authority=str(table.get("authority", authority)),
                steering_dof_rule=steering_dof_rule,
            )
        )
    return SuspensionPoseSet(
        pose_set_id=pose_set_id,
        version=version,
        nominal_state_id=nominal_state_id,
        states=tuple(states),
        source_path=str(source_path),
        authority=authority,
    )
