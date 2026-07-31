from __future__ import annotations

from pathlib import Path
import tempfile
import tomllib
import unittest
import zipfile

from scripts.verify_r25b_generator_source import (
    EXPECTED_ROWS_PER_STATE_HISTOGRAM,
    EXPECTED_STATE_COUNT,
    EXPECTED_TOTAL_ROWS,
    expected_cornering_profile,
    extract_code_paragraphs,
)

ROOT = Path(__file__).resolve().parents[1]


class R25bGeneratorProvenanceTests(unittest.TestCase):
    def test_frozen_profile_exactly_explains_9630_rows(self) -> None:
        total_rows, state_count, histogram = expected_cornering_profile()
        self.assertEqual(total_rows, EXPECTED_TOTAL_ROWS)
        self.assertEqual(state_count, EXPECTED_STATE_COUNT)
        self.assertEqual(histogram, EXPECTED_ROWS_PER_STATE_HISTOGRAM)

    def test_live_script_code_extractor_is_structural_not_ocr(self) -> None:
        document = """<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>fz_targets = [222, 445, 667, 890, 1112];
p_targets = [96.5, 82.7, 68.9, 55.2];</w:t></w:r></w:p></w:body>
        </w:document>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.mlx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("matlab/document.xml", document)
            paragraphs = extract_code_paragraphs(path)
        self.assertEqual(len(paragraphs), 1)
        self.assertIn("fz_targets", paragraphs[0])
        self.assertIn("55.2", paragraphs[0])

    def test_catalog_freezes_exact_live_script_identity(self) -> None:
        with (ROOT / "data_catalog/r25b_ttc_spline_fitter_generator_v0.toml").open("rb") as stream:
            record = tomllib.load(stream)
        generator = record["generator"]
        self.assertEqual(generator["file_id"], "1890916633802")
        self.assertEqual(generator["file_version_id"], "2085677125802")
        self.assertEqual(generator["size_bytes"], 286864)
        self.assertEqual(generator["sha1"], "c78a66751be956b60ff0f879cd0f733638a71ce3")
        self.assertEqual(
            generator["sha256"],
            "a4e8a0d079d9ba64fbba428885d9c1c2c0699ca80c12f7d5a3c05b88988aa248",
        )
        profile = record["cornering_profile"]
        self.assertEqual(profile["state_count"], 60)
        self.assertEqual(profile["total_rows"], 9630)
        self.assertTrue(profile["exact_profile_explains_processed_binary"])
        self.assertTrue(record["raw_input_lineage"]["example_paths_are_not_r25b_provenance"])

    def test_independent_raw_reproduction_is_within_frozen_bounds(self) -> None:
        with (ROOT / "benchmarks/tires/r25b_raw_reproduction_result_v0.1.0.toml").open("rb") as stream:
            result = tomllib.load(stream)
        self.assertTrue(result["decision"]["profile_reproduced"])
        self.assertTrue(result["decision"]["generator_and_raw_input_lineage_reconciled"])
        self.assertFalse(result["decision"]["runtime_authorized"])
        self.assertEqual(result["structure"]["state_count"], 60)
        self.assertEqual(result["structure"]["reproduced_rows"], 9630)
        for channel in ("SA", "FX", "FY", "MX", "MZ"):
            errors = result["errors"][channel]
            measured_key = next(key for key in errors if key.startswith("max_abs"))
            acceptance_key = next(key for key in errors if key.startswith("acceptance"))
            self.assertLess(errors[measured_key], errors[acceptance_key], channel)


if __name__ == "__main__":
    unittest.main()
