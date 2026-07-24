from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pssd_tire import (
    TireDataError,
    TireOperatingPoint,
    TireOptionalDependencyError,
    load_lateral_summary_grid,
    load_mat_ttc_channels,
    parse_tir_text,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml"


class TireLateralSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.grid = load_lateral_summary_grid(FIXTURE)

    def test_exact_uncensored_source_values_are_preserved(self) -> None:
        inside = self.grid.estimate(TireOperatingPoint(222.0, 0.0, 83.0))
        outside = self.grid.estimate(TireOperatingPoint(1112.0, 2.0, 83.0))
        self.assertEqual(299.0, inside.cornering_stiffness_n_per_deg)
        self.assertEqual(694.0, inside.peak_lateral_force_n)
        self.assertEqual(-9.6, inside.source_peak_slip_angle_deg)
        self.assertEqual(632.0, outside.cornering_stiffness_n_per_deg)
        self.assertEqual(2738.0, outside.peak_lateral_force_n)
        self.assertEqual(-10.9, outside.source_peak_slip_angle_deg)

    def test_trilinear_interpolation_propagates_source_censoring(self) -> None:
        estimate = self.grid.estimate(
            TireOperatingPoint(333.5, 1.0, 76.0),
            require_uncensored_peak=False,
        )
        expected_stiffness = sum([334, 463, 267, 405, 299, 414, 256, 383]) / 8.0
        expected_force = sum([731, 1319, 661, 1226, 694, 1256, 619, 1164]) / 8.0
        expected_slip = sum([-7.3, -8.1, -9.1, -12.0, -9.6, -9.9, -10.5, -11.4]) / 8.0
        self.assertAlmostEqual(expected_stiffness, estimate.cornering_stiffness_n_per_deg)
        self.assertAlmostEqual(expected_force, estimate.peak_lateral_force_n)
        self.assertAlmostEqual(expected_slip, estimate.source_peak_slip_angle_deg)
        self.assertEqual(8, estimate.source_sample_count)
        self.assertTrue(estimate.peak_slip_angle_censored)

    def test_peak_query_rejects_censored_source_boundary(self) -> None:
        with self.assertRaises(TireDataError):
            self.grid.estimate(TireOperatingPoint(445.0, 2.0, 69.0))
        estimate = self.grid.estimate(
            TireOperatingPoint(445.0, 2.0, 69.0),
            require_uncensored_peak=False,
        )
        self.assertTrue(estimate.peak_slip_angle_censored)
        self.assertEqual(12.0, estimate.peak_slip_angle_magnitude_deg)

    def test_no_extrapolation(self) -> None:
        with self.assertRaises(TireDataError):
            self.grid.estimate(TireOperatingPoint(1200.0, 0.0, 83.0))
        with self.assertRaises(TireDataError):
            self.grid.estimate(TireOperatingPoint(667.0, -1.0, 83.0))

    def test_tir_reader_is_metadata_only_and_dependency_free(self) -> None:
        document = parse_tir_text(
            """
            $ comment
            [MODEL]
            FITTYP = 61
            TYRESIDE = 'LEFT'
            [DIMENSION]
            UNLOADED_RADIUS = 0.2286 $ m
            """
        )
        self.assertEqual("61", document.value("MODEL", "FITTYP"))
        self.assertEqual("LEFT", document.value("MODEL", "TYRESIDE"))
        self.assertEqual("0.2286", document.value("DIMENSION", "UNLOADED_RADIUS"))

    def test_mat_reader_is_optional_not_a_core_dependency(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mat") as stream:
            with patch("importlib.util.find_spec", return_value=None):
                with self.assertRaises(TireOptionalDependencyError):
                    load_mat_ttc_channels(stream.name)


if __name__ == "__main__":
    unittest.main()
