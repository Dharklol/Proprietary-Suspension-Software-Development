from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SteeringInverseDesignAuthorizationTests(unittest.TestCase):
    def _load(self, relative_path: str) -> dict:
        with (ROOT / relative_path).open("rb") as stream:
            return tomllib.load(stream)

    def test_optimizer_composes_existing_analyzer(self) -> None:
        authorization = self._load("authorizations/steering/AUTH-STEER-0002.toml")
        self.assertEqual("active_reviewed_and_frozen", authorization["status"])
        self.assertEqual("MOD-STEER-0001", authorization["architecture"]["authoritative_evaluator_model_id"])
        self.assertEqual("MOD-STEER-0002", authorization["architecture"]["optimizer_orchestrator_model_id"])
        self.assertIn(
            "may not duplicate",
            authorization["architecture"]["composition_rule"].lower(),
        )
        prohibited = " ".join(authorization["prohibited"]["items"]).lower()
        self.assertIn("second steering-kinematics evaluator", prohibited)
        self.assertIn("surrogate", prohibited)

    def test_optimizer_model_depends_on_analyzer(self) -> None:
        record = self._load("registry/records/models/MOD-STEER-0002.toml")["record"]
        self.assertEqual("MOD-STEER-0002", record["id"])
        self.assertEqual(["MOD-STEER-0001"], record["dependency_model_ids"])
        self.assertEqual("AUTH-STEER-0002", record["authorization_id"])
        self.assertEqual("prototype_authorized", record["authorization_state"])
        self.assertIn("contains no independent steering-kinematics equations", record["description"])

    def test_wufr27_baseline_inherits_frozen_geometry(self) -> None:
        baseline = self._load("configurations/steering/WUFR27_STEERING_BASELINE_V0.toml")
        self.assertEqual("WUFR26_DESIGN_NOMINAL_V0", baseline["authority"]["geometry_source_configuration"])
        self.assertEqual("none_for_WUFR27", baseline["authority"]["geometry_change_intent"])
        self.assertTrue(baseline["inheritance"]["zero_offset_reconstruction_required"])
        self.assertEqual("derived_output", baseline["baseline_roles"]["tie_rod_length"])

    def test_development_requirement_roles_are_selectable(self) -> None:
        requirement_set = self._load("configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
        allowed = set(requirement_set["role_vocabulary"]["allowed"])
        self.assertIn("fixed_parameter", allowed)
        self.assertIn("bounded_design_variable", allowed)
        self.assertIn("discrete_option", allowed)
        self.assertIn("derived_output", allowed)
        self.assertIn("target_curve", allowed)
        self.assertIn("report_only", allowed)

        variables = {item["id"]: item for item in requirement_set["variables"]}
        self.assertEqual(
            {
                "rack_longitudinal_offset",
                "rack_vertical_offset",
                "rack_inner_joint_half_spacing",
                "outer_pickup_local_u_offset",
                "outer_pickup_local_v_offset",
                "outer_pickup_local_depth_offset",
            },
            set(variables),
        )
        for variable in variables.values():
            self.assertEqual("bounded_design_variable", variable["role"])
            self.assertLess(variable["minimum"], variable["maximum"])

    def test_outer_pickup_depth_is_heavily_bounded(self) -> None:
        requirement_set = self._load("configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
        depth = next(
            item
            for item in requirement_set["variables"]
            if item["id"] == "outer_pickup_local_depth_offset"
        )
        self.assertLessEqual(depth["maximum"] - depth["minimum"], 0.010000000001)
        self.assertIn("tightly bounded", depth["coordinate_definition"].lower())

    def test_first_release_enforces_symmetry_but_preserves_future_route(self) -> None:
        requirement_set = self._load("configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
        self.assertEqual("exact_reflection", requirement_set["symmetry"]["mode"])
        self.assertFalse(requirement_set["symmetry"]["independent_sides_enabled"])
        self.assertIn("later requirement set", requirement_set["symmetry"]["future_rule"].lower())

    def test_historical_target_is_regression_not_universal_optimum(self) -> None:
        requirement_set = self._load("configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
        target = requirement_set["target_provider"]
        self.assertEqual("WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0", target["default_target_id"])
        self.assertIn("regression", target["authority"])
        self.assertIn("exact_geometric_ackermann_reference", target["alternative_modes"])
        self.assertIn("future_external_tire_informed_target", target["alternative_modes"])

    def test_candidate_set_and_ranking_remain_visible(self) -> None:
        requirement_set = self._load("configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
        candidate_set = requirement_set["candidate_set"]
        self.assertTrue(candidate_set["return_multiple_candidates"])
        self.assertTrue(candidate_set["nondominated_candidates_required_when_tradeoffs_exist"])
        self.assertTrue(candidate_set["convenience_ranking_allowed"])
        self.assertIn("full feasible candidate set", candidate_set["ranking_rule"].lower())

    def test_physical_tasks_remain_open_but_nonblocking_for_generic_optimizer(self) -> None:
        progress = self._load("registry/progress.toml")
        phase_zero = {task["id"]: task for task in progress["phase_0"]["tasks"]}
        self.assertEqual("active", phase_zero["P0-STR-006"]["status"])
        self.assertEqual("active", phase_zero["P0-STR-011"]["status"])
        self.assertIn("does not block generic", phase_zero["P0-STR-006"]["critical_path_rule"])
        self.assertIn("does not block generic", phase_zero["P0-STR-011"]["critical_path_rule"])

        phase_one = {task["id"]: task for task in progress["phase_1"]["tasks"]}
        self.assertEqual("complete", phase_one["P1-STR-001"]["status"])
        self.assertEqual("complete", phase_one["P1-STR-002"]["status"])
        self.assertEqual("review_ready", phase_one["P1-STR-003"]["status"])
        self.assertEqual(["P1-STR-001"], phase_one["P1-STR-002"]["depends_on"])
        self.assertEqual(["P1-STR-002"], phase_one["P1-STR-003"]["depends_on"])


if __name__ == "__main__":
    unittest.main()
