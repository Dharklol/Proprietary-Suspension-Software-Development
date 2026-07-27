from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrInterfaceStaticsAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0012_authorizes_only_level1_three_body_path(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0012.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0012")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        self.assertTrue(auth["scope"]["wufr27_level1_interface_statics_authorized"])
        self.assertTrue(auth["scope"]["wufr27_current_member_interface_outputs_authorized"])
        self.assertFalse(auth["scope"]["wufr_load_case_generation_authorized"])
        self.assertFalse(auth["scope"]["rocker_reaction_propagation_authorized"])
        self.assertFalse(auth["scope"]["individual_a_arm_joint_split_authorized"])
        self.assertFalse(auth["scope"]["structural_release_authorized"])
        self.assertEqual(auth["topology"]["scalar_unknown_count"], 18)
        self.assertEqual(auth["topology"]["scalar_equilibrium_count"], 18)
        self.assertEqual(auth["topology"]["front_actuation_owner"], "upper_a_arm")
        self.assertEqual(auth["topology"]["rear_actuation_owner"], "lower_a_arm")
        self.assertFalse(auth["topology"]["rocker_in_first_graph"])

    def test_reviewer_carryover_and_level1_output_decisions_are_frozen(self) -> None:
        source = _load("data_catalog/wufr27_level1_linkage_topology_v0.toml")
        reviewer = source["reviewer_confirmation"]
        self.assertEqual(reviewer["date"], "2026-07-27")
        self.assertTrue(reviewer["carryover_authorized"])
        self.assertTrue(reviewer["level1_interface_output_authorized"])
        self.assertFalse(reviewer["individual_tab_or_member_output_authorized"])
        decision = reviewer["decision"].lower()
        for phrase in ("same suspension load paths", "geometry", "hardware", "level 1"):
            self.assertIn(phrase, decision)

    def test_connection_inference_is_source_bounded(self) -> None:
        source = _load("data_catalog/wufr27_level1_linkage_topology_v0.toml")
        joint = source["joint_model"]
        self.assertIn("spherical", joint["upper_arm_upright"].lower())
        self.assertIn("spherical", joint["lower_arm_upright"].lower())
        self.assertIn("revolute", joint["upper_arm_inboard"].lower())
        self.assertIn("revolute", joint["lower_arm_inboard"].lower())
        self.assertIn("axial two-force", joint["front_tie_rod"].lower())
        self.assertIn("axial two-force", joint["rear_toe_link"].lower())
        self.assertIn("upper-a-arm", joint["front_pullrod"].lower())
        self.assertIn("lower-a-arm", joint["rear_pushrod"].lower())

        front = "\n".join(source["source"]["front_corner_assembly"]["observations"]).lower()
        rear = "\n".join(source["source"]["rear_corner_assembly"]["observations"]).lower()
        self.assertIn("explicit reviewed inference", front)
        self.assertIn("explicit reviewed inference", rear)

    def test_exact_reaction_space_and_no_hinge_axis_moment_are_frozen(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0012.toml")
        self.assertEqual(len(auth["topology"]["unknown_order"]), 18)
        self.assertIn("only two moment components perpendicular", auth["joints"]["upper_inboard"].lower())
        self.assertIn("only two moment components perpendicular", auth["joints"]["lower_inboard"].lower())

        eq23 = _load("registry/records/equations/EQ-SUSP-0023.toml")["record"]
        self.assertIn("m_hinge dot u_h=0", eq23["canonical_equation"].lower())
        eq24 = _load("registry/records/equations/EQ-SUSP-0024.toml")["record"]
        self.assertIn("exactly eighteen scalar unknowns", eq24["description"].lower())

    def test_complete_external_wrench_and_numerical_fail_closed_rules(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0012.toml")
        self.assertTrue(auth["external_wrench_contract"]["required"])
        rule = auth["external_wrench_contract"]["rule"].lower()
        self.assertIn("complete", rule)
        self.assertIn("source_id", rule)
        self.assertFalse(auth["numerics"]["least_squares_allowed"])
        self.assertFalse(auth["numerics"]["pseudoinverse_allowed"])
        self.assertFalse(auth["numerics"]["regularization_allowed"])
        self.assertFalse(auth["numerics"]["stiffness_weighting_allowed"])
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertAlmostEqual(float(auth["numerics"]["condition_limit"]), 1.0e10)

    def test_benchmarks_freeze_analytical_geometry_and_failure_gates(self) -> None:
        b21 = _load("registry/records/benchmarks/BENCH-SUSP-0021.toml")["record"]
        b21_text = "\n".join(b21["acceptance_criteria"])
        self.assertIn("18x18", b21["title"])
        self.assertIn("740.690663077577", b21_text)
        self.assertIn("256.1483168750569", b21_text)

        b22 = _load("registry/records/benchmarks/BENCH-SUSP-0022.toml")["record"]
        b22_text = "\n".join(b22["acceptance_criteria"]).lower()
        self.assertIn("pullrod force column acts on the uca", b22_text)
        self.assertIn("pushrod force column acts on the lca", b22_text)
        self.assertIn("current steering-closure tie-rod geometry", b22_text)

        b23 = _load("registry/records/benchmarks/BENCH-SUSP-0023.toml")["record"]
        b23_text = "\n".join(b23["acceptance_criteria"]).lower()
        for phrase in ("rigidly translating", "hinge-axis sign", "singular_equilibrium", "incomplete_external_wrench", "negative-to-zero"):
            self.assertIn(phrase, b23_text)

    def test_auth_0011_hold_is_resolved_only_for_the_new_path(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0012.toml")
        resolution = auth["auth_susp_0011_resolution"]
        self.assertTrue(resolution["resolved_for_this_path"])
        self.assertIn("mod-susp-0006", resolution["remaining_hold"].lower())
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("six-links-to-upright", prohibited)
        self.assertIn("forward/aft", prohibited)
        self.assertIn("negative", prohibited)


if __name__ == "__main__":
    unittest.main()
