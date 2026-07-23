from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

from pssd_steering import load_geometry, solve_sweep
from pssd_steering.optimization import (
    CandidateEvaluationStatus,
    SearchSettings,
    evaluate_candidate,
    load_historical_fit_target,
    load_requirement_set,
    load_synthetic_recovery_fixture,
    resolve_candidate,
    run_nominal_inverse_design,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = (
    ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
)
HISTORICAL_TARGET_PATH = (
    ROOT / "benchmarks" / "steering" / "WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
)
SYNTHETIC_TARGET_PATH = (
    ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_RECOVERY_V0.toml"
)
RESULT_PATH = (
    ROOT / "benchmarks" / "steering" / "steering_nominal_optimizer_result_v0.1.0.toml"
)


class SteeringNominalOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)
        cls.historical_target = load_historical_fit_target(HISTORICAL_TARGET_PATH)
        cls.synthetic = load_synthetic_recovery_fixture(
            SYNTHETIC_TARGET_PATH,
            cls.baseline,
            cls.requirement,
        )

    def synthetic_settings(self) -> SearchSettings:
        return SearchSettings(
            active_variable_ids=self.synthetic.active_variable_ids,
            start_count=3,
            seed=self.synthetic.seed,
            maximum_iterations_per_start=28,
            initial_step_fraction=0.25,
            contraction_factor=0.5,
            minimum_step_fraction=0.0001,
            start_radius_fraction=0.20,
            retained_candidate_count=8,
        )

    def test_historical_target_contract_preserves_evidence_boundary(self) -> None:
        target = self.historical_target
        self.assertEqual("historical_polynomial_fit", target.source_type)
        self.assertEqual(15, len(target.inputs))
        self.assertEqual(-102.0, target.inputs[0])
        self.assertEqual(102.0, target.inputs[-1])
        self.assertEqual(-1.0, target.canonical_to_target_output_sign)
        self.assertIn("not an independent validation", target.authority)
        self.assertEqual(len(target.inputs), len(target.left_outputs))
        self.assertEqual(len(target.inputs), len(target.right_outputs))

    def test_reference_candidate_uses_complete_analyzer_sweep(self) -> None:
        candidate = resolve_candidate(self.requirement, candidate_id="HISTORICAL-REFERENCE")
        with patch(
            "pssd_steering.optimization.evaluation.solve_sweep",
            wraps=solve_sweep,
        ) as analyzer_sweep:
            evaluation = evaluate_candidate(
                self.baseline,
                self.requirement,
                candidate,
                self.historical_target,
            )
        self.assertEqual(1, analyzer_sweep.call_count)
        self.assertTrue(evaluation.feasible)
        self.assertEqual(CandidateEvaluationStatus.FEASIBLE, evaluation.status)
        self.assertIsNotNone(evaluation.total_objective)
        self.assertGreater(evaluation.total_objective or 0.0, 0.1)
        self.assertLess(evaluation.total_objective or 99.0, 1.5)
        self.assertEqual(2, len(evaluation.analyzer_results))
        self.assertEqual(15, len(evaluation.left_outputs))
        self.assertEqual(15, len(evaluation.right_outputs))
        self.assertTrue(all(item.passed for item in evaluation.constraints))

    def test_infeasible_candidate_has_no_objective_score(self) -> None:
        candidate = resolve_candidate(self.requirement, candidate_id="OUTSIDE-DOMAIN")
        outside_target = replace(
            self.historical_target,
            rack_displacements=tuple(
                2.0 * value for value in self.historical_target.rack_displacements
            ),
        )
        evaluation = evaluate_candidate(
            self.baseline,
            self.requirement,
            candidate,
            outside_target,
        )
        self.assertFalse(evaluation.feasible)
        self.assertEqual("rack_input_domain", evaluation.failure_code)
        self.assertEqual((), evaluation.objectives)
        self.assertIsNone(evaluation.total_objective)
        self.assertFalse(evaluation.constraint_map["rack_input_domain"].passed)

    def test_synthetic_target_is_generated_by_authoritative_analyzer(self) -> None:
        fixture = self.synthetic
        self.assertEqual("analyzer_generated_synthetic", fixture.target.source_type)
        self.assertEqual(("rack_longitudinal_offset",), fixture.active_variable_ids)
        self.assertEqual(9, len(fixture.target.inputs))
        provenance = dict(fixture.target.provenance)
        self.assertEqual("MOD-STEER-0001", provenance["evaluator_model_id"])

    def test_pattern_search_recovers_synthetic_source_parameter(self) -> None:
        result = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=self.synthetic_settings(),
            search_id="SYNTHETIC-RECOVERY-TEST",
        )
        self.assertIsNotNone(result.best)
        best = result.best
        assert best is not None
        source = dict(self.synthetic.source_candidate_values)
        recovered = dict(best.candidate_values)
        self.assertAlmostEqual(
            source["rack_longitudinal_offset"],
            recovered["rack_longitudinal_offset"],
            delta=self.synthetic.recovery_tolerance,
        )
        objective = best.objectives[0].raw_value
        self.assertLessEqual(objective, self.synthetic.objective_tolerance_deg_rms)
        self.assertGreaterEqual(len(result.ranked_candidates), 2)
        self.assertGreater(result.evaluated_candidate_count, result.feasible_candidate_count - 1)
        self.assertEqual("bounded_coordinate_pattern_search_v0.1.0", result.method_id)
        self.assertTrue(any("Hooke" in item for item in result.method_references))

    def test_inactive_variables_remain_at_requirement_references(self) -> None:
        result = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=self.synthetic_settings(),
            search_id="ACTIVE-SUBSET-TEST",
        )
        best = result.best
        assert best is not None
        values = dict(best.candidate_values)
        for variable in self.requirement.variables:
            if variable.id not in self.synthetic.active_variable_ids:
                self.assertAlmostEqual(variable.reference, values[variable.id], places=14)

    def test_repeated_runs_are_identical(self) -> None:
        settings = self.synthetic_settings()
        first = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=settings,
            search_id="REPEATABILITY-A",
        )
        second = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=settings,
            search_id="REPEATABILITY-B",
        )
        self.assertEqual(first.evaluated_candidate_count, second.evaluated_candidate_count)
        self.assertEqual(first.feasible_candidate_count, second.feasible_candidate_count)
        self.assertEqual(
            [item.evaluation.candidate_values for item in first.ranked_candidates],
            [item.evaluation.candidate_values for item in second.ranked_candidates],
        )
        self.assertEqual(
            [item.evaluation.total_objective for item in first.ranked_candidates],
            [item.evaluation.total_objective for item in second.ranked_candidates],
        )
        self.assertEqual(first.starts, second.starts)

    def test_frozen_benchmark_result_matches_current_implementation(self) -> None:
        with RESULT_PATH.open("rb") as stream:
            frozen = tomllib.load(stream)
        candidate = resolve_candidate(self.requirement, candidate_id="FROZEN-HISTORICAL")
        historical = evaluate_candidate(
            self.baseline,
            self.requirement,
            candidate,
            self.historical_target,
        )
        search = run_nominal_inverse_design(
            self.baseline,
            self.requirement,
            self.synthetic.target,
            settings=self.synthetic_settings(),
            search_id="FROZEN-SYNTHETIC",
        )
        best = search.best
        assert best is not None
        historical_record = frozen["historical_reference"]
        recovery_record = frozen["synthetic_recovery"]
        self.assertAlmostEqual(
            historical_record["raw_objective_deg_rms"],
            historical.objectives[0].raw_value,
            places=14,
        )
        recovered = dict(best.candidate_values)["rack_longitudinal_offset"]
        self.assertAlmostEqual(recovery_record["recovered_value_m"], recovered, places=14)
        self.assertAlmostEqual(
            recovery_record["raw_objective_deg_rms"],
            best.objectives[0].raw_value,
            places=14,
        )
        self.assertEqual(
            recovery_record["evaluated_candidate_count"],
            search.evaluated_candidate_count,
        )
        self.assertEqual(
            recovery_record["feasible_candidate_count"],
            search.feasible_candidate_count,
        )
        self.assertEqual(
            recovery_record["infeasible_candidate_count"],
            search.infeasible_candidate_count,
        )
        self.assertEqual(
            recovery_record["retained_ranked_candidate_count"],
            len(search.ranked_candidates),
        )


if __name__ == "__main__":
    unittest.main()
