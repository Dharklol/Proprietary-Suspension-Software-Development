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
    / "steering_tire_informed_target_result_v0.1.0.toml"
)
SCRIPT_PATH = ROOT / "scripts" / "run_steering_tire_target_benchmarks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "steering_tire_target_benchmark_script", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SteeringTireTargetFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULT_PATH.open("rb") as stream:
            cls.frozen = tomllib.load(stream)
        module = _load_script()
        cls.report = module.build_report()
        cls.summary = module.summary_report(cls.report)

    def test_source_and_intended_tire_identity_are_frozen(self) -> None:
        self.assertEqual(self.frozen["tire_grid_id"], self.summary["tire_grid_id"])
        self.assertEqual(self.frozen["source_tire_id"], self.summary["source_tire_id"])
        self.assertEqual(self.frozen["intended_tire_id"], self.summary["intended_tire_id"])
        self.assertNotEqual(self.summary["source_tire_id"], self.summary["intended_tire_id"])

    def test_reference_peak_slip_pair_matches_frozen_result(self) -> None:
        frozen = self.frozen["reference_state"]
        self.assertAlmostEqual(frozen["inside_peak_slip_deg"], self.summary["inside_peak_slip_deg"], places=14)
        self.assertAlmostEqual(frozen["outside_peak_slip_deg"], self.summary["outside_peak_slip_deg"], places=14)
        self.assertAlmostEqual(
            frozen["outside_minus_inside_peak_slip_deg"],
            self.summary["outside_minus_inside_peak_slip_deg"],
            places=14,
        )
        self.assertEqual(frozen["utilization_schedule"], self.report["reference_state"]["utilization_schedule"])

    def test_target_curves_match_frozen_result(self) -> None:
        frozen = self.frozen["target"]
        actual = self.report["target"]
        self.assertEqual(frozen["target_set_id"], actual["target_set_id"])
        self.assertEqual(frozen["source_type"], actual["source_type"])
        self.assertEqual(len(frozen["left_outputs_deg"]), len(actual["left_outputs_deg"]))
        self.assertEqual(len(frozen["right_outputs_deg"]), len(actual["right_outputs_deg"]))
        for expected, observed in zip(frozen["left_outputs_deg"], actual["left_outputs_deg"]):
            self.assertAlmostEqual(expected, observed, places=14)
        for expected, observed in zip(frozen["right_outputs_deg"], actual["right_outputs_deg"]):
            self.assertAlmostEqual(expected, observed, places=14)

    def test_reference_candidate_objective_matches_frozen_result(self) -> None:
        frozen = self.frozen["reference_candidate"]
        actual = self.report["reference_candidate"]
        self.assertEqual(frozen["feasible"], actual["feasible"])
        self.assertAlmostEqual(frozen["total_objective"], actual["total_objective"], places=14)
        self.assertEqual(1, len(actual["objectives"]))
        objective = actual["objectives"][0]
        self.assertEqual(frozen["objective_id"], objective["objective_id"])
        self.assertAlmostEqual(frozen["raw_value_deg_rms"], objective["raw_value"], places=14)
        self.assertAlmostEqual(frozen["weighted_contribution"], objective["weighted_contribution"], places=14)

    def test_historical_scale_is_frozen_but_not_promoted(self) -> None:
        frozen = self.frozen["matlab_reference"]
        actual = self.report["matlab_integration_reference"]
        self.assertAlmostEqual(
            frozen["historical_force_and_moment_scale"],
            actual["historical_force_and_moment_scale"],
            places=14,
        )
        self.assertFalse(frozen["historical_scale_promoted_to_tire_provider"])
        self.assertFalse(actual["historical_scale_promoted_to_tire_provider"])


if __name__ == "__main__":
    unittest.main()
