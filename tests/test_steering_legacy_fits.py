from __future__ import annotations

from pathlib import Path
import unittest

from pssd_steering import WheelAnglePolynomialFit, load_wheel_angle_fits


ROOT = Path(__file__).resolve().parents[1]
FIT_PATH = ROOT / "benchmarks" / "steering" / "wufr26_desmos_wheel_angle_fits.toml"


class HistoricalDesmosFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fits = load_wheel_angle_fits(FIT_PATH)

    def test_expected_fit_set_and_selected_role(self) -> None:
        self.assertEqual(
            set(self.fits),
            {"test1", "test2", "test3", "test4", "previous_year"},
        )
        self.assertEqual(self.fits["test3"].role, "selected_geometry_fit_reference")

    def test_test3_frozen_values(self) -> None:
        fit = self.fits["test3"]
        self.assertAlmostEqual(fit.left_total_deg(0.0), -1.1394, places=12)
        self.assertAlmostEqual(fit.right_total_deg(0.0), 1.1394, places=12)
        self.assertAlmostEqual(fit.left_total_deg(102.0), 22.55395968, places=10)
        self.assertAlmostEqual(fit.right_total_deg(102.0), 33.32408832, places=10)
        self.assertAlmostEqual(fit.left_total_deg(-102.0), -33.32408832, places=10)
        self.assertAlmostEqual(fit.right_total_deg(-102.0), -22.55395968, places=10)

    def test_mirror_and_incremental_definitions(self) -> None:
        for fit in self.fits.values():
            for input_deg in (-102.0, -50.0, 0.0, 50.0, 102.0):
                self.assertAlmostEqual(
                    fit.right_total_deg(input_deg),
                    -fit.left_total_deg(-input_deg),
                    places=12,
                )
                self.assertAlmostEqual(
                    fit.left_incremental_deg(input_deg),
                    fit.left_total_deg(input_deg) - fit.left_static_deg,
                    places=12,
                )
                self.assertAlmostEqual(
                    fit.right_incremental_deg(input_deg),
                    fit.right_total_deg(input_deg) - fit.right_static_deg,
                    places=12,
                )

    def test_center_gains(self) -> None:
        expected = {
            "test1": 0.2450,
            "test2": 0.2344,
            "test3": 0.2427,
            "test4": 0.2348,
            "previous_year": 0.2796,
        }
        for fit_id, gain in expected.items():
            self.assertAlmostEqual(
                self.fits[fit_id].left_center_gain_deg_per_deg,
                gain,
                places=12,
            )
            self.assertAlmostEqual(
                self.fits[fit_id].right_center_gain_deg_per_deg,
                gain,
                places=12,
            )

    def test_rejects_nonfinite_input(self) -> None:
        fit = WheelAnglePolynomialFit("bad-input-check", 0.0, 1.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            fit.left_total_deg(float("nan"))


if __name__ == "__main__":
    unittest.main()
