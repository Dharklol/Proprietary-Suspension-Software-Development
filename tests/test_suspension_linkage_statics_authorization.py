from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class SuspensionLinkageStaticsAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0010_is_provider_neutral_and_determinate_only(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0010.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0010")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        self.assertTrue(auth["scope"]["provider_neutral_only"])
        self.assertFalse(auth["scope"]["wufr_corner_adapter_authorized"])
        self.assertFalse(auth["scope"]["wufr_load_case_generation_authorized"])
        self.assertFalse(auth["scope"]["structural_release_authorized"])
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0006"])
        self.assertEqual(auth["scope"]["assumption_ids"], ["ASM-SUSP-0004"])
        self.assertEqual(len(auth["scope"]["equation_ids"]), 4)
        self.assertEqual(len(auth["scope"]["benchmark_ids"]), 3)

    def test_positive_tension_and_exact_wrench_equilibrium_are_frozen(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0010.toml")
        self.assertIn("n_j>0 is tension", auth["coordinates"]["axial_force_sign"].lower())
        self.assertEqual(
            auth["coordinates"]["wrench_row_order"],
            ["Fx_N", "Fy_N", "Fz_N", "Mx_Nm", "My_Nm", "Mz_Nm"],
        )

        eq20 = _load("registry/records/equations/EQ-SUSP-0020.toml")["record"]
        self.assertIn("a*n=b", eq20["canonical_equation"].lower())
        self.assertIn("cross", eq20["canonical_equation"].lower())

        eq22 = _load("registry/records/equations/EQ-SUSP-0022.toml")["record"]
        self.assertIn("r_f", eq22["canonical_equation"].lower())
        self.assertIn("r_m", eq22["canonical_equation"].lower())

    def test_scaling_conditioning_and_no_approximate_force_sharing_are_explicit(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0010.toml")
        numerics = auth["numerics"]
        self.assertAlmostEqual(float(numerics["condition_limit"]), 1.0e10)
        self.assertFalse(numerics["hidden_clipping_allowed"])
        self.assertFalse(numerics["least_squares_allowed"])
        self.assertFalse(numerics["pseudoinverse_allowed"])
        self.assertFalse(numerics["regularization_allowed"])
        self.assertFalse(numerics["force_magnitude_only_output_allowed"])
        self.assertIn("1/l_ref", numerics["scaled_system_rule"].lower())

        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "least squares",
            "pseudoinverse",
            "minimum-norm",
            "stiffness weighting",
            "moving an arm-mounted",
            "beam bending",
            "factor of safety",
        ):
            self.assertIn(phrase, prohibited)

    def test_analytical_benchmark_freezes_known_signed_solution(self) -> None:
        bench = _load("registry/records/benchmarks/BENCH-SUSP-0018.toml")["record"]
        text = "\n".join(bench["acceptance_criteria"])
        self.assertIn("N=[100,200,300,40,50,60] N", text)
        self.assertIn("F_ext=[-150,-260,-340] N", text)
        self.assertIn("M_ext=[-40,-50,-60] N*m", text)
        self.assertIn("positive-tension", text)

        bench19 = _load("registry/records/benchmarks/BENCH-SUSP-0019.toml")["record"]
        self.assertIn("reference-point", bench19["title"].lower())
        self.assertIn("translation", bench19["title"].lower())

        bench20 = _load("registry/records/benchmarks/BENCH-SUSP-0020.toml")["record"]
        failures = "\n".join(bench20["acceptance_criteria"]).lower()
        self.assertIn("five-link", failures)
        self.assertIn("seven-link", failures)
        self.assertIn("singular_equilibrium", failures)
        self.assertIn("ill_conditioned_equilibrium", failures)

    def test_wufr_arm_mounted_actuation_is_a_separate_topology_gate(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0010.toml")
        boundary = auth["source_boundary"]
        self.assertIn("upper a-arm", boundary["wufr_topology_gap"].lower())
        self.assertIn("lower a-arm", boundary["wufr_topology_gap"].lower())
        self.assertIn("not authorized", boundary["wufr_topology_gap"].lower())

        model = _load("registry/records/models/MOD-SUSP-0006.toml")["record"]
        self.assertEqual(model["status"], "proposed")
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0010")
        self.assertIn("topology source audit", "\n".join(model["planned_downstream"]).lower())

    def test_roadmap_stages_preserve_data_gated_vehicle_work(self) -> None:
        roadmap = (ROOT / "docs/roadmaps/post_rigid_contact_program_v0.1.0.md").read_text(encoding="utf-8")
        for heading in (
            "Program A — WUFR static-equilibrium closeout",
            "Program B — suspension linkage and load-path statics",
            "Program C — reusable steady-state tire model",
            "Program D — WUFR-27 physical correlation contract",
            "Program E — integrated maneuver QSS after correlation",
        ):
            self.assertIn(heading, roadmap)
        self.assertIn("front push/pull attachment is on the upper A-arm", roadmap)
        self.assertIn("rear attachment is on the lower A-arm", roadmap)


if __name__ == "__main__":
    unittest.main()
