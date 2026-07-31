from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from pssd_tire.force_demand import invert_lateral_force_magnitude
from pssd_tire.lateral import TireDataError, TireOperatingPoint
from pssd_tire.r25b_force_demand_adapter import (
    INSIDE_REFERENCE_POINT,
    OUTSIDE_REFERENCE_POINT,
    R25B_FORCE_DEMAND_BRANCH_SET_ID,
    load_r25b_reference_force_demand_branch_set,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = (
    ROOT
    / "benchmarks/steering/r25b_source_force_demand_adapter_result_v0.1.0.toml"
)


class R25bForceDemandAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.branch_set = load_r25b_reference_force_demand_branch_set()
        cls.inside = cls.branch_set.branch_for(INSIDE_REFERENCE_POINT)
        cls.outside = cls.branch_set.branch_for(OUTSIDE_REFERENCE_POINT)
        with RESULT.open("rb") as stream:
            cls.result = tomllib.load(stream)

    def test_exact_source_identity_and_operating_points_are_retained(self) -> None:
        self.assertEqual(
            self.branch_set.branch_set_id,
            R25B_FORCE_DEMAND_BRANCH_SET_ID,
        )
        self.assertEqual(
            self.branch_set.source_tire_id,
            "HOOSIER_43105_18X7.5-10_R25B",
        )
        self.assertEqual(
            self.branch_set.intended_tire_id,
            "HOOSIER_43104_18X7.5-10_R20",
        )
        self.assertNotEqual(
            self.branch_set.source_tire_id,
            self.branch_set.intended_tire_id,
        )
        self.assertEqual(self.inside.operating_point, INSIDE_REFERENCE_POINT)
        self.assertEqual(self.outside.operating_point, OUTSIDE_REFERENCE_POINT)
        self.assertEqual(INSIDE_REFERENCE_POINT.pressure_kpa, 82.7)
        self.assertEqual(OUTSIDE_REFERENCE_POINT.pressure_kpa, 82.7)

    def test_exact_strict_prefix_sample_counts_and_endpoints_match_source(self) -> None:
        self.assertEqual(len(self.inside.samples), 64)
        self.assertEqual(len(self.outside.samples), 86)

        self.assertAlmostEqual(
            self.inside.samples[0].slip_angle_magnitude_deg,
            0.07547169811320754,
        )
        self.assertAlmostEqual(
            self.inside.samples[0].lateral_force_magnitude_n,
            50.97234695655734,
        )
        self.assertAlmostEqual(
            self.inside.samples[-1].slip_angle_magnitude_deg,
            9.584905660377357,
        )
        self.assertAlmostEqual(
            self.inside.samples[-1].lateral_force_magnitude_n,
            694.041896190421,
        )

        self.assertAlmostEqual(
            self.outside.samples[0].slip_angle_magnitude_deg,
            0.06349206349206349,
        )
        self.assertAlmostEqual(
            self.outside.samples[0].lateral_force_magnitude_n,
            275.83617788180254,
        )
        self.assertAlmostEqual(
            self.outside.samples[-1].slip_angle_magnitude_deg,
            10.857142857142856,
        )
        self.assertAlmostEqual(
            self.outside.samples[-1].lateral_force_magnitude_n,
            2737.8937842052433,
        )

    def test_no_zero_anchor_or_source_repair_is_introduced(self) -> None:
        for branch in self.branch_set.branches:
            self.assertGreater(branch.minimum_force_magnitude_n, 0.0)
            self.assertGreater(branch.samples[0].slip_angle_magnitude_deg, 0.0)
            self.assertTrue(
                all(
                    upper.slip_angle_magnitude_deg
                    > lower.slip_angle_magnitude_deg
                    for lower, upper in zip(branch.samples, branch.samples[1:])
                )
            )
            self.assertTrue(
                all(
                    upper.lateral_force_magnitude_n
                    > lower.lateral_force_magnitude_n
                    for lower, upper in zip(branch.samples, branch.samples[1:])
                )
            )
            provenance = dict(branch.provenance)
            self.assertEqual(provenance["source_branch_id"], "negative_slip_pre_peak")
            self.assertEqual(provenance["source_side"], "negative_slip")
            self.assertEqual(provenance["zero_anchor_inserted"], "false")
            self.assertEqual(provenance["track_scale_applied"], "false")

    def test_bounded_piecewise_linear_inversion_uses_exact_source_segments(self) -> None:
        inside = invert_lateral_force_magnitude(
            self.inside,
            75.90395334602191,
        )
        self.assertFalse(inside.exact_sample)
        self.assertAlmostEqual(inside.interpolation_fraction, 0.5)
        self.assertAlmostEqual(
            inside.required_slip_angle_magnitude_deg,
            0.1509433962264151,
        )

        outside = self.branch_set.invert(
            OUTSIDE_REFERENCE_POINT,
            316.39913728089266,
        )
        self.assertFalse(outside.exact_sample)
        self.assertAlmostEqual(outside.interpolation_fraction, 0.5)
        self.assertAlmostEqual(
            outside.required_slip_angle_magnitude_deg,
            0.12698412698412698,
        )

    def test_zero_below_minimum_above_peak_and_state_substitution_fail_closed(self) -> None:
        with self.assertRaises(TireDataError):
            self.branch_set.invert(INSIDE_REFERENCE_POINT, 0.0)
        with self.assertRaises(TireDataError):
            self.branch_set.invert(
                INSIDE_REFERENCE_POINT,
                self.inside.maximum_force_magnitude_n + 1.0,
            )
        with self.assertRaises(TireDataError):
            self.branch_set.invert(
                TireOperatingPoint(222.0, 0.0, 83.0),
                self.inside.minimum_force_magnitude_n,
            )
        with self.assertRaises(TireDataError):
            self.branch_set.invert(
                TireOperatingPoint(333.5, 1.0, 82.7),
                self.inside.minimum_force_magnitude_n,
            )

    def test_frozen_result_matches_executable_adapter(self) -> None:
        self.assertEqual(self.result["status"], "pass")
        self.assertEqual(
            self.result["branch_set_id"],
            self.branch_set.branch_set_id,
        )
        self.assertEqual(
            self.result["source_tire_id"],
            self.branch_set.source_tire_id,
        )
        self.assertEqual(
            self.result["intended_tire_id"],
            self.branch_set.intended_tire_id,
        )
        inside = self.result["inside_reference"]
        outside = self.result["outside_reference"]
        self.assertEqual(inside["sample_count"], len(self.inside.samples))
        self.assertEqual(outside["sample_count"], len(self.outside.samples))
        self.assertEqual(
            inside["minimum_force_n"],
            self.inside.minimum_force_magnitude_n,
        )
        self.assertEqual(
            outside["minimum_force_n"],
            self.outside.minimum_force_magnitude_n,
        )
        self.assertEqual(
            inside["maximum_force_n"],
            self.inside.maximum_force_magnitude_n,
        )
        self.assertEqual(
            outside["maximum_force_n"],
            self.outside.maximum_force_magnitude_n,
        )
        gates = self.result["fail_closed"]
        self.assertTrue(gates["zero_demand_below_source_branch_rejected"])
        self.assertTrue(gates["above_peak_demand_rejected"])
        self.assertTrue(gates["rounded_83kpa_state_rejected"])
        self.assertTrue(gates["operating_state_interpolation_rejected"])


if __name__ == "__main__":
    unittest.main()
