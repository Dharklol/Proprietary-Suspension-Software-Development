from __future__ import annotations

from pathlib import Path
import unittest

from pssd_tire import TireDataError, TireOperatingPoint, load_lateral_force_branch_set
from pssd_tire.force_demand import (
    LateralForceBranch,
    LateralForceCurveSample,
    invert_lateral_force_magnitude,
)


ROOT = Path(__file__).resolve().parents[1]


class TireForceDemandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.branch_set = load_lateral_force_branch_set(
            ROOT / "benchmarks/tires/SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml"
        )
        self.inside_point = TireOperatingPoint(222.0, 0.0, 83.0)
        self.outside_point = TireOperatingPoint(1112.0, 2.0, 83.0)

    def test_exact_and_interpolated_force_demand_inversion(self) -> None:
        exact = self.branch_set.invert(self.inside_point, 250.0)
        self.assertTrue(exact.exact_sample)
        self.assertEqual(2.0, exact.required_slip_angle_magnitude_deg)

        interpolated = self.branch_set.invert(self.inside_point, 300.0)
        self.assertFalse(interpolated.exact_sample)
        self.assertAlmostEqual(2.5, interpolated.required_slip_angle_magnitude_deg)
        self.assertAlmostEqual(0.25, interpolated.interpolation_fraction)

        outside = self.branch_set.invert(self.outside_point, 2500.0)
        self.assertAlmostEqual(9.714285714285714, outside.required_slip_angle_magnitude_deg)

    def test_force_demand_never_extrapolates(self) -> None:
        with self.assertRaises(TireDataError):
            self.branch_set.invert(self.inside_point, 700.0)
        with self.assertRaises(TireDataError):
            self.branch_set.invert(self.inside_point, -1.0)

    def test_operating_point_is_exact_not_interpolated(self) -> None:
        with self.assertRaises(TireDataError):
            self.branch_set.invert(TireOperatingPoint(300.0, 0.0, 83.0), 200.0)
        with self.assertRaises(TireDataError):
            self.branch_set.invert(TireOperatingPoint(222.0, 1.0, 83.0), 200.0)

    def test_nonmonotonic_prepeak_branch_is_rejected(self) -> None:
        with self.assertRaises(TireDataError):
            LateralForceBranch(
                branch_id="bad",
                operating_point=self.inside_point,
                samples=(
                    LateralForceCurveSample(0.0, 0.0),
                    LateralForceCurveSample(2.0, 300.0),
                    LateralForceCurveSample(4.0, 250.0),
                ),
                authority="test",
                source_branch_description="intentionally invalid",
            )

    def test_direct_inversion_retains_bracketing_samples(self) -> None:
        branch = self.branch_set.branch_for(self.outside_point)
        result = invert_lateral_force_magnitude(branch, 1500.0)
        self.assertAlmostEqual(5.090909090909091, result.required_slip_angle_magnitude_deg)
        self.assertEqual(1200.0, result.lower_sample.lateral_force_magnitude_n)
        self.assertEqual(1750.0, result.upper_sample.lateral_force_magnitude_n)


if __name__ == "__main__":
    unittest.main()
