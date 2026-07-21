from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_steering import load_geometry, load_wheel_angle_fits
from pssd_steering.level_e import (
    HistoricalConventionAdapter,
    compare_wufr26_projected_heading,
)


ROOT = Path(__file__).resolve().parents[1]


class WUFR26LevelEComparisonTests(unittest.TestCase):
    def _comparison(self):
        geometry = load_geometry(
            ROOT / "configurations" / "steering" / "WUFR26_DESIGN_NOMINAL_V0.toml"
        )
        fit = load_wheel_angle_fits(
            ROOT / "benchmarks" / "steering" / "wufr26_desmos_wheel_angle_fits.toml"
        )["test3"]
        inputs = tuple(float(value) for value in range(-102, 103))
        result = compare_wufr26_projected_heading(
            geometry,
            fit,
            inputs,
            rack_metres_per_input_degree=3.5 * 0.0254 / 360.0,
        )
        return inputs, result

    def test_nominal_projected_heading_comparison_is_available(self) -> None:
        _, result = self._comparison()

        for side in (result.left, result.right):
            self.assertTrue(side.total.available)
            self.assertTrue(side.incremental.available)
            self.assertEqual(len(side.total.residuals), 205)
            self.assertEqual(len(side.incremental.residuals), 205)
            self.assertIsNotNone(side.total.metrics)
            self.assertIsNotNone(side.incremental.metrics)
            assert side.total.metrics is not None
            assert side.incremental.metrics is not None
            self.assertTrue(math.isfinite(side.total.metrics.rmse))
            self.assertTrue(math.isfinite(side.incremental.metrics.rmse))

    def test_total_residual_retains_independent_static_datum(self) -> None:
        inputs, result = self._comparison()
        center_index = inputs.index(0.0)

        for side in (result.left, result.right):
            static_difference = side.canonical_static_deg - side.historical_static_deg
            self.assertAlmostEqual(side.incremental.residuals[center_index], 0.0, places=12)
            self.assertAlmostEqual(
                side.total.residuals[center_index], static_difference, places=12
            )
            for total_residual, incremental_residual in zip(
                side.total.residuals, side.incremental.residuals
            ):
                self.assertAlmostEqual(
                    total_residual - incremental_residual,
                    static_difference,
                    places=12,
                )

    def test_requires_centered_input_state(self) -> None:
        geometry = load_geometry(
            ROOT / "configurations" / "steering" / "WUFR26_DESIGN_NOMINAL_V0.toml"
        )
        fit = load_wheel_angle_fits(
            ROOT / "benchmarks" / "steering" / "wufr26_desmos_wheel_angle_fits.toml"
        )["test3"]
        with self.assertRaisesRegex(ValueError, "centred 0 deg state"):
            compare_wufr26_projected_heading(
                geometry,
                fit,
                (-2.0, -1.0, 1.0, 2.0),
                rack_metres_per_input_degree=3.5 * 0.0254 / 360.0,
            )

    def test_adapter_rejects_undeclared_side_swap(self) -> None:
        with self.assertRaises(ValueError):
            HistoricalConventionAdapter(side_mapping="swapped")


if __name__ == "__main__":
    unittest.main()
