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
        self.assertIn("may not duplicate", authorization["architecture"]["composition_rule"].lower())
        prohibited = " ".join(authorization["prohibited"]["items"]).lower()
        self.assertIn("second steering-kinematics evaluator", prohibited)
        self.assertIn("surrogate", prohibited)
        self.assertIn("native suspension", prohibited)
        self.assertIn("already contains tie-rod-induced steering", prohibited)
        self.assertIn("silently applying a nominal", prohibited)
        self.assertIn("synthetic operating-state target", prohibited)
        self.assertIn("optimumk steering toe angle gain", prohibited)
        self.assertIn("43105 r25b", prohibited)
        self.assertIn("12 deg", prohibited)
        self.assertIn("2/3", prohibited)
        self.assertIn("clipping negative vehicle-state normal loads", prohibited)

    def test_optimizer_model_depends_on_analyzer_and_accepts_explicit_motion_provider(self) -> None:
        record = self._load("registry/records/models/MOD-STEER-0002.toml")["record"]
        self.assertEqual("MOD-STEER-0002", record["id"])
        self.assertEqual(["MOD-STEER-0001"], record["dependency_model_ids"])
        self.assertEqual(["MOD-VEH-0001", "MOD-VEH-0002"], record["provider_model_ids"])
        self.assertEqual("AUTH-STEER-0002", record["authorization_id"])
        self.assertEqual("prototype_authorized", record["authorization_state"])
        self.assertIn("no independent steering, suspension, tire, or load equations", record["description"])
        for benchmark_id in (
            "BENCH-STEER-0016",
            "BENCH-STEER-0017",
            "BENCH-STEER-0018",
            "BENCH-STEER-0019",
            "BENCH-STEER-0020",
            "BENCH-STEER-0021",
            "BENCH-STEER-0023",
        ):
            self.assertIn(benchmark_id, record["benchmark_ids"])

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
        self.assertIn("explicit_center_dynamic_toe_targets", target["alternative_modes"])
        self.assertIn("explicit_center_rack_to_wheel_gain_targets", target["alternative_modes"])
        self.assertIn("tire_informed_peak_slip_differential", target["alternative_modes"])
        self.assertEqual("BENCH-STEER-0020", target["tire_target_benchmark_id"])

    def test_operating_state_target_authority_remains_bounded(self) -> None:
        authorization = self._load("authorizations/steering/AUTH-STEER-0002.toml")
        target_provider = authorization["provider_contracts"]["target_provider"]
        self.assertIn("OperatingStateTargetSet", target_provider)
        self.assertIn("StateMetricTargetSet", target_provider)
        self.assertIn("bounded tire-informed differential target route", target_provider)
        vehicle_provider = authorization["provider_contracts"]["vehicle_operating_state_provider"]
        self.assertIn("AUTH-VEH-0001", vehicle_provider)
        self.assertIn("no load-transfer or equilibrium equations", vehicle_provider)

        gate = authorization["required_before_operating_target_merge"]
        self.assertEqual("complete_in_PR25", gate["status"])
        self.assertEqual(["BENCH-STEER-0016", "BENCH-STEER-0017"], gate["benchmark_ids"])
        metric_gate = authorization["required_before_state_metric_objective_merge"]
        self.assertEqual("complete_in_PR27", metric_gate["status"])
        self.assertEqual("34e6c98f1f47e1b986777bf05249db8e54b89ff2", metric_gate["merge_commit"])
        self.assertEqual(["BENCH-STEER-0019"], metric_gate["benchmark_ids"])
        tire_gate = authorization["required_before_tire_target_provider_merge"]
        self.assertEqual("complete_in_PR28", tire_gate["status"])
        self.assertEqual("5ec28ed1932994c75ff616e4d208912259895f7e", tire_gate["merge_commit"])
        self.assertEqual(["BENCH-STEER-0020"], tire_gate["benchmark_ids"])
        vehicle_gate = authorization["required_before_vehicle_operating_state_provider_merge"]
        self.assertEqual("implemented_for_PR29_review", vehicle_gate["status"])
        self.assertEqual(["BENCH-VEH-0001"], vehicle_gate["benchmark_ids"])

    def test_force_demand_target_authorization_is_complete_and_bounded(self) -> None:
        authorization = self._load("authorizations/steering/AUTH-STEER-0003.toml")
        self.assertEqual("complete", authorization["status"])
        self.assertEqual(["BENCH-STEER-0021"], authorization["scope"]["benchmark_ids"])
        self.assertEqual(
            "PR #30, merge commit 1d894d3cc2e252b2cb4b6f1e594da5ae1b6c6ff7",
            authorization["merge_record"],
        )
        self.assertIn("MOD-STEER-0001 remains the only", authorization["architecture"]["steering_evaluator_rule"])
        self.assertIn("never prescribed globally", authorization["architecture"]["regime_rule"])
        prohibited = " ".join(authorization["prohibited"]["items"]).lower()
        self.assertIn("synthetic force-response", prohibited)
        self.assertIn("globally requires anti-ackermann", prohibited)
        self.assertIn("python magic formula rewrite", prohibited)
        self.assertIn("2/3", prohibited)
        self.assertIn("production wufr steering geometry ranking", prohibited)

    def test_motion_aware_vehicle_and_steering_authorizations_are_bounded(self) -> None:
        vehicle = self._load("authorizations/vehicle/AUTH-VEH-0002.toml")
        steering = self._load("authorizations/steering/AUTH-STEER-0004.toml")
        self.assertEqual("review_ready", vehicle["status"])
        self.assertEqual("review_ready", steering["status"])
        self.assertEqual(["MOD-VEH-0002"], vehicle["scope"]["model_ids"])
        self.assertIn("BENCH-STEER-0023", steering["scope"]["benchmark_ids"])
        vehicle_prohibited = " ".join(vehicle["prohibited"]["items"]).lower()
        steering_prohibited = " ".join(steering["prohibited"]["items"]).lower()
        self.assertIn("solving or inferring u, v, r", vehicle_prohibited)
        self.assertIn("assuming the velocity center lies on the rear axle", vehicle_prohibited)
        self.assertIn("inferring u/v/r from steering input", steering_prohibited)
        self.assertIn("synthetic u-v-r schedules", steering_prohibited)
        self.assertIn("global anti-ackermann", steering_prohibited)

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
        for task_id in (
            "P1-STR-001",
            "P1-STR-002",
            "P1-STR-003",
            "P1-STR-004",
            "P1-STR-006A",
            "P1-STR-006B",
            "P1-STR-006C",
            "P1-STR-006F",
            "P1-STR-006G",
            "P1-STR-006H",
            "P1-STR-006I",
            "P1-STR-006J",
        ):
            self.assertEqual("complete", phase_one[task_id]["status"])
        self.assertEqual("review_ready", phase_one["P1-STR-006L"]["status"])
        self.assertEqual("active", phase_one["P1-STR-006D"]["status"])
        self.assertEqual("active", phase_one["P1-STR-006E"]["status"])
        self.assertIn("explicitly deferred", phase_one["P1-STR-006E"]["execution_rule"].lower())
        self.assertEqual(["P1-STR-001"], phase_one["P1-STR-002"]["depends_on"])
        self.assertEqual(["P1-STR-002"], phase_one["P1-STR-003"]["depends_on"])
        self.assertEqual(["P1-STR-003"], phase_one["P1-STR-004"]["depends_on"])
        self.assertEqual(["P1-STR-006A"], phase_one["P1-STR-006B"]["depends_on"])
        self.assertEqual(["P1-STR-006B"], phase_one["P1-STR-006C"]["depends_on"])
        self.assertEqual(["P1-STR-006A", "P1-STR-006B"], phase_one["P1-STR-006F"]["depends_on"])
        self.assertEqual(["P1-STR-006B", "P1-STR-006C"], phase_one["P1-STR-006G"]["depends_on"])
        self.assertEqual(["P1-STR-006C", "P1-STR-006G"], phase_one["P1-STR-006H"]["depends_on"])
        self.assertEqual(["P1-STR-006H"], phase_one["P1-STR-006I"]["depends_on"])
        self.assertEqual(["P1-STR-006H", "P1-STR-006I"], phase_one["P1-STR-006J"]["depends_on"])
        self.assertEqual(["P1-STR-006J"], phase_one["P1-STR-006L"]["depends_on"])
        self.assertIn("P0-STR-011", phase_one["P1-STR-006E"]["depends_on"])


if __name__ == "__main__":
    unittest.main()
