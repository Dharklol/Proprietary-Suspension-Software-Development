"""Full rigid-upright steering transport for the development maneuver adapter.

Inputs share the source suspension/steering axle frame, metres, and x-forward,
y-left, z-up axes. Frame reconciliation belongs to the caller. This slice does
not assign tire inclination signs or provide road compatibility/equilibrium.
"""
from dataclasses import dataclass, replace
import math

from pssd_suspension import Axle
from pssd_suspension.wheel_reference import WheelReferenceState
from pssd_steering import AxisLine, SteeringCorner, SteeringGeometry, solve_corner_position
from pssd_steering.core import dot, cross, normalize, rotate_direction_about_axis, rotate_point_about_axis
from pssd_steering.projection import road_intersection_direction


@dataclass(frozen=True)
class SteeredUpright:
    wheel_state: WheelReferenceState
    steering_axis: AxisLine | None
    steering_rotation_rad: float
    closure_residual_m: float | None
    steering_owner: str

    def transport_point(self, nominal_point):
        upstream = self.wheel_state.upstream_state
        transform = (upstream.minimum_twist_transform if self.wheel_state.axle is Axle.FRONT
                     else upstream.upright_transform)
        point = transform.apply_point(nominal_point)
        return (rotate_point_about_axis(point, self.steering_axis, self.steering_rotation_rad)
                if self.steering_axis is not None else point)

    def transport_direction(self, nominal_direction):
        upstream = self.wheel_state.upstream_state
        transform = (upstream.minimum_twist_transform if self.wheel_state.axle is Axle.FRONT
                     else upstream.upright_transform)
        direction = transform.apply_direction(nominal_direction)
        return (rotate_direction_about_axis(direction, self.steering_axis.direction,
                                            self.steering_rotation_rad)
                if self.steering_axis is not None else direction)

    @property
    def center_m(self):
        return self.transport_point(self.wheel_state.nominal.center_m)

    @property
    def plane_normal(self):
        return self.transport_direction(self.wheel_state.nominal.plane_normal)

    def road_heading(self, road_normal=(0.0, 0.0, 1.0)):
        return road_intersection_direction(
            self.plane_normal,
            forward_hint=self.transport_direction(self.wheel_state.nominal.forward_reference),
            road_normal=road_normal,
        )

    def signed_inclination_rad(self, road_normal=(0.0, 0.0, 1.0)):
        """SAE J670 / reviewed unchanged-IA polarity: top leaning right positive.

        Orient the plane normal toward contact-frame left before measuring its
        right-handed rotation about forward. This handles outward source normals
        on both sides without taking an absolute value of inclination.
        """
        road = normalize(road_normal)
        left = cross(road, self.road_heading(road))
        normal = self.plane_normal
        polarity = 1.0 if dot(normal, left) > 0 else -1.0
        return math.atan2(polarity * dot(normal, road), polarity * dot(normal, left))


def close_native_upright(wheel_state: WheelReferenceState, steering: SteeringGeometry,
                         rack_displacement_m: float) -> SteeredUpright:
    """Apply front tie-rod closure once; preserve rear native toe-link closure.

    The input wheel coordinate remains the native pre-steering reference
    displacement. The resulting actual center may move vertically under steer.
    """
    if not math.isfinite(rack_displacement_m):
        raise ValueError("Rack displacement must be finite")
    upstream = wheel_state.upstream_state
    if not wheel_state.ok or upstream is None or not upstream.ok:
        raise ValueError("A successful native wheel and upright state is required")
    if wheel_state.axle is Axle.REAR:
        if wheel_state.transform_role != "rear_chassis_toe_link_closed" or upstream.upright_transform is None:
            raise ValueError("Rear native toe-link closure is required")
        return SteeredUpright(wheel_state, None, 0.0, None, "rear_native_toe_link")
    transform = upstream.minimum_twist_transform
    if (wheel_state.transform_role != "front_minimum_twist_unresolved_steering"
            or transform is None or transform.source_role != "minimum_twist_zero_steer_reference"):
        raise ValueError("Front closure requires the unresolved minimum-twist reference")
    side = wheel_state.side.value
    original = steering.left if side == "left" else steering.right
    axis = AxisLine(transform.apply_point(original.steering_axis.point),
                    transform.apply_direction(original.steering_axis.direction))
    corner = SteeringCorner(
        side=original.side, steering_axis=axis,
        rack_inner_joint_at_center=original.rack_inner_joint_at_center,
        outer_tie_rod_joint_at_center=transform.apply_point(original.outer_tie_rod_joint_at_center),
        tie_rod_length=original.tie_rod_length, reference_upright_rotation=0.0,
        mechanical_rotation_min=original.mechanical_rotation_min,
        mechanical_rotation_max=original.mechanical_rotation_max,
        wheel_forward_direction_at_center=(transform.apply_direction(original.wheel_forward_direction_at_center)
            if original.wheel_forward_direction_at_center is not None else None),
        static_toe=original.static_toe, source_role="AUTH-VEH-0012:native_front_closure",
    )
    posed = replace(steering, left=corner if side == "left" else steering.left,
                    right=corner if side == "right" else steering.right, steering_axis_track=None)
    solved = solve_corner_position(posed, side, rack_displacement_m)
    if not solved.ok or solved.upright_rotation is None:
        raise ValueError(f"Native front steering closure failed: {solved.failure_code}: {solved.message}")
    return SteeredUpright(wheel_state, axis, solved.upright_rotation,
                         solved.closure_length_residual, "front_tie_rod_once")
