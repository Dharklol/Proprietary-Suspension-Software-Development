from __future__ import annotations

from pathlib import Path
import unittest

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    OperatingStateTargetSet,
    OperatingTargetRole,
    SearchSettings,
    evaluate_operating_state_candidate,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    load_synthetic_operating_target_fixture,
    resolve_candidate,
    run_operating_state_inverse_design,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
SAMPLING_TARGET_PATH = ROOT / "benchmarks" / "steering" / "WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
POSE_SET_PATH = ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_POSE_SET_V0.toml"
OPERATING_FIXTURE_PATH = ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_OPERATING_TARGETS_V0.toml"


class SteeringOperatingStateTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)
        cls.sampling_target = load_historical_fit_target(SAMPLING_TARGET_PATH)
        cls.pose_set = load_pose_set(POSE_SET_PATH)
        cls.fixture = load_synthetic_operating_target_fixture(
            OPERATING_FIXTURE_PATH,
            cls.baseline,
            cls.requirement,
            cls.sampling_target,
            cls.pose_set,
        )
        cls.source_values = dict(cls.fixture.source_candidate_values)

    def test_fixture_assigns_explicit_objective_weights_to_all_three_states(self) -> None:
        target_set = self.fixture.target_set
        self.assertEqual("sum_weighted_normalized_state_rms", target_set.aggregation_method)
        self.assertIs(target_set.unlisted_state_role, OperatingTargetRole.REPORT_ONLY)
        self.assertEqual(
            {"nominal", "symmetric_bump_5mm", "opposed_travel_5mm"},
            {item.state_id for item in target_set.objective_states},
        )
        weights = {item.state_id: item.objective_weight for item in target_set.objective_states}
        self.assertEqual(1.0, weights["nominal"])
        self.assertEqual(0.8, weights["symmetric_bump_5mm"])
        self.assertEqual(0.6, weights["opposed_travel_5mm"])

    def test_synthetic_source_candidate_has_zero_aggregated_objective(self) -> None:
        candidate = resolve_candidate(
            self.requirement,
            self.source_values,
            candidate_id="OPERATING-TARGET-SOURCE-CHECK",
        )
        evaluation = evaluate_operating_state_candidate(
            self.baseline,
            self.requirement,
            candidate,
            self.fixture.target_set,
            self.pose_set,
        )
        self.assertTrue(evaluation.feasible)
        self.assertEqual(3, len(evaluation.objectives))
        self.assertAlmostEqual(0.0, evaluation.total_objective or 0.0, places=12)
        for objective in evaluation.objectives:
            self.assertAlmostEqual(0.0, objective.raw_value, places=12)

    def test_unlisted_pose_state_is_report_only_not_silently_targeted(self) -> None:
        nominal_target = self.fixture.target_set.state_map["nominal"]
        reduced = OperatingStateTargetSet(
            target_set_id="OPERATING-REPORT-ONLY-CHECK",
            version="0",
            pose_set_id=self.pose_set.pose_set_id,
            sampling_target=self.sampling_target,
            state_targets=(nominal_target,),
            aggregation_method="sum_weighted_normalized_state_rms",
            unlisted_state_role=OperatingTargetRole.REPORT_ONLY,
            authority="unit-test",
            source_path="unit-test",
        )
        candidate = resolve_candidate(self.requirement, candidate_id="OPERATING-REPORT-ONLY-CANDIDATE")
        evaluation = evaluate_operating_state_candidate(
            self.baseline, self.requirement, candidate, reduced, self.pose_set
        )
        self.assertTrue(evaluation.feasible)
        self.assertEqual(1, len(evaluation.objectives))
        self.assertEqual(3, len(evaluation.multistate.states if evaluation.multistate else ()))
        self.assertIs(
            reduced.state_target("symmetric_bump_5mm").role,
            OperatingTargetRole.REPORT_ONLY,
        )

    def test_multistate_target_changes_reference_candidate_objective(self) -> None:
        reference = resolve_candidate(self.requirement, candidate_id="OPERATING-REFERENCE")
        evaluation = evaluate_operating_state_candidate(
            self.baseline,
            self.requirement,
            reference,
            self.fixture.target_set,
            self.pose_set,
        )
        self.assertTrue(evaluation.feasible)
        self.assertIsNotNone(evaluation.total_objective)
        self.assertGreater(evaluation.total_objective or 0.0, 1.0e-6)
        self.assertEqual(3, len(evaluation.objectives))

    def _search(self):
        return run_operating_state_inverse_design(
            self.baseline,
            self.requirement,
            self.fixture.target_set,
            self.pose_set,
            settings=SearchSettings(
                active_variable_ids=self.fixture.active_variable_ids,
                start_count=2,
                seed=self.fixture.seed,
                maximum_iterations_per_start=16,
                initial_step_fraction=0.25,
                contraction_factor=0.5,
                minimum_step_fraction=0.001,
                start_radius_fraction=0.20,
                retained_candidate_count=8,
            ),
            search_id="STEERING-SYNTHETIC-OPERATING-RECOVERY-V0",
        )

    def test_deterministic_search_recovers_known_multistate_source(self) -> None:
        result = self._search()
        self.assertIsNotNone(result.best)
        best = result.best
        assert best is not None
        recovered = dict(best.candidate_values)["rack_longitudinal_offset"]
        expected = self.source_values["rack_longitudinal_offset"]
        self.assertLessEqual(abs(recovered - expected), self.fixture.recovery_tolerance)
        self.assertLessEqual(best.total_objective or 0.0, self.fixture.objective_tolerance)
        self.assertEqual("bounded_coordinate_pattern_search_v0.1.0", result.method_id)
        self.assertIn(("search_core", "shared_with_nominal_search_v0.1.0"), result.provenance)
        self.assertGreaterEqual(len(result.ranked_candidates), 2)

    def test_operating_state_search_is_repeatable(self) -> None:
        first = self._search()
        second = self._search()
        self.assertEqual(first.evaluated_candidate_count, second.evaluated_candidate_count)
        self.assertEqual(first.feasible_candidate_count, second.feasible_candidate_count)
        self.assertEqual(first.infeasible_candidate_count, second.infeasible_candidate_count)
        self.assertEqual(first.starts, second.starts)
        first_archive = [
            (item.evaluation.candidate_values, item.evaluation.total_objective)
            for item in first.ranked_candidates
        ]
        second_archive = [
            (item.evaluation.candidate_values, item.evaluation.total_objective)
            for item in second.ranked_candidates
        ]
        self.assertEqual(first_archive, second_archive)


if __name__ == "__main__":
    unittest.main()
