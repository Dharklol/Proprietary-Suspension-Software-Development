from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrStaticCarrierWrenchAuthorizationTests(unittest.TestCase):
    def test_authorization_is_narrow_and_implementation_ready(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0011.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0011")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])

        scope = auth["scope"]
        self.assertEqual(scope["model_ids"], ["MOD-VEH-0008"])
        self.assertEqual(
            scope["equation_ids"],
            ["EQ-VEH-0020", "EQ-VEH-0021", "EQ-VEH-0022"],
        )
        self.assertEqual(
            scope["benchmark_ids"],
            ["BENCH-VEH-0015", "BENCH-VEH-0016", "BENCH-VEH-0017"],
        )
        self.assertTrue(scope["static_carrier_wrench_generation_authorized"])
        self.assertTrue(scope["complete_for_authorized_static_gravity_case"])
        self.assertFalse(scope["integrated_level1_linkage_result_publication_authorized"])
        self.assertFalse(scope["rocker_reaction_publication_authorized"])
        self.assertFalse(scope["structural_load_case_packet_authorized"])
        self.assertFalse(scope["maneuver_wrench_generation_authorized"])
        self.assertFalse(scope["installed_as_built_authority"])

    def test_upstream_success_and_corner_contract_are_exact(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0011.toml")
        upstream = auth["input_contract"]
        self.assertEqual(upstream["required_upstream_model"], "MOD-VEH-0007")
        self.assertEqual(upstream["required_authorization"], "AUTH-VEH-0010")
        self.assertEqual(
            upstream["required_result_label"],
            "uncorrelated_design_intent_static_gravity",
        )
        self.assertEqual(
            upstream["required_corner_order"],
            ["front_left", "front_right", "rear_left", "rear_right"],
        )

        source = _load("data_catalog/wufr27_static_carrier_wrench_v0.toml")
        self.assertEqual(source["record_id"], "WUFR27_STATIC_CARRIER_WRENCH_V0")
        self.assertEqual(source["upstream"]["static_equilibrium"]["model_id"], "MOD-VEH-0007")
        self.assertEqual(source["corner_contract"]["order"], upstream["required_corner_order"])
        self.assertFalse(source["corner_contract"]["reaction_reordering_authorized"])
        self.assertFalse(source["corner_contract"]["negative_reaction_authorized"])

    def test_carrier_wrench_contains_only_external_static_case_loads(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0011.toml")
        mechanics = auth["mechanics"]
        self.assertIn("lambda_i*n_road", mechanics["road_force"])
        self.assertIn("m_u,i*g_vector", mechanics["unsprung_gravity"])
        self.assertIn("F_road,i+F_u,i", mechanics["carrier_resultant_force"])
        self.assertIn("r_contact", mechanics["carrier_resultant_moment"])
        self.assertIn("r_wc", mechanics["carrier_resultant_moment"])
        self.assertIn("sprung gravity", mechanics["four_corner_reconstruction"])

        source = _load("data_catalog/wufr27_static_carrier_wrench_v0.toml")
        internal = source["completeness"]["internal_suspension_forces_excluded"]
        for item in ("spring", "anti_roll_bar", "pushrod", "pullrod", "tie_rod", "toe_link"):
            self.assertIn(item, internal)
        self.assertTrue(source["completeness"]["complete_for_authorized_static_gravity_case"])
        self.assertFalse(source["completeness"]["complete_physical_hardware_wrench"])
        self.assertFalse(source["completeness"]["complete_maneuver_wrench"])

    def test_frame_chain_preserves_nonzero_body_pose(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0011.toml")
        frames = auth["frames"]
        self.assertEqual(frames["input_frame"], "WUFR27_NOMINAL_ROAD")
        self.assertEqual(frames["level1_frame"], "WUFR26_OPTIMUMK_SUSPENSION_CANONICAL_AXLE_LOCAL")
        self.assertIn("front or rear axle source x-position", frames["placement_rule"])
        self.assertIn("Rz(psi) Ry(theta) Rx(phi)", frames["rotation_rule"])
        self.assertIn("do not assume", frames["rotation_rule"])

        source = _load("data_catalog/wufr27_static_carrier_wrench_v0.toml")
        frame = source["frame_contract"]
        self.assertIn("x_axle_source", frame["axle_local_to_source_rule"])
        self.assertIn("Rz(psi)Ry(theta)Rx(phi)", frame["body_to_road_rule"])
        self.assertFalse(frame["implicit_identity_authorized"])

    def test_prototype_unsprung_allocation_is_not_promoted(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0011.toml")
        statement = auth["completeness"]["prototype_unsprung_allocation_statement"].lower()
        self.assertIn("5 kg", statement)
        self.assertIn("not a measured distribution", statement)

        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "component-level gravity distribution",
            "historical corner-scale values",
            "balancing forces/couples",
            "assuming road, body, source, and level-1 frames are identical",
            "publishing mod-susp-0007 linkage forces",
        ):
            self.assertIn(phrase, prohibited)

    def test_model_equation_and_benchmark_links_are_consistent(self) -> None:
        model = _load("registry/records/models/MOD-VEH-0008.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0011")
        self.assertEqual(
            model["equation_ids"],
            ["EQ-VEH-0020", "EQ-VEH-0021", "EQ-VEH-0022"],
        )
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-VEH-0015", "BENCH-VEH-0016", "BENCH-VEH-0017"],
        )
        self.assertIn("MOD-VEH-0007", model["upstream_model_ids"])
        self.assertEqual(model["downstream_model_ids"], ["MOD-SUSP-0007"])

        for equation_id in model["equation_ids"]:
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(equation["authorization_id"], "AUTH-VEH-0011")
            self.assertIn("MOD-VEH-0008", equation["target_ids"])

        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-VEH-0008", benchmark["target_ids"])
            self.assertEqual(
                benchmark["authorization"],
                "authorizations/vehicle/AUTH-VEH-0011.toml",
            )

    def test_next_gate_remains_separate(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0011.toml")
        gates = "\n".join(auth["promotion_gates"]["items"]).lower()
        self.assertIn("separate downstream authorization", gates)
        self.assertIn("mod-susp-0007", gates)
        self.assertIn("kw v5 non-spring static force", gates)


if __name__ == "__main__":
    unittest.main()
