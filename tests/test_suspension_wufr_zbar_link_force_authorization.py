from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrZBarLinkForceAuthorizationTests(unittest.TestCase):
    def test_auth_susp_0013_is_narrow_physical_link_force_authority(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0013.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0013")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["physical_linkage_force_authorized"])
        self.assertFalse(scope["rocker_equilibrium_authorized"])
        self.assertFalse(scope["rocker_pivot_reaction_authorized"])
        self.assertFalse(scope["spring_arb_structural_composition_authorized"])
        self.assertFalse(scope["wheel_or_tire_load_transfer_authorized"])
        self.assertFalse(scope["structural_release_authorized"])

    def test_source_record_freezes_physical_rod_ended_linkages(self) -> None:
        source = _load("data_catalog/wufr27_arb_physical_link_force_v0.toml")
        front = "\n".join(source["source"]["front_arb_assembly"]["observations"]).lower()
        rear = "\n".join(source["source"]["rear_arb_assembly"]["observations"]).lower()
        self.assertIn("two", front)
        self.assertIn("rod-end", front)
        self.assertIn("two", rear)
        self.assertIn("rod ends", rear)
        self.assertFalse(source["boundaries"]["rocker_equilibrium_authorized"])

    def test_virtual_work_projection_and_sign_are_explicit(self) -> None:
        eq = _load("registry/records/equations/EQ-SUSP-0027.toml")["record"]
        equation = eq["canonical_equation"].lower()
        self.assertIn("t_i=f_i/(u_i dot n_i)", equation)
        self.assertIn("t_i>0 tension", equation)
        self.assertIn("f_ri=-t_i*u_i", equation)

        auth = _load("authorizations/suspension/AUTH-SUSP-0013.toml")
        self.assertEqual(float(auth["numerics"]["projection_absolute_threshold"]), 1.0e-6)
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertFalse(auth["numerics"]["absolute_value_sign_repair_allowed"])
        self.assertFalse(auth["numerics"]["regularization_allowed"])

    def test_physical_force_has_existing_generalized_torque_oracle(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0013.toml")
        torque = auth["coordinates"]["rocker_torque_check"].lower()
        self.assertIn("cross", torque)
        self.assertIn("generalized_rocker_torque", torque)
        benchmark = _load("registry/records/benchmarks/BENCH-SUSP-0024.toml")["record"]
        text = "\n".join(benchmark["acceptance_criteria"]).lower()
        self.assertIn("front nonzero benchmark", text)
        self.assertIn("asymmetric rear benchmark", text)
        self.assertIn("degenerate_link_projection", text)

    def test_prohibited_shortcuts_and_downstream_boundary_are_frozen(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0013.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "physical linkage axial force",
            "q_rocker",
            "q_z",
            "motion ratio",
            "absolute values",
            "rocker pivot reaction",
        ):
            self.assertIn(phrase, prohibited)
        self.assertIn("physical spring force vector", auth["promotion_gates"]["items"][-1].lower())


if __name__ == "__main__":
    unittest.main()
