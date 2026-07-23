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
    / "steering_constraint_sensitivity_result_v0.1.0.toml"
)
SCRIPT_PATH = ROOT / "scripts" / "run_steering_constraint_sensitivity_benchmarks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "steering_constraint_sensitivity_benchmark_script", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SteeringConstraintSensitivityFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULT_PATH.open("rb") as stream:
            cls.frozen = tomllib.load(stream)
        module = _load_script()
        cls.summary = module.summary_report(module.build_report())

    def test_reference_screening_matches_frozen_result(self) -> None:
        frozen = self.frozen["reference_screening"]
        self.assertEqual(
            frozen["feasible"], self.summary["reference_screened_feasible"]
        )
        self.assertAlmostEqual(
            frozen["base_objective"], self.summary["reference_objective"], places=14
        )
        self.assertEqual(
            frozen["active_constraint_count"],
            self.summary["active_constraint_count"],
        )
        self.assertEqual(
            frozen["active_constraint_pass_count"],
            self.summary["active_constraint_pass_count"],
        )
        self.assertEqual(
            frozen["unavailable_constraint_ids"],
            self.summary["unavailable_constraint_ids"],
        )

    def test_local_sensitivity_matches_frozen_result(self) -> None:
        frozen = self.frozen["local_sensitivity"]
        self.assertEqual(frozen["variable_id"], self.summary["sensitivity_variable_id"])
        self.assertEqual(frozen["scheme"], self.summary["sensitivity_scheme"])
        self.assertAlmostEqual(
            frozen["step_m"], self.summary["sensitivity_step"], places=14
        )
        self.assertAlmostEqual(
            frozen["objective_derivative_per_m"],
            self.summary["objective_derivative_per_unit"],
            places=12,
        )
        self.assertAlmostEqual(
            frozen["normalized_objective_derivative_over_full_variable_span"],
            self.summary["normalized_objective_derivative"],
            places=12,
        )

    def test_candidate_comparison_matches_frozen_result(self) -> None:
        frozen = self.frozen["candidate_comparison"]
        self.assertEqual(
            frozen["screened_candidate_count"],
            self.summary["comparison_screened_candidate_count"],
        )
        self.assertEqual(
            frozen["screened_feasible_count"],
            self.summary["comparison_screened_feasible_count"],
        )
        self.assertEqual(
            frozen["selected_candidate_count"],
            self.summary["comparison_selected_candidate_count"],
        )
        self.assertEqual(
            frozen["excluded_near_duplicate_count"],
            self.summary["comparison_excluded_near_duplicate_count"],
        )
        best = self.summary["selected_candidates"][0]
        self.assertEqual(frozen["best_candidate_id"], best["candidate_id"])
        self.assertAlmostEqual(
            frozen["best_objective"], best["total_objective"], places=14
        )
        self.assertAlmostEqual(
            frozen["best_tie_rod_length_m"], best["tie_rod_length_m"], places=14
        )


if __name__ == "__main__":
    unittest.main()
