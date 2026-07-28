from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class RockerIncludedLoadAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0016_is_explicitly_incomplete(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0016.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0016")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["provider_neutral_kernel_authorized"])
        self.assertTrue(scope["wufr_adapter_authorized"])
        self.assertFalse(scope["complete_rocker_equilibrium_authorized"])
        self.assertFalse(scope["complete_pivot_reaction_authorized"])
        self.assertFalse(scope["damper_static_contribution_authorized"])

    def test_ideal_revolute_projection_and_residual_are_frozen(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0016.toml")
        mechanics = auth["mechanics"]
        self.assertIn("F_inc=sum_i F_i", mechanics["included_resultants"])
        self.assertEqual(mechanics["support_force_contribution"], "F_p=-F_inc")
        self.assertIn("a dot M_inc", mechanics["support_moment_contribution"])
        self.assertIn("tau_axis", mechanics["free_axis_residual"])
        self.assertIn("without repair", mechanics["interpretation"].lower())

    def test_wufr_physical_source_ownership_and_missing_damper_are_explicit(self) -> None:
        source = _load("data_catalog/wufr27_rocker_included_load_statics_v0.toml")
        self.assertEqual(source["source"]["level1_interface"]["model_id"], "MOD-SUSP-0007")
        self.assertEqual(source["source"]["spring_force"]["physical_vector_authorization_id"], "AUTH-SUSP-0014")
        self.assertEqual(source["source"]["arb_link_force"]["physical_vector_authorization_id"], "AUTH-SUSP-0013")
        damper = source["source"]["damper_static_force_hold"]
        self.assertEqual(damper["authorization_id"], "AUTH-SUSP-0015")
        self.assertFalse(damper["zero_assumption_authorized"])
        self.assertFalse(source["included_force_set"]["complete_hardware_reaction"])

    def test_no_hidden_repair_or_shortcuts_are_authorized(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0016.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "complete rocker equilibrium",
            "assuming the missing kw v5",
            "unreported balancing term",
            "scalar motion ratios",
            "moving an input",
            "bearing split",
        ):
            self.assertIn(phrase, prohibited)
        numerics = auth["numerics"]
        self.assertFalse(numerics["hidden_clipping_allowed"])
        self.assertFalse(numerics["absolute_value_sign_repair_allowed"])
        self.assertFalse(numerics["hidden_balancing_allowed"])
        self.assertFalse(numerics["least_squares_repair_allowed"])

    def test_registry_links_and_benchmarks_are_consistent(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0008.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0016")
        self.assertEqual(model["equation_ids"], ["EQ-SUSP-0029", "EQ-SUSP-0030", "EQ-SUSP-0031"])
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0026", "BENCH-SUSP-0027", "BENCH-SUSP-0028"])
        self.assertEqual(model["assumption_ids"], ["ASM-SUSP-0008"])
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-SUSP-0008", benchmark["target_ids"])


if __name__ == "__main__":
    unittest.main()
