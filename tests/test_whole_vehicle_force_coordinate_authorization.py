from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WholeVehicleForceCoordinateAuthorizationTests(unittest.TestCase):
    def test_authorization_is_bounded_and_review_ready(self) -> None:
        auth = _load("authorizations/vehicle/AUTH-VEH-0003.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-VEH-0003")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-VEH-0003"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-VEH-0004", "EQ-VEH-0005", "EQ-VEH-0006", "EQ-VEH-0007"],
        )
        self.assertEqual(
            auth["scope"]["benchmark_ids"],
            ["BENCH-VEH-0003", "BENCH-VEH-0004"],
        )
        self.assertEqual(
            auth["scope"]["assumption_ids"],
            ["ASM-VEH-0001", "ASM-VEH-0002", "ASM-SUSP-0001"],
        )
        numerics = auth["numerics"]
        self.assertFalse(numerics["hidden_clipping_allowed"])
        self.assertFalse(numerics["silent_origin_inference_allowed"])
        self.assertFalse(numerics["negative_contact_reaction_allowed"])
        self.assertFalse(numerics["constitutive_force_evaluation_allowed"])
        self.assertFalse(numerics["equilibrium_solve_allowed"])
        self.assertFalse(numerics["linkage_force_solve_allowed"])

    def test_model_equation_benchmark_and_assumption_links_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-VEH-0003.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0003")
        self.assertEqual(
            model["equation_ids"],
            ["EQ-VEH-0004", "EQ-VEH-0005", "EQ-VEH-0006", "EQ-VEH-0007"],
        )
        self.assertEqual(model["benchmark_ids"], ["BENCH-VEH-0003", "BENCH-VEH-0004"])
        self.assertEqual(
            model["assumption_ids"],
            ["ASM-VEH-0001", "ASM-VEH-0002", "ASM-SUSP-0001"],
        )
        self.assertEqual(
            model["upstream_model_ids"],
            ["MOD-SUSP-0001", "MOD-SUSP-0002", "MOD-SUSP-0003"],
        )

        for equation_id in model["equation_ids"]:
            record = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(record["id"], equation_id)
            self.assertEqual(record["verification_level"], "none")
            self.assertTrue(set(record["benchmark_ids"]).issubset(set(model["benchmark_ids"])))

        for benchmark_id in model["benchmark_ids"]:
            record = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(record["id"], benchmark_id)
            self.assertIn("MOD-VEH-0003", record["target_ids"])

        for assumption_id in model["assumption_ids"]:
            family = "vehicle" if assumption_id.startswith("ASM-VEH") else "suspension"
            record = _load(f"registry/records/assumptions/{assumption_id}.toml")["record"]
            self.assertEqual(record["id"], assumption_id)
            self.assertIn("MOD-VEH-0003", record["affected_ids"])
            self.assertIn(family, {"vehicle", "suspension"})

    def test_canonical_mechanics_and_contact_signs_are_explicit(self) -> None:
        transport = _load("registry/records/equations/EQ-VEH-0004.toml")["record"]
        wrench = _load("registry/records/equations/EQ-VEH-0005.toml")["record"]
        virtual_work = _load("registry/records/equations/EQ-VEH-0006.toml")["record"]
        contact = _load("registry/records/equations/EQ-VEH-0007.toml")["record"]

        self.assertIn("R_z(psi) R_y(theta) R_x(phi)", transport["canonical_equation"])
        self.assertIn("(r_P-r_O) cross F", wrench["canonical_equation"])
        self.assertIn("Q = J_r^T F + J_omega^T M", virtual_work["canonical_equation"])
        self.assertIn("lambda_i", contact["canonical_equation"])
        self.assertIn(">= 0", contact["canonical_equation"])

        failures = "\n".join(contact["failure_behavior"])
        self.assertIn("wheel_lift", failures)
        self.assertIn("do not clip", failures)

    def test_wufr_inheritance_does_not_create_whole_vehicle_origin_authority(self) -> None:
        inherited = _load("registry/records/assumptions/ASM-VEH-0001.toml")["record"]
        contact = _load("registry/records/assumptions/ASM-VEH-0002.toml")["record"]
        linkage = _load("registry/records/assumptions/ASM-SUSP-0001.toml")["record"]
        auth = _load("authorizations/vehicle/AUTH-VEH-0003.toml")

        self.assertIn("same reviewed suspension geometry", inherited["description"])
        self.assertIn("does not establish a common whole-vehicle origin", inherited["description"])
        self.assertIn("negative reaction", contact["description"])
        self.assertIn("never clipped", contact["description"])
        self.assertIn("does not authorize linkage-force computation", linkage["description"])
        self.assertIn("wheelbase alone is insufficient", auth["source_boundary"]["missing_wufr_authority"])

    def test_authorization_matrix_contains_active_gate(self) -> None:
        text = (ROOT / "docs/governance/implementation_authorization_matrix.md").read_text(encoding="utf-8")
        self.assertIn("`MOD-VEH-0003`", text)
        self.assertIn("`EQ-VEH-0004` through `0007`", text)
        self.assertIn("`AUTH-VEH-0003`", text)
        self.assertIn("negative normal reaction", text)
        self.assertIn("two-force", text)


if __name__ == "__main__":
    unittest.main()
