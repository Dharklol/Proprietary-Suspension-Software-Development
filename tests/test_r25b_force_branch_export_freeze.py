from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


class R25bForceBranchExportFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        with (root / "benchmarks/tires/WUFR26_H43105_R25B_CORNERING_TROJAN_EXPORT_PROFILE_V0.toml").open("rb") as stream:
            cls.profile = tomllib.load(stream)
        with (root / "benchmarks/steering/r25b_force_branch_export_result_v0.1.0.toml").open("rb") as stream:
            cls.result = tomllib.load(stream)

    def test_source_and_intended_tire_identities_remain_distinct(self) -> None:
        self.assertEqual(self.profile["source_tire_id"], "HOOSIER_43105_18X7.5-10_R25B")
        self.assertEqual(self.profile["intended_tire_id"], "HOOSIER_43104_18X7.5-10_R20")
        self.assertNotEqual(self.profile["source_tire_id"], self.profile["intended_tire_id"])

    def test_real_source_hashes_are_frozen(self) -> None:
        source = self.result["source_profile"]
        self.assertEqual(source["cornering_trojan_sha1"], "475338b18b6cba21b967c7e75bdd12d9a0e3437a")
        self.assertEqual(source["raw_cornering_run_21_sha1"], "fca6c5b5116ae7fb16e2036b757ff294e0f790f6")
        self.assertEqual(source["raw_cornering_run_22_sha1"], "a995a2a89290dc32c5372b22e7bb5f469b6cf949")
        self.assertEqual(source["april_interpolator_sha1"], "e73eb559b1e0be42cc9c135d86be69e168d9e606")
        self.assertEqual(source["parser_april_sha1"], "32608eef763acacb7b233b82b8690bd3250752cc")
        self.assertEqual(source["fitted_tir_sha1"], "27b100c306ec4f207c9c42506edeeb23c95d4247")

    def test_synthetic_export_is_not_promoted_to_physical_tire_data(self) -> None:
        synthetic = self.result["synthetic_export"]
        self.assertFalse(synthetic["physical_tire_claim"])
        self.assertEqual(synthetic["inside_prepeak_rows"], 4)
        self.assertEqual(synthetic["outside_prepeak_rows"], 4)
        self.assertEqual(synthetic["roundtrip_branch_count"], 2)

    def test_failure_paths_and_track_scale_are_frozen(self) -> None:
        failures = self.result["failure_paths"]
        self.assertTrue(failures["missing_exact_operating_point_rejected"])
        self.assertTrue(failures["nonmonotonic_prepeak_source_rejected"])
        self.assertFalse(failures["hidden_operating_point_interpolation"])
        self.assertFalse(failures["hidden_source_refit"])
        self.assertFalse(failures["historical_two_thirds_track_scale_applied"])

    def test_real_branch_table_remains_explicitly_pending(self) -> None:
        status = self.result["real_source_status"]
        self.assertFalse(status["binary_source_committed_to_repository"])
        self.assertFalse(status["real_branch_table_frozen"])


if __name__ == "__main__":
    unittest.main()
