"""Ideal coaxial double-D clearance/contact sizing model for WUFR-27.

SCREEN ONLY: flush-end, perfectly concentric, sharp chord endpoints, nominal
circular bounds and no angular positional/form error. It is not a worst-case
tolerance/contact-FEA or a released fit/backlash acceptance criterion.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

INCH_MM = 25.4


@dataclass(frozen=True)
class IdealDoubleDFit:
    male_major_radius_in: float = 0.295
    male_across_flats_in: float = 0.472
    engagement_in: float = 0.375

    def __post_init__(self) -> None:
        vals = (self.male_major_radius_in, self.male_across_flats_in,
                self.engagement_in)
        if not all(math.isfinite(v) for v in vals):
            raise ValueError("all double-D dimensions must be finite")
        if (self.male_major_radius_in <= 0 or self.engagement_in <= 0
                or not 0 < self.male_across_flats_in < 2*self.male_major_radius_in):
            raise ValueError("invalid double-D geometry")

    @property
    def half_flat_in(self) -> float:
        return .5*self.male_across_flats_in

    @property
    def half_chord_in(self) -> float:
        a=self.half_flat_in
        return math.sqrt(self.male_major_radius_in**2-a*a)

    @property
    def flat_depth_in(self) -> float:
        return self.male_major_radius_in-self.half_flat_in

    def one_sided_ideal_rotation_deg(self, diametral_flat_clearance_in: float) -> float:
        """Chord-corner interference limit, coaxial D profiles, deg one-way.

        For theta>=0, rotated male support on +y:
          a*cos(theta)+b*sin(theta) = a+C/2.
        This is the small-angle branch, valid while the corner remains the
        support point, for dimensions here in the engineering clearance range.
        """
        c=diametral_flat_clearance_in
        if not math.isfinite(c) or c<0:
            raise ValueError("clearance must be finite and nonnegative")
        a=self.half_flat_in
        r=self.male_major_radius_in
        if a+c/2>=r:
            raise ValueError("clearance too large for small-angle corner contact")
        phi=math.asin(a/r)
        return math.degrees(math.asin((a+c/2)/r)-phi)

    def bidirectional_ideal_play_deg(self, diametral_flat_clearance_in: float) -> float:
        """Return total +/- take-up, twice the one-direction value."""
        return 2*self.one_sided_ideal_rotation_deg(diametral_flat_clearance_in)

    def max_clearance_for_bidirectional_play_in(self, budget_deg: float) -> float:
        """Inverse of coaxial corner-contact model for a positive play budget."""
        if not math.isfinite(budget_deg) or budget_deg<=0:
            raise ValueError("play budget must be finite and positive")
        phi=math.asin(self.half_flat_in/self.male_major_radius_in)
        half_angle=math.radians(budget_deg/2)
        if phi+half_angle>=math.pi/2:
            raise ValueError("play budget exceeds small-angle contact branch")
        return 2*(self.male_major_radius_in*math.sin(phi+half_angle)
                  -self.half_flat_in)

    def nominal_clearance_range_in(self, female_nominal_af_in:float,
                                   male_half_tolerance_in:float,
                                   female_half_tolerance_in:float)->tuple[float,float]:
        vals=(female_nominal_af_in,male_half_tolerance_in,
              female_half_tolerance_in)
        if not all(math.isfinite(v) for v in vals):
            raise ValueError("nonfinite tolerance inputs")
        if female_nominal_af_in<=0 or min(vals[1:])<0:
            raise ValueError("invalid tolerances")
        c0=female_nominal_af_in-self.male_across_flats_in
        dt=male_half_tolerance_in+female_half_tolerance_in
        return c0-dt,c0+dt

    def lower_bound_flank_reaction_n(self, torque_nm:float)->float:
        """Absolute torque / (2 chord half width), assuming two opposite flats.

        At maximum edge leverage b, F >= T/(2b) PER OPPOSING FLANK
        if two equal and opposite compressive reactions form a couple.
        Not a prediction of actual contact pressure, stress or load sharing.
        """
        if not math.isfinite(torque_nm):
            raise ValueError("nonfinite torque")
        return abs(torque_nm)/(2*self.half_chord_in*.0254)

    def illustrative_mean_contact_pressure_mpa(self,torque_nm:float,
                                               chosen_contact_strip_width_mm:float)->float:
        """NOT an actual Hertz/contact-FEA pressure: chosen uniform patch only."""
        if (not math.isfinite(chosen_contact_strip_width_mm)
                or chosen_contact_strip_width_mm<=0):
            raise ValueError("contact strip width must be finite and positive")
        f=self.lower_bound_flank_reaction_n(torque_nm)
        return f/(self.engagement_in*INCH_MM*chosen_contact_strip_width_mm)
