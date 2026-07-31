from __future__ import annotations

from pathlib import Path
import math
import tomllib
import unittest

from pssd_tire.r25b_source_native import load_r25b_source_native_exchange

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "benchmarks/tires/WUFR26_H43105_R25B_COMPLETE_SIGNED_SOURCE_NATIVE_V0/manifest.toml"
)


class R25bCompleteSignedSourceNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exchange = load_r25b_source_native_exchange(MANIFEST)

    def test_complete_exchange_has_exact_state_and_sample_coverage(self) -> None:
        exchange = self.exchange
        self.assertEqual(len(exchange.curves), 60)
        self.assertEqual(exchange.sample_count, 9630)
        self.assertEqual(
            sorted({curve.normal_load_n for curve in exchange.curves}),
            [222.0, 445.0, 667.0, 890.0, 1112.0],
        )
        self.assertEqual(
            sorted({curve.inclination_deg for curve in exchange.curves}),
            [0.0, 2.0, 4.0],
        )
        self.assertEqual(
            sorted({curve.pressure_kpa for curve in exchange.curves}),
            [55.2, 68.9, 82.7, 96.5],
        )
        self.assertFalse(exchange.runtime_authorized)
        self.assertFalse(exchange.canonical_adapter_reviewed)

    def test_exact_signed_curves_retain_both_slip_signs_and_postpeak_shape(self) -> None:
        for curve in self.exchange.curves:
            slip = curve.source_slip_angle_deg
            force = curve.source_lateral_force_n
            self.assertAlmostEqual(slip[0], -12.0, places=12)
            self.assertAlmostEqual(slip[-1], 12.0, places=12)
            self.assertTrue(any(value < 0.0 for value in slip))
            self.assertTrue(any(value > 0.0 for value in slip))
            self.assertEqual(len(slip), len(force))
            self.assertEqual(
                curve.segment_branch_role,
                "unclassified_complete_signed_source_curve",
            )

    def test_reference_states_match_frozen_source_peaks(self) -> None:
        inside = next(
            curve
            for curve in self.exchange.curves
            if curve.state_key == (222.0, 0.0, 82.7)
        )
        outside = next(
            curve
            for curve in self.exchange.curves
            if curve.state_key == (1112.0, 2.0, 82.7)
        )
        inside_pairs = [
            (slip, force)
            for slip, force in zip(
                inside.source_slip_angle_deg, inside.source_lateral_force_n
            )
            if slip < 0.0 and force > 0.0
        ]
        outside_pairs = [
            (slip, force)
            for slip, force in zip(
                outside.source_slip_angle_deg, outside.source_lateral_force_n
            )
            if slip < 0.0 and force > 0.0
        ]
        inside_peak = max(inside_pairs, key=lambda pair: pair[1])
        outside_peak = max(outside_pairs, key=lambda pair: pair[1])
        self.assertAlmostEqual(inside_peak[0], -9.584905660377357)
        self.assertAlmostEqual(inside_peak[1], 694.041896190421)
        self.assertAlmostEqual(outside_peak[0], -10.857142857142856)
        self.assertAlmostEqual(outside_peak[1], 2737.8937842052433)

    def test_candidate_axis_and_force_transform_has_positive_local_slope(self) -> None:
        # Evidence only: alpha_canonical = SA_source and Fy_canonical = -FY_source.
        # The pressure basis and source-specific authorization remain blocked.
        slopes = []
        for curve in self.exchange.curves:
            slip = curve.source_slip_angle_deg
            force = curve.source_lateral_force_n
            right = next(index for index, value in enumerate(slip) if value > 0.0)
            left = right - 1
            delta_alpha = math.radians(slip[right] - slip[left])
            canonical_force_left = -force[left]
            canonical_force_right = -force[right]
            slopes.append((canonical_force_right - canonical_force_left) / delta_alpha)
        self.assertEqual(len(slopes), 60)
        self.assertTrue(all(value > 0.0 for value in slopes))

        with (ROOT / "data_catalog/r25b_runtime_source_activation_v0.toml").open("rb") as stream:
            activation = tomllib.load(stream)
        adapter = activation["canonical_adapter_candidate"]
        self.assertEqual(adapter["slip_angle_rule"], "alpha_rad = deg_to_rad(source_SA_deg)")
        self.assertEqual(adapter["lateral_force_rule"], "Fy_canonical_N = -source_FY_N")
        self.assertFalse(adapter["pressure_basis_resolved"])
        self.assertFalse(activation["activation_gate"]["source_to_canonical_adapter_reviewed"])
        self.assertFalse(
            activation["activation_gate"]["source_specific_runtime_activation_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
