from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrUnsprungGravityReductionAuthorizationTests(unittest.TestCase):
    def test_correction_supersedes_only_the_incomplete_body_equation(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0010.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0010")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        self.assertEqual(auth["scope"]["prior_authorization"], "AUTH-VEH-0009")
        self.assertEqual(auth["scope"]["supersedes_equilibrium_equation"], "EQ-VEH-0016")
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-VEH-0015", "EQ-VEH-0017", "EQ-VEH-0018", "EQ-VEH-0019"],
        )
        self.assertIn("Retains EQ-VEH-0015", auth["effective_condition"])
        self.assertIn("EQ-VEH-0017", auth["effective_condition"])

    def test_failed_old_residual_probe_is_retained_without_weakening_closure(self) -> None:
        finding = _load("authorizations/vehicle/AUTH-VEH-0010.toml")["finding"]
        self.assertEqual(finding["probe_pr"], 82)
        self.assertLess(max(abs(v) for v in finding["old_reduced_residual_N_Nm"]), 5.0e-5)
        self.assertGreater(abs(finding["physical_resultant_force_N"][2]), 1.0)
        self.assertGreater(abs(finding["physical_resultant_moment_Nm"][1]), 0.5)
        self.assertEqual(finding["required_force_tolerance_N"], 1.0e-6)
        self.assertEqual(finding["required_moment_tolerance_Nm"], 1.0e-6)
        self.assertIn("omitted", finding["source_observation"].lower())

    def test_chain_rule_and_potential_oracle_are_explicit(self) -> None:
        mechanics = _load("authorizations/vehicle/AUTH-VEH-0010.toml")["mechanics"]
        self.assertIn("J_r", mechanics["direct_body_unsprung_gravity"])
        self.assertIn("J_wb^T Q_u,z", mechanics["compatible_reduced_unsprung_gravity"])
        self.assertIn("Q_u,red", mechanics["corrected_body_residual"])
        self.assertIn("-d/dq_b", mechanics["independent_potential_check"])
        self.assertIn("Q_u,z,i", mechanics["contact_recovery"])

        eq18 = _load("registry/records/equations/EQ-VEH-0018.toml")["record"]
        self.assertEqual(eq18["authorization_id"], "AUTH-VEH-0010")
        self.assertIn("Q_u,b,direct", eq18["canonical_equation"])
        self.assertIn("J_wb^T Q_u,z", eq18["canonical_equation"])

        eq19 = _load("registry/records/equations/EQ-VEH-0019.toml")["record"]
        self.assertEqual(eq19["supersedes_equation_id"], "EQ-VEH-0016")
        self.assertIn("Q_u,red", eq19["canonical_equation"])
        self.assertIn("MOD-VEH-0004", "\n".join(eq19["inputs"]))

    def test_corrected_source_record_preserves_upstream_ownership(self) -> None:
        source = _load("data_catalog/wufr27_static_equilibrium_composition_v1.toml")
        self.assertEqual(source["record_id"], "WUFR27_STATIC_EQUILIBRIUM_COMPOSITION_V1")
        self.assertEqual(source["authorization_id"], "AUTH-VEH-0010")
        self.assertEqual(source["correction"]["prior_record_id"], "WUFR27_STATIC_EQUILIBRIUM_COMPOSITION_V0")
        self.assertFalse(source["correction"]["old_equation_fallback_authorized"])
        self.assertIn("Q_unsprung_body_direct", source["source"]["equilibrium"]["body_rule"])
        self.assertIn("J_wb^T", source["source"]["equilibrium"]["body_rule"])
        self.assertEqual(source["source"]["gravity"]["model_id"], "MOD-VEH-0005")
        self.assertEqual(source["source"]["compatibility"]["model_id"], "MOD-VEH-0006")
        self.assertEqual(source["source"]["equilibrium"]["model_id"], "MOD-VEH-0004")

    def test_model_and_benchmark_registry_links_use_the_correction(self) -> None:
        model = _load("registry/records/models/MOD-VEH-0007.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0010")
        self.assertEqual(
            model["equation_ids"],
            ["EQ-VEH-0015", "EQ-VEH-0017", "EQ-VEH-0018", "EQ-VEH-0019"],
        )
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-VEH-0011", "BENCH-VEH-0012", "BENCH-VEH-0013", "BENCH-VEH-0014"],
        )
        self.assertEqual(model["source_snapshot"], "data_catalog/wufr27_static_equilibrium_composition_v1.toml")
        for benchmark_id in model["benchmark_ids"]:
            record = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(record["authorization"], "authorizations/vehicle/AUTH-VEH-0010.toml")
            self.assertIn("MOD-VEH-0007", record["target_ids"])

    def test_no_scalar_repair_or_authority_promotion_is_reachable(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0010.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "road-fixed",
            "dropping the direct body term",
            "scalar unsprung-weight correction",
            "balancing wrench",
            "weakening the 1e-6",
            "installed/as-built",
            "carrier wrenches",
            "structural load cases",
        ):
            self.assertIn(phrase, prohibited)
        boundaries = _load("data_catalog/wufr27_static_equilibrium_composition_v1.toml")["boundaries"]
        self.assertFalse(boundaries["installed_as_built_authority"])
        self.assertFalse(boundaries["physical_correlation_authority"])
        self.assertFalse(boundaries["carrier_wrench_authority"])
        self.assertFalse(boundaries["structural_load_case_authority"])
        self.assertFalse(boundaries["maneuver_qss_authority"])


if __name__ == "__main__":
    unittest.main()
