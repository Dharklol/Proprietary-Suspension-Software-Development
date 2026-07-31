from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
VEHICLE_SOURCE = (
    ROOT / "benchmarks/vehicle/WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml"
)
READINESS = ROOT / "data_catalog/r25b_steering_target_input_readiness_v1.toml"


class R25bSteeringTargetInputReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with VEHICLE_SOURCE.open("rb") as stream:
            cls.vehicle = tomllib.load(stream)
        with READINESS.open("rb") as stream:
            cls.readiness = tomllib.load(stream)

    def test_current_vehicle_states_are_evidence_only_and_unweighted(self) -> None:
        states = self.vehicle["states"]
        self.assertEqual(len(states), 2)
        self.assertTrue(all(state["role"] == "evidence_only" for state in states))
        self.assertTrue(all(state["state_weight"] == 0.0 for state in states))

    def test_all_front_wheels_preserve_missing_tire_inputs(self) -> None:
        required_missing = {
            "inclination_deg",
            "pressure_kpa",
            "lateral_force_demand_n",
        }
        for state in self.vehicle["states"]:
            front = [
                wheel
                for wheel in state["wheels"]
                if wheel["position"] in {"front_left", "front_right"}
            ]
            self.assertEqual(len(front), 2)
            for wheel in front:
                self.assertTrue(required_missing.issubset(wheel["missing_reasons"]))

    def test_front_load_domain_dispositions_match_source_values(self) -> None:
        audited = {item["id"]: item for item in self.readiness["vehicle_states"]}
        source = {item["id"]: item for item in self.vehicle["states"]}

        right = source["SC26_EDGE3_1P2G_RIGHT_AERO_NO_ARB"]
        right_wheels = {wheel["position"]: wheel for wheel in right["wheels"]}
        self.assertAlmostEqual(
            audited[right["id"]]["front_inside_normal_load_n"],
            right_wheels["front_right"]["normal_load_n"],
        )
        self.assertAlmostEqual(
            audited[right["id"]]["front_outside_normal_load_n"],
            right_wheels["front_left"]["normal_load_n"],
        )
        self.assertEqual(
            audited[right["id"]]["front_inside_load_domain_status"],
            "below_r25b_minimum",
        )
        self.assertEqual(
            audited[right["id"]]["front_outside_load_domain_status"],
            "above_r25b_maximum",
        )

        left = source["SC26_EDGE4_1P2G_LEFT_AERO_NO_ARB"]
        left_wheels = {wheel["position"]: wheel for wheel in left["wheels"]}
        self.assertAlmostEqual(
            audited[left["id"]]["front_inside_normal_load_n"],
            left_wheels["front_left"]["normal_load_n"],
        )
        self.assertAlmostEqual(
            audited[left["id"]]["front_outside_normal_load_n"],
            left_wheels["front_right"]["normal_load_n"],
        )
        self.assertEqual(
            audited[left["id"]]["front_inside_load_domain_status"],
            "inside_bounded_load_interval_but_not_exact_knot",
        )
        self.assertEqual(
            audited[left["id"]]["front_outside_load_domain_status"],
            "above_r25b_maximum",
        )

    def test_no_current_state_is_promoted_to_a_tire_or_steering_target(self) -> None:
        readiness = self.readiness["readiness"]
        self.assertEqual(readiness["states_ready_for_exact_r25b_force_demand_handoff"], 0)
        self.assertEqual(readiness["states_ready_for_bounded_r25b_runtime_query"], 0)
        self.assertEqual(readiness["states_ready_for_motion_aware_steering_target"], 0)
        self.assertFalse(readiness["steering_design_ranking_authorized"])
        self.assertFalse(readiness["track_scale_authorized"])

    def test_missing_input_policy_forbids_hidden_completion(self) -> None:
        missing = self.readiness["missing_inputs"]
        self.assertEqual(
            set(missing["required_for_each_front_wheel"]),
            {"inclination_deg", "pressure_kpa_gauge", "lateral_force_demand_n"},
        )
        self.assertEqual(
            set(missing["required_for_each_target_state"]),
            {
                "suspension_pose_state_id",
                "planar_motion_u_v_r_at_target_resolution",
                "reviewed_state_weight",
            },
        )
        self.assertIn("Do not infer", missing["rule"])

    def test_program_disposition_pauses_wrong_subsystem_expansion(self) -> None:
        disposition = self.readiness["program_disposition"]
        self.assertTrue(disposition["r25b_steering_extension_paused"])
        self.assertIn("suspension", disposition["pause_reason"])
        self.assertIn("vehicle-state", disposition["pause_reason"])
        self.assertIn(
            "PDR claim closeout and figure selection",
            disposition["immediate_focus"],
        )
        self.assertIn(
            "reviewed zero-steer suspension-pose series",
            disposition["resume_requires"],
        )
        self.assertIn(
            "reviewed synchronized vehicle and tire-demand state package",
            disposition["resume_requires"],
        )


if __name__ == "__main__":
    unittest.main()
