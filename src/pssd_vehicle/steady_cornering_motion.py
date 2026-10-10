"""Development-only steady motion (EQ-VEH-0023), AUTH-VEH-0012.

Heading-frame axes are +x forward, +y left, +z up. This boundary supplies
kinematics and the explicitly selected virtual speed holder, not equilibrium.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SteadyCorneringMotion:
    speed_m_s: float
    curvature_per_m: float
    sideslip_rad: float
    forward_velocity_m_s: float
    lateral_velocity_m_s: float
    yaw_rate_rad_s: float
    acceleration_m_s2: tuple[float, float, float]
    travel_direction: tuple[float, float, float]


def steady_cornering_motion(*, speed_m_s: float, curvature_per_m: float,
                            sideslip_rad: float) -> SteadyCorneringMotion:
    """Use CG path curvature, not the forward-speed/yaw-rate radius."""
    if not all(math.isfinite(v) for v in (speed_m_s, curvature_per_m, sideslip_rad)):
        raise ValueError("Motion inputs must be finite")
    if speed_m_s <= 0:
        raise ValueError("Steady motion requires positive speed")
    direction = (math.cos(sideslip_rad), math.sin(sideslip_rad), 0.0)
    u, v = speed_m_s * direction[0], speed_m_s * direction[1]
    r = speed_m_s * curvature_per_m
    acceleration = (-r * v, r * u, 0.0)
    if not all(math.isfinite(x) for x in (u, v, r, *acceleration)):
        raise ValueError("Motion calculation overflowed")
    return SteadyCorneringMotion(speed_m_s, curvature_per_m, sideslip_rad,
                                u, v, r, acceleration, direction)


@dataclass(frozen=True)
class VirtualSpeedHold:
    force_heading_n: tuple[float, float, float]
    power_w: float
    policy: str = "virtual_tangential_force_at_current_total_cg"


def virtual_speed_hold(motion: SteadyCorneringMotion, *, force_n: float,
                       policy: str) -> VirtualSpeedHold:
    """Map a solved signed force to travel direction; caller applies it at CG."""
    if policy != "virtual_tangential_force_at_current_total_cg":
        raise ValueError("Explicit virtual speed-holding policy is required")
    if not math.isfinite(force_n):
        raise ValueError("Holding force must be finite")
    force = tuple(force_n * x for x in motion.travel_direction)
    power = force_n * motion.speed_m_s
    if not all(math.isfinite(x) for x in (*force, power)):
        raise ValueError("Holding calculation overflowed")
    return VirtualSpeedHold(force, power)


@dataclass(frozen=True)
class CurrentMassPoint:
    source_id: str
    mass_kg: float
    position_heading_m: tuple[float, float, float]


@dataclass(frozen=True)
class ManeuverInertia:
    current_total_cg_heading_m: tuple[float, float, float]
    forces_heading_n: tuple[tuple[float, float, float], ...]
    mass_source_ids: tuple[str, ...]
    assumption_id: str = "ASM-VEH-0006"


def maneuver_inertia(motion: SteadyCorneringMotion, *,
                     mass_points: tuple[CurrentMassPoint, ...],
                     policy: str) -> ManeuverInertia:
    """Apply uniform acceleration to explicitly supplied current mass points.

    Omits angular-momentum rate, wheel gyro and local yaw acceleration terms.
    Mass provenance and geometry remain the responsibility of upstream providers.
    """
    if policy != "uniform_acceleration_current_mass_lumps":
        raise ValueError("Explicit lumped maneuver inertia policy is required")
    if not mass_points:
        raise ValueError("Current mass points are required")
    ids = tuple(p.source_id for p in mass_points)
    if any(not isinstance(s, str) or not s.strip() for s in ids) or len(set(ids)) != len(ids):
        raise ValueError("Mass source identities must be nonempty and unique")
    for point in mass_points:
        if not math.isfinite(point.mass_kg) or point.mass_kg <= 0:
            raise ValueError("Mass must be finite and positive")
        if len(point.position_heading_m) != 3 or not all(
                math.isfinite(x) for x in point.position_heading_m):
            raise ValueError("Current positions require three finite heading-frame coordinates")
    try:
        total = math.fsum(p.mass_kg for p in mass_points)
        cg = tuple(math.fsum((p.mass_kg / total)*p.position_heading_m[i]
                             for p in mass_points) for i in range(3))
        forces = tuple(tuple(-p.mass_kg*a for a in motion.acceleration_m_s2)
                       for p in mass_points)
    except OverflowError as exc:
        raise ValueError("Mass-point calculation overflowed") from exc
    if not math.isfinite(total) or not all(math.isfinite(x) for x in (*cg, *(x for f in forces for x in f))):
        raise ValueError("Mass-point calculation overflowed")
    return ManeuverInertia(cg, forces, ids)
