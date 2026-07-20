"""Traceable evaluation of recovered historical steering-response fits.

These polynomials are fit-derived cross-tool evidence. They do not replace the
rigid steering mechanism, raw CAD samples, or physical validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class WheelAnglePolynomialFit:
    """One left-wheel polynomial with a symmetry-derived right-wheel branch."""

    fit_id: str
    c0: float
    c1: float
    c2: float
    c3: float
    c4: float
    role: str = ""

    def __post_init__(self) -> None:
        values = (self.c0, self.c1, self.c2, self.c3, self.c4)
        if not self.fit_id:
            raise ValueError("fit_id is required")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Polynomial coefficients must be finite")

    def left_total_deg(self, input_deg: float) -> float:
        """Evaluate the toe-inclusive left branch using Horner's rule."""

        x = float(input_deg)
        if not math.isfinite(x):
            raise ValueError("input_deg must be finite")
        return ((((self.c4 * x) + self.c3) * x + self.c2) * x + self.c1) * x + self.c0

    def right_total_deg(self, input_deg: float) -> float:
        """Evaluate the recovered symmetry relation right(x) = -left(-x)."""

        return -self.left_total_deg(-float(input_deg))

    @property
    def left_static_deg(self) -> float:
        return self.c0

    @property
    def right_static_deg(self) -> float:
        return -self.c0

    def left_incremental_deg(self, input_deg: float) -> float:
        return self.left_total_deg(input_deg) - self.left_static_deg

    def right_incremental_deg(self, input_deg: float) -> float:
        return self.right_total_deg(input_deg) - self.right_static_deg

    @property
    def left_center_gain_deg_per_deg(self) -> float:
        return self.c1

    @property
    def right_center_gain_deg_per_deg(self) -> float:
        return self.c1


def load_wheel_angle_fits(path: str | Path) -> dict[str, WheelAnglePolynomialFit]:
    """Load every fit from the frozen TOML benchmark source."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)

    result: dict[str, WheelAnglePolynomialFit] = {}
    for fit_id, values in document["fits"].items():
        result[fit_id] = WheelAnglePolynomialFit(
            fit_id=fit_id,
            c0=float(values["c0"]),
            c1=float(values["c1"]),
            c2=float(values["c2"]),
            c3=float(values["c3"]),
            c4=float(values["c4"]),
            role=str(values.get("role", "")),
        )
    return result
