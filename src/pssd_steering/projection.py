"""Canonical wheel-plane projection for rigid steering geometry.

The projected road-wheel heading is the direction of the intersection between
an oriented wheel centre plane and the road plane.  The wheel-plane normal is
rotated with the upright about the declared steering axis; projecting a generic
"forward" vector is not equivalent when camber and an inclined steering axis
are present.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .core import GeometryError, SteeringCorner, Vec3, cross, dot, norm, normalize, rotate_direction_about_axis, scale

ROAD_NORMAL: Vec3 = (0.0, 0.0, 1.0)


@dataclass(frozen=True)
class WheelPlaneReference:
    """Frozen wheel-plane orientation at the centred reference state.

    ``normal_at_center`` may point to either side of the plane; ``forward_at_center``
    removes the 180-degree ambiguity from the plane/road intersection.
    """

    side: str
    normal_at_center: Vec3
    forward_at_center: Vec3
    source_role: str = "direct"

    def __post_init__(self) -> None:
        if self.side not in {"left", "right"}:
            raise GeometryError("Wheel-plane side must be 'left' or 'right'")
        normal = normalize(tuple(float(v) for v in self.normal_at_center))
        forward = normalize(tuple(float(v) for v in self.forward_at_center))
        if abs(dot(normal, forward)) > 1.0e-10:
            raise GeometryError("Wheel-plane normal and forward reference must be orthogonal")
        if math.hypot(forward[0], forward[1]) <= 1.0e-15:
            raise GeometryError("Forward reference has no usable road-plane projection")
        object.__setattr__(self, "normal_at_center", normal)
        object.__setattr__(self, "forward_at_center", forward)


def reference_from_static_alignment(
    side: str,
    *,
    toe_out: float,
    camber: float,
    source_role: str = "alignment_derived",
) -> WheelPlaneReference:
    """Construct a centred wheel plane from side-local toe and camber.

    Coordinate convention is ``+x`` forward, ``+y`` vehicle-left, ``+z`` up.
    ``toe_out`` is positive when the front of either wheel points away from the
    vehicle centreline. ``camber`` is positive when the wheel top leans outward.
    Angles are radians.
    """

    if side not in {"left", "right"}:
        raise GeometryError("Wheel-plane side must be 'left' or 'right'")
    if not math.isfinite(toe_out) or not math.isfinite(camber):
        raise GeometryError("Toe and camber must be finite")
    side_sign = 1.0 if side == "left" else -1.0
    heading = side_sign * toe_out
    forward = (math.cos(heading), math.sin(heading), 0.0)
    outward_horizontal = (-side_sign * math.sin(heading), side_sign * math.cos(heading), 0.0)
    # Positive camber (top outward) gives the outward normal a negative z component.
    normal = (
        math.cos(camber) * outward_horizontal[0],
        math.cos(camber) * outward_horizontal[1],
        -math.sin(camber),
    )
    return WheelPlaneReference(side, normal, forward, source_role)


def road_intersection_direction(
    plane_normal: Sequence[float],
    *,
    forward_hint: Sequence[float],
    road_normal: Sequence[float] = ROAD_NORMAL,
    minimum_norm: float = 1.0e-12,
) -> Vec3:
    """Return the forward-oriented plane/road intersection unit direction."""

    normal = normalize(tuple(float(v) for v in plane_normal))
    road = normalize(tuple(float(v) for v in road_normal))
    direction = cross(road, normal)
    magnitude = norm(direction)
    if magnitude <= minimum_norm:
        raise GeometryError("Wheel plane is parallel to the road plane; heading is undefined")
    direction = scale(direction, 1.0 / magnitude)
    hint = normalize(tuple(float(v) for v in forward_hint))
    if dot(direction, hint) < 0.0:
        direction = scale(direction, -1.0)
    return direction


def projected_wheel_heading(
    corner: SteeringCorner,
    reference: WheelPlaneReference,
    upright_rotation: float,
) -> tuple[float, float]:
    """Return total and centred-incremental road-wheel heading in radians."""

    if corner.side != reference.side:
        raise GeometryError("Corner and wheel-plane reference sides do not match")
    delta = upright_rotation - corner.reference_upright_rotation
    current_normal = rotate_direction_about_axis(
        reference.normal_at_center, corner.steering_axis.direction, delta
    )
    current_forward_hint = rotate_direction_about_axis(
        reference.forward_at_center, corner.steering_axis.direction, delta
    )
    current_direction = road_intersection_direction(
        current_normal, forward_hint=current_forward_hint
    )
    reference_direction = road_intersection_direction(
        reference.normal_at_center, forward_hint=reference.forward_at_center
    )
    total = math.atan2(current_direction[1], current_direction[0])
    reference_heading = math.atan2(reference_direction[1], reference_direction[0])
    incremental = math.atan2(
        math.sin(total - reference_heading), math.cos(total - reference_heading)
    )
    return total, incremental
