"""Provisional WUFR-27 steel steering joint structural screens.

Closed-form engineering *sensitivity* functions only. Geometry is nominal;
weld throat, weld category, load distribution, material grade and in-service
axial pin load have not been certified. Never report an approved joint FoS.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


INCH_TO_M = .0254
MPA = 1e6


def _positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True)
class WeldRingScreen:
    """Circular weld LINE model, not a complete weld-joint qualification.

    Annular wall full penetration would be approximately a 0.0625-inch
    throat for the nominal 0.750/0.625-inch tube; any partial-penetration weld
    has a smaller effective throat to be determined from the final drawing.
    This line model gives uniform shear flow q=T/(2*pi*rm^2), excluding
    shoulder eccentricity, local discontinuity, weld-toe notch and fatigue.
    """

    tube_outer_diameter_in: float = .750
    tube_inner_diameter_in: float = .625

    def __post_init__(self) -> None:
        _positive("outer diameter", self.tube_outer_diameter_in)
        _positive("inner diameter", self.tube_inner_diameter_in)
        if self.tube_inner_diameter_in >= self.tube_outer_diameter_in:
            raise ValueError("inner diameter must be less than outer")

    @property
    def wall_thickness_m(self) -> float:
        return .5 * (self.tube_outer_diameter_in -
                     self.tube_inner_diameter_in) * INCH_TO_M

    @property
    def mean_radius_m(self) -> float:
        return .25 * (self.tube_outer_diameter_in +
                      self.tube_inner_diameter_in) * INCH_TO_M

    def shear_flow_n_per_mm(self, torque_nm: float) -> float:
        if not math.isfinite(torque_nm):
            raise ValueError("torque must be finite")
        return abs(torque_nm) / (2 * math.pi * self.mean_radius_m**2) / 1000

    def required_throat_mm(self, torque_nm: float,
                           admissible_shear_mpa: float) -> float:
        _positive("admissible shear", admissible_shear_mpa)
        return self.shear_flow_n_per_mm(torque_nm) / admissible_shear_mpa

    def shear_mpa(self, torque_nm: float, effective_throat_mm: float) -> float:
        _positive("effective throat", effective_throat_mm)
        return self.shear_flow_n_per_mm(torque_nm) / effective_throat_mm

    def full_wall_line_shear_mpa(self, torque_nm: float) -> float:
        return self.shear_mpa(torque_nm, self.wall_thickness_m * 1000)


@dataclass(frozen=True)
class ClevisPinBendingScreen:
    """Concentrated-center-load simply supported beam sensitivity.

    support_span_in is center-to-center distance between idealized outer
    bearing reactions; NOT the overall pin length, usable length, or edge
    distance. Real three-member distributed bearing and pin contact require
    the actual geometry and fit before a bending capacity can be assigned.
    """

    min_pin_diameter_in: float = .121
    assumed_yield_mpa: float = 205
    factor_of_safety: float = 3

    def __post_init__(self) -> None:
        for name, value in (
            ("pin diameter", self.min_pin_diameter_in),
            ("assumed pin yield", self.assumed_yield_mpa),
            ("factor of safety", self.factor_of_safety),
        ):
            _positive(name, value)

    def point_load_capacity_n(self, support_span_in: float) -> float:
        _positive("support span", support_span_in)
        d = self.min_pin_diameter_in * INCH_TO_M
        s = support_span_in * INCH_TO_M
        allowable_bending_pa = self.assumed_yield_mpa * MPA / self.factor_of_safety
        return math.pi * d**3 * allowable_bending_pa / (8 * s)

    def uniform_center_load_capacity_n(self, central_width_in: float,
                                        outer_wall_bearing_width_in: float) -> float:
        """Symmetric uniform center load and point reactions at outer-wall midplanes.

        Maximum bending moment is F*(b/8+t/4), where b is central
        bearing-member width and t each outer bearing width.
        """
        _positive("central width", central_width_in)
        _positive("outer bearing width", outer_wall_bearing_width_in)
        lever = (central_width_in / 8 +
                 outer_wall_bearing_width_in / 4) * INCH_TO_M
        d = self.min_pin_diameter_in * INCH_TO_M
        allowable_bending_pa = self.assumed_yield_mpa * MPA / self.factor_of_safety
        return allowable_bending_pa * math.pi * d**3 / (32 * lever)


@dataclass(frozen=True)
class LugScreen:
    """Idealized steel lug yield screens. Does not assume real lug load sharing."""

    loaded_wall_thickness_in: float = .094
    hole_diameter_in: float = .125
    transverse_width_in: float = .300
    assumed_steel_yield_mpa: float = 205
    factor_of_safety: float = 3

    def __post_init__(self) -> None:
        for name, value in (
            ("thickness", self.loaded_wall_thickness_in),
            ("hole diameter", self.hole_diameter_in),
            ("transverse width", self.transverse_width_in),
            ("assumed steel yield", self.assumed_steel_yield_mpa),
            ("factor of safety", self.factor_of_safety),
        ):
            _positive(name, value)
        if self.transverse_width_in <= self.hole_diameter_in:
            raise ValueError("negative net section")

    def net_section_allowable_n(self) -> float:
        area = (self.transverse_width_in - self.hole_diameter_in) * (
            self.loaded_wall_thickness_in * INCH_TO_M**2
        )
        return area * self.assumed_steel_yield_mpa * MPA / self.factor_of_safety

    def shear_out_allowable_n(self, center_to_free_edge_in: float) -> float:
        """Two parallel ligament shear planes per ONE wall, if datum is true.

        The edge dimension must be *pin-center-to-free-edge in load direction*.
        A free-edge-to-pin-surface distance is NOT interchangeable.
        """
        _positive("center-to-free-edge", center_to_free_edge_in)
        remaining = center_to_free_edge_in - self.hole_diameter_in / 2
        if remaining <= 0:
            raise ValueError("pin hole cuts through free edge")
        area = 2 * remaining * self.loaded_wall_thickness_in * INCH_TO_M**2
        tau_allow_pa = self.assumed_steel_yield_mpa * MPA / (
            math.sqrt(3) * self.factor_of_safety
        )
        return area * tau_allow_pa


def required_shear_endurance_mpa(
    nominal_alternating_shear_mpa: float, *,
    fatigue_notch_factor: float,
    required_fatigue_safety_factor: float,
) -> float:
    """Required corrected torsional endurance limit for zero-mean cycling.

    This is NOT a life forecast or Marin-corrected material property.
    A fatigue life/capacity requires actual steel grade, strength, finish,
    stress gradient, weld quality, geometry, mean stress and load spectrum.
    """
    _positive("alternating shear", nominal_alternating_shear_mpa)
    _positive("fatigue notch factor", fatigue_notch_factor)
    _positive("required safety factor", required_fatigue_safety_factor)
    return nominal_alternating_shear_mpa * fatigue_notch_factor * (
        required_fatigue_safety_factor
    )
