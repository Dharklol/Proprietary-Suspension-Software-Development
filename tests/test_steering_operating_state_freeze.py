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
    / "steering_operating_state_target_result_v0.1.0.toml"
)
SCRIPT_PATH = ROOT / "scripts" / "run_steering_operating_state_benchmarks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "steering_operating_state_benchmark_script", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SteeringOperatingStateFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULT_PATH.open("rb") as stream:
            cls.frozen = tomllib.load(stream)
        module = _load_script()
        cls.summary = module.summary_report(module.build_report())

    def test_objective_contract_matches_frozen_result(self) -> None:
        frozen = self.frozen["objective_contract"]
        self.assertEqual(frozen["aggregation_method"], "sum_weighted_normalized_state_rms")
        self.assertEqual(frozen["unlisted_state_role"], "report_only")
        self.assertEqual(frozen["objective_state_count"], len(self.summary["objective_states"]))
        expected = [
            (item["state_id"], item["objective_weight"], item["normalization_scale_deg"])
            for item in frozen["states"]
        ]
        actual = [
            (item["state_id"], item["objective_weight"], item["normalization_scale_deg"])
            for item in self.summary["objective_states"]
        ]
        self.assertEqual(expected, actual)

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
        for expected, actual in zip(
            frozen["objective_contributions"],
            self.summary["best_objective_contributions"],
        ):
            self.assertEqual(expected["objective_id"], actual["objective_id"])
            self.assertAlmostEqual(expected["raw_value_deg_rms"], actual["raw_value"], places=14)
            self.assertAlmostEqual(expected["normalized_value"], actual["normalized_value"], places=14)
            self.assertAlmostEqual(expected["weight"], actual["weight"], places=14)
            self.assertAlmostEqual(
                expected["weighted_contribution"], actual["weighted_contribution"], places=14
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
