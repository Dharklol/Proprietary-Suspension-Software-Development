from __future__ import annotations

import unittest

from pssd_tire import (
    LateralForceSlipCurve,
    TireDataError,
    TireOperatingPoint,
    invert_front_axle_force_demands,
)


class TireForceDemandTests(unittest.TestCase):
    def _curve(self, curve_id: str, forces: tuple[float, ...]) -> LateralForceSlipCurve:
        return LateralForceSlipCurve(
            curve_id=curve_id,
            operating_point=TireOperatingPoint(
                normal_load_n=500.0,
                inclination_deg=0.0,
                pressure_kpa=83.0,
            ),
            slip_angle_magnitude_deg=(0.0, 2.0, 4.0, 6.0),
            lateral_force_magnitude_n=forces,
            source_authority="synthetic_software_verification_only",
        )

    def test_bounded_linear_inversion(self) -> None:
        curve = self._curve("curve", (0.0, 200.0, 360.0, 450.0))
        self.assertAlmostEqual(3.0, curve.required_slip_angle_magnitude_deg(280.0))
        self.assertAlmostEqual(3.0, curve.required_slip_angle_magnitude_deg(-280.0))

    def test_rejects_force_above_reviewed_branch(self) -> None:
        curve = self._curve("curve", (0.0, 200.0, 360.0, 450.0))
        with self.assertRaises(TireDataError):
            curve.required_slip_angle_magnitude_deg(451.0)

    def test_positive_outside_minus_inside_is_anti_ackermann_tendency(self) -> None:
        inside = self._curve("inside", (0.0, 220.0, 380.0, 460.0))
        outside = self._curve("outside", (0.0, 300.0, 520.0, 650.0))
        result = invert_front_axle_force_demands(
            inside_curve=inside,
            outside_curve=outside,
            inside_lateral_force_demand_n=240.0,
            outside_lateral_force_demand_n=560.0,
        )
        self.assertGreater(result.outside_minus_inside_deg, 0.0)
        self.assertEqual(
            "toward_less_ackermann_or_anti_ackermann",
            result.steering_correction_tendency,
        )

    def test_curve_requires_monotone_invertible_branch(self) -> None:
        with self.assertRaises(TireDataError):
            self._curve("bad", (0.0, 300.0, 250.0, 450.0))


if __name__ == "__main__":
    unittest.main()
