from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MACRO = ROOT / "tools" / "solidworks" / "WUFR26_SolidWorks_Metadata_Exporter.bas"
DOC = ROOT / "docs" / "tools" / "solidworks_metadata_exporter.md"
SCHEMA = ROOT / "schemas" / "solidworks_metadata_report.schema.json"


class SolidWorksMetadataExporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = MACRO.read_text(encoding="utf-8")
        cls.source_lower = cls.source.lower()

    def test_exporter_and_schema_are_versioned(self) -> None:
        self.assertTrue(self.source.startswith('Attribute VB_Name = "WUFR26_Metadata_Exporter"'))
        self.assertIn('Private Const EXTRACTOR_VERSION As String = "1.0.0"', self.source)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual("urn:pssd:solidworks-metadata-report:1.0.0", schema["$id"])
        self.assertEqual("1.0.0", schema["properties"]["schema_version"]["const"])

    def test_public_entrypoint_and_required_read_apis_are_present(self) -> None:
        self.assertIn("Public Sub main()", self.source)
        for api_name in (
            "RevisionNumber",
            "GetBuildNumbers2",
            "GetConfigurationNames",
            "GetEquationMgr",
            "GetWhatsWrongCount",
            "GetWhatsWrong",
            "GetDependencies",
            "ListExternalFileReferencesCount",
            "ListExternalFileReferences2",
            "GetMotionStudyManager",
            "GetMotionStudyNames",
            "GetMotionStudy",
            "GetMotionFeatures",
            "GetFirstDisplayDimension",
            "GetNextDisplayDimension",
            "GetErrorCode2",
            "GetSaveFlag",
        ):
            with self.subTest(api_name=api_name):
                self.assertIn(api_name, self.source)

    def test_no_model_mutation_calls_are_present(self) -> None:
        forbidden_patterns = {
            "save": r"\.\s*(?:save|save2|save3|saveas|saveas2|saveas3)\b",
            "rebuild": r"\.\s*(?:editrebuild3|forcerebuild3|rebuild)\b",
            "configuration_activation": r"\.\s*(?:showconfiguration2|activateconfiguration)\b",
            "motion_activation": r"\.\s*activatemotionstudy\b",
            "motion_calculation": r"\.\s*calculate\b",
            "component_resolution": r"\.\s*(?:setlightweight|resolvealllightweightcomponents)\b",
        }
        for label, pattern in forbidden_patterns.items():
            with self.subTest(label=label):
                self.assertIsNone(re.search(pattern, self.source_lower))

    def test_vba_structure_and_line_continuations_are_bounded(self) -> None:
        sub_starts = len(re.findall(r"(?im)^\s*(?:public |private )?sub\b", self.source))
        sub_ends = len(re.findall(r"(?im)^\s*end sub\s*$", self.source))
        function_starts = len(re.findall(r"(?im)^\s*(?:public |private )?function\b", self.source))
        function_ends = len(re.findall(r"(?im)^\s*end function\s*$", self.source))
        self.assertEqual(sub_starts, sub_ends)
        self.assertEqual(function_starts, function_ends)

        continuation_run = 0
        maximum_run = 0
        for line in self.source.splitlines():
            if line.rstrip().endswith(" _"):
                continuation_run += 1
                maximum_run = max(maximum_run, continuation_run)
            else:
                continuation_run = 0
        self.assertLessEqual(maximum_run, 24)
        self.assertLess(max(len(line) for line in self.source.splitlines()), 1023)

    def test_output_is_utf8_json_and_records_dirty_state(self) -> None:
        self.assertIn('CreateObject("ADODB.Stream")', self.source)
        self.assertIn('streamObj.Charset = "utf-8"', self.source)
        self.assertIn('Q("dirty_before")', self.source)
        self.assertIn('Q("dirty_after")', self.source)
        self.assertIn('Q("warnings")', self.source)
        self.assertIn('Q("target_name_matches")', self.source)

    def test_documentation_preserves_source_authority_boundary(self) -> None:
        documentation = DOC.read_text(encoding="utf-8")
        self.assertIn("does not replace the untouched native SOLIDWORKS file", documentation)
        self.assertIn("raw-byte SHA-256", documentation)
        self.assertIn("Pack and Go", documentation)
        self.assertIn("Find References > Copy List", documentation)
        self.assertIn("Lightweight", documentation)


if __name__ == "__main__":
    unittest.main()
