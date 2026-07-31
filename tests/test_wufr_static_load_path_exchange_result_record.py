from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest

from scripts.run_wufr_static_load_path_exchange_benchmarks import build_report, summary_toml
from pssd_suspension.wufr_static_load_path_exchange import ROOT, canonical_json_bytes


class WufrStaticLoadPathExchangeResultRecordTests(unittest.TestCase):
    def test_frozen_records_match_regeneration(self) -> None:
        json_path = ROOT / "benchmarks/suspension/wufr_static_load_path_exchange_result_v0.1.0.json"
        toml_path = ROOT / "benchmarks/suspension/wufr_static_load_path_exchange_result_v0.1.0.toml"
        if not json_path.exists() or not toml_path.exists():
            self.skipTest("Frozen MOD-SUSP-0011 records have not yet been committed")
        generated = build_report()
        frozen = json.loads(json_path.read_text())
        self.assertEqual(generated, frozen)
        self.assertEqual(canonical_json_bytes(generated), json_path.read_bytes())
        self.assertEqual(summary_toml(generated), toml_path.read_text())
        with toml_path.open("rb") as stream:
            summary = tomllib.load(stream)
        self.assertEqual(summary["model_id"], "MOD-SUSP-0011")
        self.assertEqual(summary["authorization_id"], "AUTH-SUSP-0019")
        self.assertTrue(summary["bench_susp_0035_pass"])
        self.assertTrue(summary["bench_susp_0036_pass"])
        self.assertTrue(summary["bench_susp_0037_pass"])
        self.assertFalse(summary["fea_boundary_condition_authority"])
        self.assertFalse(summary["structural_release_authority"])


if __name__ == "__main__":
    unittest.main()
