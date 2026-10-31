"""Publish native front minimum-twist states through the steering pose contract.

Both frames use metres and +x forward/+y left/+z up. The explicit origin
translation maps axle-local suspension points into the steering geometry frame.
This adapter does not solve body motion, contact inclination, or wheel forces.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math

from pssd_suspension.geometry import Axle, Side, SuspensionGeometrySet
from pssd_suspension.kinematics import (
    SuspensionCornerStateResult,
    minimum_twist_upright_transform,
)

from .poses import PoseCoordinate, PoseDefinitionError, RigidTransform, SteeringPoseState

CANONICAL_AXES = "+x forward, +y vehicle left, +z upward; right-handed"


@dataclass(frozen=True)
class NativePoseFrameMap:
    """Explicit same-axis mapping: steering_point = suspension_point + offset."""

    steering_frame_id: str
    suspension_origin_in_steering_m: tuple[float, float, float]
    source_revision: str
    source_path: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (
            self.steering_frame_id, self.source_revision, self.source_path,
        )):
            raise PoseDefinitionError("Frame mapping requires frame, revision, and source path")
        offset = tuple(float(value) for value in self.suspension_origin_in_steering_m)
        if len(offset) != 3 or not all(math.isfinite(value) for value in offset):
            raise PoseDefinitionError("Origin offset must contain three finite metre values")
        object.__setattr__(self, "suspension_origin_in_steering_m", offset)


def build_native_front_pose(
    geometry: SuspensionGeometrySet,
    left: SuspensionCornerStateResult,
    right: SuspensionCornerStateResult,
    *,
    state_id: str,
    frame_map: NativePoseFrameMap,
) -> SteeringPoseState:
    """Adapt one paired front state, rejecting mismatches or added steering twist.

    Origin conversion conjugates the rigid transform: t_new = t + o - R o.
    Configuration and source authority must match across corners and the supplied
    geometry. Upstream solver authority is retained without maneuver promotion.
    """
    if geometry.canonical_axes != CANONICAL_AXES:
        raise PoseDefinitionError("Native pose adapter requires canonical same-axis frames")
    if not left.configuration_id or left.configuration_id != right.configuration_id:
        raise PoseDefinitionError("Front states require the same explicit configuration")
    transforms = []
    for state, side in ((left, Side.LEFT), (right, Side.RIGHT)):
        if not state.ok or state.axle is not Axle.FRONT or state.side is not side:
            raise PoseDefinitionError("Expected successful left/right front native states")
        if state.geometry_id != geometry.geometry_id or state.source_authority != geometry.authority:
            raise PoseDefinitionError("Native state geometry/source authority mismatch")
        transform = state.minimum_twist_transform
        if (transform is None or state.lower_upright_m is None
                or state.upper_upright_m is None):
            raise PoseDefinitionError("Native state is missing its zero-steer transform/joints")
        if transform.source_role != "minimum_twist_zero_steer_reference":
            raise PoseDefinitionError("Native pose must exclude tie-rod steering rotation")
        corner = geometry.corner(Axle.FRONT, side)
        expected = minimum_twist_upright_transform(
            corner.wishbone.lower_upright.position_m,
            corner.wishbone.upper_upright.position_m,
            state.lower_upright_m, state.upper_upright_m,
        )
        # Verify minimum twist independently of the role label, including hidden
        # rotations about the kingpin which leave both upright joints unchanged.
        actual = tuple(x for row in transform.rotation for x in row) + transform.translation_m
        wanted = tuple(x for row in expected.rotation for x in row) + expected.translation_m
        if any(not math.isfinite(a) or abs(a - b) > 1.0e-10 for a, b in zip(actual, wanted)):
            raise PoseDefinitionError("Native transform differs from minimum twist")
        offset = frame_map.suspension_origin_in_steering_m
        rotated_offset = tuple(sum(a * b for a, b in zip(row, offset)) for row in transform.rotation)
        transforms.append(RigidTransform(
            rotation=transform.rotation,
            translation_m=tuple(t + o - r for t, o, r in zip(
                transform.translation_m, offset, rotated_offset,
            )),
            source_role="native_front_minimum_twist_unresolved_steering",
        ))
    provenance = json.dumps({
        "geometry_id": geometry.geometry_id,
        "configuration_id": left.configuration_id,
        "geometry_source_catalog": geometry.source.catalog_id,
        "geometry_source_version": geometry.source.file_version_id,
        "geometry_source_frame": geometry.source.source_frame_id,
        "frame_mapping_source": frame_map.source_path,
        "source_revision": frame_map.source_revision,
        "steering_frame_id": frame_map.steering_frame_id,
        "suspension_origin_in_steering_m": frame_map.suspension_origin_in_steering_m,
    }, sort_keys=True)
    return SteeringPoseState(
        state_id=state_id, left_transform=transforms[0], right_transform=transforms[1],
        coordinates=(PoseCoordinate("front_left_q_L", left.requested_q_L_rad, "rad"),
                     PoseCoordinate("front_right_q_L", right.requested_q_L_rad, "rad")),
        source_type="native_suspension_minimum_twist", source_path=provenance,
        authority=geometry.authority,
    )
