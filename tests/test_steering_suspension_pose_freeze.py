from __future__ import annotations

import importlib.util
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "benchmarks" / "steering" / "steering_pose_provider_result_v0.1.0.toml"
SCRIPT_PATH = ROOT / "scripts" / "run_steering_pose_provider_benchmarks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("steering_pose_provider_benchmark_script", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SteeringSuspensionPoseFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULT_PATH.open("rb") as stream:
            cls.frozen = tomllib.load(stream)
        module = _load_script()
        cls.summary = module.summary_report(module.build_report())

    def test_identity_state_matches_frozen_result(self) -> None:
        frozen = self.frozen["nominal_identity"]
        self.assertEqual(3, self.summary["state_count"])
        self.assertTrue(self.summary["all_states_feasible"])
        self.assertEqual(frozen["rack_sample_count_per_side"], self.summary["rack_sample_count_per_side"])
        self.assertAlmostEqual(frozen["left_dynamic_toe_deg"], self.summary["nominal_left_dynamic_toe_deg"], places=14)
        self.assertAlmostEqual(frozen["right_dynamic_toe_deg"], self.summary["nominal_right_dynamic_toe_deg"], places=14)

    def test_symmetric_bump_state_matches_frozen_result(self) -> None:
        frozen = self.frozen["symmetric_bump_synthetic"]
        self.assertAlmostEqual(
            frozen["left_side_local_toe_out_change_deg"],
            self.summary["symmetric_bump_left_dynamic_toe_deg"],
            places=12,
        )
        self.assertAlmostEqual(
            frozen["right_side_local_toe_out_change_deg"],
            self.summary["symmetric_bump_right_dynamic_toe_deg"],
            places=12,
        )
        self.assertAlmostEqual(
            frozen["minimum_singularity_ratio"],
            self.summary["symmetric_bump_minimum_singularity_ratio"],
            places=12,
        )

    def test_opposed_travel_state_matches_frozen_result(self) -> None:
        frozen = self.frozen["opposed_travel_synthetic"]
        self.assertAlmostEqual(
            frozen["left_side_local_toe_out_change_deg"],
            self.summary["opposed_travel_left_dynamic_toe_deg"],
            places=12,
        )
        self.assertAlmostEqual(
            frozen["right_side_local_toe_out_change_deg"],
            self.summary["opposed_travel_right_dynamic_toe_deg"],
            places=12,
        )
        self.assertAlmostEqual(
            frozen["minimum_singularity_ratio"],
            self.summary["opposed_travel_minimum_singularity_ratio"],
            places=12,
        )

    def test_authority_boundary_stays_synthetic(self) -> None:
        boundary = self.summary["authority_boundary"].lower()
        self.assertIn("synthetic", boundary)
        self.assertIn("not wufr suspension-motion evidence", boundary)
        self.assertIn("no suspension solver", boundary)


if __name__ == "__main__":
    unittest.main()
