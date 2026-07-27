from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WufrLinkageTopologyAuditTests(unittest.TestCase):
    def test_auth_susp_0011_is_a_wufr_adapter_hold_not_a_generic_kernel_revoke(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0011.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0011")
        self.assertEqual(auth["status"], "review_ready")
        self.assertFalse(auth["implementation_authorized"])
        self.assertTrue(auth["scope"]["generic_linkage_kernel_remains_authorized"])
        self.assertFalse(auth["scope"]["wufr_corner_adapter_authorized"])
        self.assertFalse(auth["scope"]["wufr_multi_body_graph_authorized"])
        self.assertFalse(auth["scope"]["wufr_member_force_output_authorized"])
        self.assertFalse(auth["scope"]["wufr_load_case_generation_authorized"])

    def test_source_record_preserves_arm_mounted_actuation_and_wufr27_gap(self) -> None:
        audit = _load("data_catalog/wufr26_linkage_topology_source_audit_v0.toml")
        confirmed = "\n".join(audit["confirmed_topology"]["items"]).lower()
        unresolved = "\n".join(audit["unresolved_topology"]["items"]).lower()
        self.assertIn("front actuation load enters the upper a-arm", confirmed)
        self.assertIn("rear actuation load enters the lower a-arm", confirmed)
        self.assertFalse(audit["authority_boundaries"]["wufr27_topology_authority"])
        self.assertFalse(audit["authority_boundaries"]["wufr_member_force_authority"])
        self.assertIn("wufr27", unresolved)
        self.assertFalse(audit["candidate_architecture_not_authorized"]["implementation_authorized"])

    def test_legacy_negative_force_clipping_is_rejected(self) -> None:
        audit = _load("data_catalog/wufr26_linkage_topology_source_audit_v0.toml")
        legacy = audit["source"]["legacy_load_matrix"]
        self.assertFalse(legacy["governing_authority"])
        reasons = "\n".join(legacy["rejection_reasons"]).lower()
        self.assertIn("negative values as 0 n", reasons)

        auth = _load("authorizations/suspension/AUTH-SUSP-0011.toml")
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("negative-to-zero", prohibited)
        self.assertFalse(auth["finding"]["legacy_negative_force_clipping_allowed"])

    def test_candidate_architecture_keeps_structural_output_boundary_explicit(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0011.toml")
        candidate = auth["candidate_architecture"]
        self.assertEqual(candidate["status"], "not_authorized")
        self.assertIn("revolute", candidate["a_arm_support_candidate"].lower())
        self.assertIn("forward/aft", candidate["limitation"].lower())

        audit_doc = (ROOT / "docs/models/suspension/wufr_linkage_topology_source_audit.md").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("equivalent revolute", audit_doc)
        self.assertIn("net hinge reaction", audit_doc)
        self.assertIn("beam/fe", audit_doc)

    def test_mod_susp_0006_remains_provider_neutral(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0006.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0010")
        self.assertIn("provider-neutral", model["title"].lower())
        self.assertIn("no_wufr", model["authorization_state"].lower())
        self.assertIn("topology", model["next_implementation_gate"].lower())


if __name__ == "__main__":
    unittest.main()
