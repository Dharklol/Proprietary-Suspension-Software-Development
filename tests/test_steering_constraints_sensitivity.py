from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    CandidateComparisonSettings,
    ConstraintAvailability,
    ConstraintDisposition,
    SearchSettings,
    SensitivitySettings,
    analyze_local_sensitivity,
    build_candidate_comparison,
    candidate_comparison_report,
    evaluate_candidate,
    load_constraint_set,
    load_historical_fit_target,
    load_requirement_set,
    load_synthetic_recovery_fixture,
    local_sensitivity_report,
    resolve_candidate,
    run_nominal_inverse_design,
    screen_candidate_evaluation,
    screened_candidate_report,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = ROOT / "configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml"
CONSTRAINT_PATH = ROOT / "configurations/steering/STEERING_CONSTRAINT_PROVIDER_DEV_V0.toml"
HISTORICAL_PATH = ROOT / "benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
SYNTHETIC_PATH = ROOT / "benchmarks/steering/STEERING_SYNTHETIC_RECOVERY_V0.toml"


class SteeringConstraintSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)
        cls.constraint_set = load_constraint_set(CONSTRAINT_PATH)
        cls.historical_target = load_historical_fit_target(HISTORICAL_PATH)
        cls.synthetic = load_synthetic_recovery_fixture(
            SYNTHETIC_PATH,
            cls.baseline,
            cls.requirement,
        )

    def reference_evaluation(self):
        candidate = resolve_candidate(
            self.requirement,
            candidate_id="CONSTRAINT-REFERENCE",
        )
        return candidate, evaluate_candidate(
            self.baseline,
            self.requirement,
            candidate,
            self.historical_target,
        )

    def test_constraint_provider_separates_active_and_unavailable_evidence(self) -> None:
        active = [
            item
            for item in self.constraint_set.constraints
            if item.availability is ConstraintAvailability.ACTIVE
        ]
        unavailable = [
            item
            for item in self.constraint_set.constraints
            if item.availability is ConstraintAvailability.UNAVAILABLE
        ]
        self.assertEqual(3, len(active))
        self.assertEqual(6, len(unavailable))
        self.assertTrue(all(not item.blocking for item in unavailable))

        _, evaluation = self.reference_evaluation()
        screened = screen_candidate_evaluation(evaluation, self.constraint_set)
        self.assertTrue(screened.feasible)
        dispositions = {
            item.constraint_id: item.disposition
            for item in screened.supplemental_constraints
        }
        self.assertEqual(
            ConstraintDisposition.PASSED,
            dispositions["tie_rod_joint_center_length"],
        )
        self.assertEqual(
            ConstraintDisposition.UNAVAILABLE,
            dispositions["rod_end_articulation"],
        )
        self.assertIn("thread_engagement", screened.unavailable_constraint_ids)

    def test_blocking_constraint_failure_removes_objective_from_screened_use(self) -> None:
        _, evaluation = self.reference_evaluation()
        assert evaluation.generated is not None
        short_generated = replace(
            evaluation.generated,
            left_tie_rod_length=0.10,
            right_tie_rod_length=0.10,
        )
        altered = replace(evaluation, generated=short_generated)
        screened = screen_candidate_evaluation(altered, self.constraint_set)
        self.assertFalse(screened.feasible)
        self.assertEqual("tie_rod_joint_center_length", screened.failure_code)
        self.assertIsNone(screened.total_objective)
        result = next(
            item
            for item in screened.supplemental_constraints
            if item.constraint_id == "tie_rod_joint_center_length"
        )
        self.assertEqual(ConstraintDisposition.FAILED, result.disposition)
        self.assertLess(result.margin or 0.0, 0.0)

    def test_local_sensitivity_is_deterministic_and_analyzer_composed(self) -> None:
        candidate = resolve_candidate(
            self.requirement,
            candidate_id="SENSITIVITY-REFERENCE",
        )
        settings = SensitivitySettings(
            relative_step_fraction=0.001,
            minimum_absolute_step=1.0e-7,
            variable_ids=("rack_longitudinal_offset",),
        )
        first = analyze_local_sensitivity(
            self.baseline,
            self.requirement,
            candidate,
            self.historical_target,
            constraint_set=self.constraint_set,
            settings=settings,
        )
        second = analyze_local_sensitivity(
            self.baseline,
            self.requirement,
            candidate,
            self.historical_target,
            constraint_set=self.constraint_set,
            settings=settings,
        )
        self.assertEqual("complete", first.status)
        self.assertEqual(first.variable_results, second.variable_results)
        self.assertEqual(1, len(first.variable_results))
        variable = first.variable_results[0]
        self.assertEqual("rack_longitudinal_offset", variable.variable_id)
        self.assertEqual("central", variable.scheme)
        self.assertIsNotNone(variable.objective_derivative_per_unit)
        self.assertTrue(variable.lower_feasible)
        self.assertTrue(variable.upper_feasible)
        self.assertGreater(len(variable.constraint_margin_sensitivities), 0)

    def test_candidate_comparison_keeps_differences_and_unavailable_gates_visible(self) -> None:
        search = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=SearchSettings(
                active_variable_ids=self.synthetic.active_variable_ids,
                start_count=2,
                seed=self.synthetic.seed,
                maximum_iterations_per_start=12,
                initial_step_fraction=0.25,
                contraction_factor=0.5,
                minimum_step_fraction=0.01,
                start_radius_fraction=0.20,
                retained_candidate_count=30,
            ),
            search_id="CONSTRAINT-COMPARISON-TEST",
        )
        comparison = build_candidate_comparison(
            search,
            self.requirement,
            self.constraint_set,
            settings=CandidateComparisonSettings(
                maximum_candidates=4,
                minimum_normalized_design_distance=0.0,
            ),
        )
        self.assertGreaterEqual(comparison.screened_candidate_count, 2)
        self.assertGreaterEqual(len(comparison.selected_candidates), 2)
        best = comparison.selected_candidates[0]
        self.assertEqual(0.0, best.objective_delta_from_best)
        self.assertIn("rod_end_articulation", best.unavailable_constraint_ids)
        self.assertIsNotNone(best.tie_rod_length_m)
        self.assertGreaterEqual(
            comparison.selected_candidates[1].objective_delta_from_best,
            0.0,
        )

    def test_new_reports_are_machine_readable(self) -> None:
        candidate, evaluation = self.reference_evaluation()
        screened = screen_candidate_evaluation(evaluation, self.constraint_set)
        screened_payload = screened_candidate_report(screened, self.requirement)
        self.assertTrue(screened_payload["screened_feasible"])
        self.assertIn("supplemental_constraints", screened_payload)

        sensitivity = analyze_local_sensitivity(
            self.baseline,
            self.requirement,
            candidate,
            self.historical_target,
            constraint_set=self.constraint_set,
            settings=SensitivitySettings(
                variable_ids=("rack_longitudinal_offset",),
            ),
        )
        sensitivity_payload = local_sensitivity_report(
            sensitivity, self.requirement
        )
        self.assertEqual("complete", sensitivity_payload["status"])
        self.assertIn("authority_boundary", sensitivity_payload)

        search = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=SearchSettings(
                active_variable_ids=self.synthetic.active_variable_ids,
                start_count=1,
                maximum_iterations_per_start=4,
                retained_candidate_count=10,
            ),
            search_id="REPORT-COMPARISON-TEST",
        )
        comparison = build_candidate_comparison(
            search,
            self.requirement,
            self.constraint_set,
            settings=CandidateComparisonSettings(
                maximum_candidates=2,
                minimum_normalized_design_distance=0.0,
            ),
        )
        comparison_payload = candidate_comparison_report(comparison)
        self.assertIn("selected_candidates", comparison_payload)
        self.assertIn("authority_boundary", comparison_payload)


if __name__ == "__main__":
    unittest.main()
