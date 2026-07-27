from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrSpringRockerForceAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0014_is_spring_only_physical_vector_authority(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0014.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0014")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["physical_spring_force_vector_authorized"])
        self.assertFalse(scope["rocker_equilibrium_authorized"])
        self.assertFalse(scope["rocker_pivot_reaction_authorized"])
        self.assertFalse(scope["damper_force_authorized"])
        self.assertFalse(scope["arb_structural_composition_authorized"])
        self.assertFalse(scope["structural_release_authorized"])

    def test_exact_physical_force_and_virtual_work_identity_are_frozen(self) -> None:
        eq = _load("registry/records/equations/EQ-SUSP-0028.toml")["record"]
        equation = eq["canonical_equation"].lower()
        self.assertIn("e=(d-c)/||d-c||", equation)
        self.assertIn("f_rocker=f_s*e", equation)
        self.assertIn("f_chassis=-f_s*e", equation)
        self.assertIn("dl_d/dtheta", equation)
        self.assertIn("tau_s", equation)
        self.assertIn("f_s*dl_d/dtheta", equation)

    def test_source_record_preserves_existing_spring_and_actuation_ownership(self) -> None:
        source = _load("data_catalog/wufr27_spring_physical_rocker_force_v0.toml")
        self.assertEqual(source["configuration_id"], "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertEqual(source["source"]["actuation"]["model_id"], "MOD-SUSP-0003")
        self.assertEqual(source["source"]["spring_provider"]["model_id"], "MOD-SUSP-0004")
        self.assertAlmostEqual(
            float(source["source"]["spring_package"]["front_nominal_eye_to_eye_m"]),
            0.16459934705216787,
        )
        self.assertAlmostEqual(
            float(source["source"]["spring_package"]["rear_nominal_eye_to_eye_m"]),
            0.1646105387908077,
        )
        self.assertFalse(source["boundaries"]["damper_gas_force_authorized"])
        self.assertFalse(source["boundaries"]["rocker_pivot_reaction_authorized"])

    def test_non_spring_damper_physics_cannot_enter_this_bridge(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0014.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "damper velocity force",
            "gas force",
            "seal friction",
            "bump/top-out",
            "rocker pivot reaction",
            "motion ratio",
        ):
            self.assertIn(phrase, prohibited)
        assumption = _load("registry/records/assumptions/ASM-SUSP-0007.toml")["record"]
        self.assertIn("spring contribution", assumption["description"].lower())
        self.assertIn("gas force", assumption["control"].lower())

    def test_benchmark_and_next_gate_keep_rocker_equilibrium_separate(self) -> None:
        benchmark = _load("registry/records/benchmarks/BENCH-SUSP-0025.toml")["record"]
        text = "\n".join(benchmark["acceptance_criteria"]).lower()
        self.assertIn("action-reaction", text)
        self.assertIn("torque/virtual-work", text)
        self.assertIn("degenerate_eye_line", text)
        auth = _load("authorizations/suspension/AUTH-SUSP-0014.toml")
        last_gate = auth["promotion_gates"]["items"][-1].lower()
        self.assertIn("damper gas", last_gate)
        self.assertIn("rocker pivot", last_gate)


if __name__ == "__main__":
    unittest.main()
