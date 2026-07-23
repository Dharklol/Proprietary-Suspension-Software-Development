from __future__ import annotations

import importlib.util
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = (
    ROOT
    / "benchmarks"
    / "steering"
    / "steering_state_metric_objective_result_v0.1.0.toml"
)
SCRIPT_PATH = ROOT / "scripts" / "run_steering_state_metric_benchmarks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "steering_state_metric_benchmark_script", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SteeringStateMetricFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULT_PATH.open("rb") as stream:
            cls.frozen = tomllib.load(stream)
        module = _load_script()
        cls.summary = module.summary_report(module.build_report())

    def test_source_and_reference_objectives_match_frozen_result(self) -> None:
        self.assertAlmostEqual(
            self.frozen["source_candidate"]["total_objective"],
            self.summary["source_total_objective"],
            places=14,
        )
        self.assertAlmostEqual(
            self.frozen["reference_candidate"]["total_objective"],
            self.summary["reference_total_objective"],
            places=12,
        )

    def test_target_contract_matches_frozen_result(self) -> None:
        frozen_targets = self.frozen["objective_contract"]["targets"]
        actual = {
            item["objective_id"]: item
            for item in self.summary["best_objective_contributions"]
        }
        self.assertEqual(len(frozen_targets), len(actual))
        for target in frozen_targets:
            objective_id = f"{target['metric_id']}:{target['state_id']}"
            item = actual[objective_id]
            self.assertAlmostEqual(target["normalization_scale"], item["normalization_scale"], places=14)
            self.assertAlmostEqual(target["objective_weight"], item["weight"], places=14)
            self.assertAlmostEqual(0.0, item["raw_value"], places=14)
            self.assertAlmostEqual(0.0, item["weighted_contribution"], places=14)

    def test_source_metric_pairs_match_frozen_result(self) -> None:
        for state_id, frozen_pairs in self.frozen["source_metric_pairs"].items():
            actual_pairs = self.summary["source_metric_pairs"][state_id]
            for metric_id, expected_pair in frozen_pairs.items():
                actual_pair = actual_pairs[metric_id]
                self.assertEqual(2, len(actual_pair))
                self.assertAlmostEqual(expected_pair[0], actual_pair[0], places=14)
                self.assertAlmostEqual(expected_pair[1], actual_pair[1], places=14)

    def test_recovery_matches_frozen_result(self) -> None:
        frozen = self.frozen["recovery"]
        self.assertAlmostEqual(
            frozen["recovered_rack_longitudinal_offset_m"],
            self.summary["recovered_rack_longitudinal_offset_m"],
            places=14,
        )
        self.assertAlmostEqual(
            frozen["absolute_error_m"],
            self.summary["recovery_absolute_error_m"],
            places=20,
        )
        self.assertAlmostEqual(
            frozen["best_total_objective"],
            self.summary["best_total_objective"],
            places=14,
        )

    def test_search_counts_match_frozen_result(self) -> None:
        frozen = self.frozen["search"]
        self.assertEqual(frozen["evaluated_candidate_count"], self.summary["evaluated_candidate_count"])
        self.assertEqual(frozen["feasible_candidate_count"], self.summary["feasible_candidate_count"])
        self.assertEqual(frozen["infeasible_candidate_count"], self.summary["infeasible_candidate_count"])
        self.assertEqual(frozen["retained_candidate_count"], self.summary["retained_candidate_count"])
        self.assertEqual(self.frozen["method_id"], self.summary["method_id"])


if __name__ == "__main__":
    unittest.main()
