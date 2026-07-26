from __future__ import annotations
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(path: str) -> dict:
    with (ROOT / path).open("rb") as stream:
        return tomllib.load(stream)

class WufrArbArmAuthorizationTests(unittest.TestCase):
    def test_authorization_and_source_semantics(self) -> None:
        auth = load("authorizations/suspension/AUTH-SUSP-0007.toml")
        source = load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0007")
        self.assertEqual(auth["status"], "review_ready")
        self.assertFalse(auth["scope"]["implementation_authorized"])
        self.assertEqual(auth["source_interpretation"]["arm_count"], 2)
        self.assertIn("blade arm", auth["source_interpretation"]["source_semantics"].lower())
        self.assertIn("3ei/l^3", auth["source_interpretation"]["source_semantics"].lower())
        self.assertEqual(source["governing_solidworks_fea"]["arm_count"], 2)
        self.assertTrue(source["authority_boundaries"]["two_arm_vector_constitutive_authorized"])
        self.assertFalse(source["authority_boundaries"]["scalar_whole_blade_rescaling_authorized"])

    def test_two_arm_energy_hand_cases(self) -> None:
        for k, expected_single, expected_pair in [
            (280000.0, 0.140, 0.280),
            (2300000.0, 1.150, 2.300),
        ]:
            d = 0.001
            self.assertAlmostEqual(0.5*k*d*d, expected_single, places=12)
            self.assertAlmostEqual(0.5*k*(d*d+d*d), expected_pair, places=12)

    def test_effective_axle_lineage_is_downstream(self) -> None:
        source = load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        lineage = source["historical_effective_axle_lineage"]
        self.assertEqual(lineage["front_roll_stiffness_Nm_per_deg"][0], 2560.0)
        self.assertEqual(lineage["rear_roll_stiffness_Nm_per_deg"][0], 2270.0)
        self.assertIn("downstream", lineage["role"].lower())
        self.assertIn("not an independent", source["comparison_only"]["matlab_semantics"].lower())

if __name__ == "__main__":
    unittest.main()
