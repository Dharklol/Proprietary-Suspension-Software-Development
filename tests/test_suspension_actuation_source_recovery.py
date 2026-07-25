from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_REAR_LEFT_Q_SOURCE_V0.toml"
ACTUATION_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_ACTUATION_V0.toml"


def _load(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _scale(a: tuple[float, float, float], scalar: float) -> tuple[float, float, float]:
    return tuple(scalar * value for value in a)  # type: ignore[return-value]


def _signed_hinge_angle_deg(
    fore: tuple[float, float, float],
    aft: tuple[float, float, float],
    nominal: tuple[float, float, float],
    current: tuple[float, float, float],
) -> float:
    axis = _sub(aft, fore)
    axis_norm = math.sqrt(_dot(axis, axis))
    k = _scale(axis, 1.0 / axis_norm)
    a = _sub(nominal, fore)
    b = _sub(current, fore)
    a_perp = _sub(a, _scale(k, _dot(k, a)))
    b_perp = _sub(b, _scale(k, _dot(k, b)))
    angle = math.atan2(_dot(k, _cross(a_perp, b_perp)), _dot(a_perp, b_perp))
    return math.degrees(angle)


class SuspensionActuationSourceRecoveryTests(unittest.TestCase):
    def test_rear_q_L_values_are_reproducible_from_frozen_source_points(self) -> None:
        source = _load(SOURCE_PATH)
        actuation = _load(ACTUATION_PATH)
        nominal = source["nominal_canonical_mm"]
        fore = tuple(nominal["lower_fore_inboard"])
        aft = tuple(nominal["lower_aft_inboard"])
        lower0 = tuple(nominal["lower_upright"])
        actuation_by_heave = {float(row["heave_mm"]): row for row in actuation["states"]}

        for row in source["states"]:
            heave = float(row["heave_mm"])
            raw = row["source_lower_upright_mm"]
            current = (
                float(raw[0]) + 1562.4,
                -float(raw[1]),
                float(raw[2]) - heave,
            )
            recovered = _signed_hinge_angle_deg(fore, aft, lower0, current)
            expected = float(row["expected_rear_left_q_L_deg"])
            self.assertLessEqual(abs(recovered - expected), 2.0e-12)

            frozen = actuation_by_heave[heave]
            self.assertAlmostEqual(frozen["rear_left_q_L_deg"], expected, places=12)
            self.assertAlmostEqual(frozen["rear_right_q_L_deg"], -expected, places=12)

    def test_source_fixture_preserves_external_benchmark_boundary(self) -> None:
        source = _load(SOURCE_PATH)
        self.assertEqual(source["source_coordinate_precision_mm"], 0.001)
        self.assertIn("benchmark", source["authority_boundary"])
        self.assertIn("not installed/as-built", source["authority_boundary"])


if __name__ == "__main__":
    unittest.main()
