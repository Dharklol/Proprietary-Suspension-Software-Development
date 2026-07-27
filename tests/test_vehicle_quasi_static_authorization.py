from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class VehicleQuasiStaticAuthorizationTests(unittest.TestCase):
    def test_authorization_is_generic_and_review_ready(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0004.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0004")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-VEH-0004"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-VEH-0008", "EQ-VEH-0009", "EQ-VEH-0010"],
        )
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-VEH-0005", "BENCH-VEH-0006"])
        self.assertEqual(
            auth["scope"]["upstream_model_ids"],
            ["MOD-VEH-0003", "MOD-SUSP-0004", "MOD-SUSP-0005"],
        )
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertFalse(auth["numerics"]["negative_contact_reaction_allowed"])
        self.assertFalse(auth["numerics"]["hidden_mass_default_allowed"])
        self.assertFalse(auth["numerics"]["hidden_crossweight_rule_allowed"])
        self.assertFalse(auth["numerics"]["wufr_mass_adapter_allowed"])

    def test_registry_links_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-VEH-0004.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0004")
        self.assertEqual(
            model["equation_ids"],
            ["EQ-VEH-0008", "EQ-VEH-0009", "EQ-VEH-0010"],
        )
        self.assertEqual(model["benchmark_ids"], ["BENCH-VEH-0005", "BENCH-VEH-0006"])
        self.assertEqual(
            model["upstream_model_ids"],
            ["MOD-VEH-0003", "MOD-SUSP-0004", "MOD-SUSP-0005"],
        )
        for equation_id in model["equation_ids"]:
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(equation["id"], equation_id)
            self.assertEqual(equation["verification_level"], "none")
            self.assertEqual(set(equation["benchmark_ids"]), {"BENCH-VEH-0005", "BENCH-VEH-0006"})
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(benchmark["id"], benchmark_id)
            self.assertIn("MOD-VEH-0004", benchmark["target_ids"])

    def test_reduced_and_contact_equations_keep_force_roles_separate(self) -> None:
        body = _load("registry/records/equations/EQ-VEH-0009.toml")["record"]
        contact = _load("registry/records/equations/EQ-VEH-0010.toml")["record"]
        self.assertIn("J_wb(q_b)^T Q_susp_w", body["canonical_equation"])
        self.assertIn("wheel-only external forces", "\n".join(body["assumptions"]).lower())
        self.assertIn("Q_wheel_ext_i", contact["canonical_equation"])
        self.assertIn("lambda_i >= 0", contact["canonical_equation"])

    def test_symmetric_benchmark_hand_case_is_self_consistent(self) -> None:
        sprung_mass_kg = 100.0
        wheel_mass_kg = 5.0
        g = 9.81
        k = 10000.0
        z_s = -(sprung_mass_kg * g) / (4.0 * k)
        z_w = -z_s
        q_susp = -k * z_w
        q_wheel_ext = -wheel_mass_kg * g
        reaction = -(q_susp + q_wheel_ext)
        self.assertAlmostEqual(z_s, -0.024525, places=12)
        self.assertAlmostEqual(z_w, 0.024525, places=12)
        self.assertAlmostEqual(q_susp, -245.25, places=12)
        self.assertAlmostEqual(reaction, 294.30, places=12)
        self.assertAlmostEqual(4.0 * reaction, (sprung_mass_kg + 4.0 * wheel_mass_kg) * g, places=12)

    def test_wufr_mass_defaults_are_explicitly_prohibited(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0004.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("5 kg per corner", prohibited)
        self.assertIn("10 kg per-corner", prohibited)
        self.assertIn("207 kg", prohibited)
        self.assertIn("220+100 kg", prohibited)
        self.assertIn("crossweight", prohibited)
        self.assertIn("scalar arb", prohibited)

        audit = (ROOT / "docs/models/vehicle/quasi_static_load_state_source_audit.md").read_text(encoding="utf-8")
        self.assertIn("10 kg front axle + 10 kg rear axle", audit)
        self.assertIn("does **not** yet support a WUFR-specific four-corner road-reaction result", audit)


if __name__ == "__main__":
    unittest.main()
