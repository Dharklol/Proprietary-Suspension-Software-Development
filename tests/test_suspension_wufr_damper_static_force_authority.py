from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrDamperStaticForceAuthorityTests(unittest.TestCase):
    def test_auth_susp_0015_is_a_fail_closed_source_hold(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0015.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0015")
        self.assertEqual(auth["status"], "review_ready")
        self.assertFalse(auth["implementation_authorized"])
        scope = auth["scope"]
        self.assertTrue(scope["damper_hardware_identity_frozen"])
        self.assertTrue(scope["generic_static_force_mechanics_frozen"])
        self.assertFalse(scope["wufr_damper_gas_force_model_authorized"])
        self.assertFalse(scope["wufr_damper_static_friction_model_authorized"])
        self.assertFalse(scope["complete_rocker_pivot_reaction_authorized"])
        self.assertTrue(scope["partial_included_load_contribution_may_be_authorized_separately"])

    def test_exact_purchased_kw_v5_identity_is_frozen(self) -> None:
        source = _load("data_catalog/wufr27_damper_static_force_authority_v0.toml")
        invoice = source["source"]["purchase_invoice"]
        self.assertEqual(invoice["quantity"], 4)
        self.assertEqual(invoice["item_number"], "3980599103")
        self.assertEqual(invoice["description"], "V5 FSAE DAMPER-PIGGY BACK")
        correspondence = "\n".join(source["source"]["kw_correspondence"]["observations"]).lower()
        self.assertIn("four-way adjustable solid-piston", correspondence)

    def test_generic_static_mechanics_do_not_become_kw_numbers(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0015.toml")
        mechanics = auth["generic_mechanics"]
        relations = "\n".join(mechanics["creep_loop_relations"]).lower()
        self.assertIn("f_g = 0.5*(f_in + f_out)", relations)
        self.assertIn("f_f = 0.5*(f_in - f_out)", relations)
        self.assertIn("generic mechanics only", mechanics["analytic_relation_boundary"].lower())
        finding = auth["finding"]
        self.assertFalse(finding["source_specific_static_force_available"])
        self.assertFalse(finding["zero_force_assumption_supported"])

    def test_missing_authority_and_prohibited_shortcuts_are_explicit(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0015.toml")
        missing = "\n".join(auth["missing_authority"]["items"]).lower()
        for phrase in (
            "effective rod/displacement area",
            "nitrogen charge pressure",
            "gas volume",
            "both directions",
            "friction",
        ):
            self.assertIn(phrase, missing)

        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "setting damper gas force",
            "generic motorsport nitrogen pressure",
            "complete rocker equilibrium",
            "hidden balancing torque",
        ):
            self.assertIn(phrase, prohibited)

    def test_complete_reaction_is_blocked_but_included_load_diagnostic_is_permitted(self) -> None:
        source = _load("data_catalog/wufr27_damper_static_force_authority_v0.toml")
        boundaries = source["boundaries"]
        self.assertFalse(boundaries["complete_rocker_equilibrium_authorized"])
        self.assertFalse(boundaries["complete_rocker_pivot_reaction_authorized"])
        self.assertFalse(boundaries["zero_force_assumption_authorized"])
        self.assertTrue(boundaries["partial_included_load_contribution_may_be_authorized_separately"])

        permitted = "\n".join(
            _load("authorizations/suspension/AUTH-SUSP-0015.toml")["permitted"]["items"]
        ).lower()
        self.assertIn("included-load contribution", permitted)
        self.assertIn("marked incomplete", permitted)


if __name__ == "__main__":
    unittest.main()
