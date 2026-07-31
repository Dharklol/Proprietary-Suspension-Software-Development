from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from pssd_tire.steady_state_lateral_benchmarks import (
    build_benchmark_result,
    format_benchmark_result_json,
    format_benchmark_result_toml,
)

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "benchmarks" / "tires" / "steady_state_lateral_tire_result_v0.1.0.json"
TOML_PATH = ROOT / "benchmarks" / "tires" / "steady_state_lateral_tire_result_v0.1.0.toml"


class SteadyStateLateralResultRecordTests(unittest.TestCase):
    def test_frozen_json_matches_deterministic_regeneration(self) -> None:
        result = build_benchmark_result()
        self.assertEqual(
            JSON_PATH.read_text(encoding="utf-8"),
            format_benchmark_result_json(result),
        )
        self.assertEqual(json.loads(JSON_PATH.read_text(encoding="utf-8")), result)

    def test_frozen_toml_matches_deterministic_regeneration(self) -> None:
        result = build_benchmark_result()
        self.assertEqual(
            TOML_PATH.read_text(encoding="utf-8"),
            format_benchmark_result_toml(result),
        )
        parsed = tomllib.loads(TOML_PATH.read_text(encoding="utf-8"))
        self.assertEqual(parsed["record_id"], result["record_id"])
        self.assertFalse(parsed["fidelity"]["source_specific_r25b_runtime_activation_authorized"])

    def test_all_three_benchmarks_and_failure_gates_are_frozen(self) -> None:
        result = build_benchmark_result()
        self.assertEqual(
            set(result["benchmarks"]),
            {"BENCH-TIRE-0001", "BENCH-TIRE-0002", "BENCH-TIRE-0003"},
        )
        self.assertEqual(result["benchmarks"]["BENCH-TIRE-0002"]["curve_count"], 8)
        self.assertEqual(result["benchmarks"]["BENCH-TIRE-0003"]["all_roots_rad"], [0.125, 0.26])
        self.assertEqual(
            result["failure_code_coverage"]["r25b_activation"],
            "source_specific_activation_blocked",
        )


if __name__ == "__main__":
    unittest.main()
