from __future__ import annotations

from pathlib import Path
import unittest

from pssd_steering import load_geometry
from pssd_steering.optimization import load_historical_fit_target, load_pose_set, load_requirement_set, resolve_candidate
from pssd_steering.optimization.state_metrics import (
    StateMetricId,
    build_analyzer_state_metric_target_set,
    evaluate_state_metric_candidate,
    state_metric_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
SAMPLING_TARGET_PATH = ROOT / "benchmarks" / "steering" / "WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
POSE_SET_PATH = ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_POSE_SET_V0.toml"


class SteeringStateMetricObjectiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)
        cls.sampling_target = load_historical_fit_target(SAMPLING_TARGET_PATH)
        cls.pose_set = load_pose_set(POSE_SET_PATH)
        cls.source_values = {"rack_longitudinal_offset": 0.01875}
        cls.target_set = build_analyzer_state_metric_target_set(
            cls.baseline,
            cls.requirement,
            cls.source_values,
            cls.sampling_target,
            cls.pose_set,
            target_set_id="STEERING-SYNTHETIC-STATE-METRICS-V0",
            version="0.1.0",
            state_metric_weights={
                ("symmetric_bump_5mm", StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE): 1.0,
                ("opposed_travel_5mm", StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE): 0.8,
                ("nominal", StateMetricId.CENTER_RACK_TO_WHEEL_GAIN): 0.6,
                ("symmetric_bump_5mm", StateMetricId.CENTER_RACK_TO_WHEEL_GAIN): 0.6,
            },
            authority="software_verification_only",
            source_path="unit-test",
        )

    def test_analyzer_source_has_zero_dynamic_toe_and_gain_objective(self) -> None:
        candidate = resolve_candidate(
            self.requirement,
            self.source_values,
            candidate_id="STATE-METRIC-SOURCE",
        )
        result = evaluate_state_metric_candidate(
            self.baseline, self.requirement, candidate, self.target_set, self.pose_set
        )
        self.assertTrue(result.feasible)
        self.assertEqual(4, len(result.objectives))
        self.assertAlmostEqual(0.0, result.total_objective or 0.0, places=12)

    def test_reference_geometry_differs_from_source_metric_targets(self) -> None:
        candidate = resolve_candidate(self.requirement, candidate_id="STATE-METRIC-REFERENCE")
        result = evaluate_state_metric_candidate(
            self.baseline, self.requirement, candidate, self.target_set, self.pose_set
        )
        self.assertTrue(result.feasible)
        self.assertGreater(result.total_objective or 0.0, 1.0e-6)

    def test_gain_is_explicitly_state_dependent(self) -> None:
        candidate = resolve_candidate(
            self.requirement,
            self.source_values,
            candidate_id="STATE-METRIC-GAIN-STATE-CHECK",
        )
        result = evaluate_state_metric_candidate(
            self.baseline, self.requirement, candidate, self.target_set, self.pose_set
        )
        assert result.multistate is not None
        nominal = result.multistate.state_map["nominal"]
        bump = result.multistate.state_map["symmetric_bump_5mm"]
        nominal_gain = state_metric_pair(
            nominal,
            self.sampling_target.rack_displacements,
            StateMetricId.CENTER_RACK_TO_WHEEL_GAIN,
        )
        bump_gain = state_metric_pair(
            bump,
            self.sampling_target.rack_displacements,
            StateMetricId.CENTER_RACK_TO_WHEEL_GAIN,
        )
        self.assertNotEqual(nominal_gain, bump_gain)

    def test_dynamic_toe_uses_side_local_center_change(self) -> None:
        candidate = resolve_candidate(
            self.requirement,
            self.source_values,
            candidate_id="STATE-METRIC-TOE-CONVENTION-CHECK",
        )
        result = evaluate_state_metric_candidate(
            self.baseline, self.requirement, candidate, self.target_set, self.pose_set
        )
        assert result.multistate is not None
        state = result.multistate.state_map["opposed_travel_5mm"]
        pair = state_metric_pair(
            state,
            self.sampling_target.rack_displacements,
            StateMetricId.CENTER_DYNAMIC_TOE_OUT_CHANGE,
        )
        self.assertAlmostEqual(state.center_left_side_local_toe_out_change_deg or 0.0, pair[0])
        self.assertAlmostEqual(state.center_right_side_local_toe_out_change_deg or 0.0, pair[1])


if __name__ == "__main__":
    unittest.main()
