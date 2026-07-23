from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from pssd_steering import load_geometry
from pssd_steering.optimization import (
    ExternalPoseAdapterError,
    evaluate_candidate_over_pose_set,
    generate_candidate_geometry,
    load_external_pose_table,
    load_historical_fit_target,
    load_pose_set,
    load_requirement_set,
    resolve_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "benchmarks" / "steering" / "STEERING_EXTERNAL_POSE_TABLE_FIXTURE_V0.toml"
REFERENCE_POSE_PATH = ROOT / "benchmarks" / "steering" / "STEERING_SYNTHETIC_POSE_SET_V0.toml"
BASELINE_PATH = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
REQUIREMENT_PATH = ROOT / "configurations" / "steering" / "STEERING_INVERSE_DESIGN_DEV_V0.toml"
TARGET_PATH = ROOT / "benchmarks" / "steering" / "WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml"
SOURCE_CSV_PATH = ROOT / "benchmarks" / "steering" / "STEERING_EXTERNAL_POSE_TABLE_FIXTURE_V0.csv"


class SteeringExternalPoseAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.imported = load_external_pose_table(MANIFEST_PATH)
        cls.reference = load_pose_set(REFERENCE_POSE_PATH)
        cls.baseline = load_geometry(BASELINE_PATH)
        cls.requirement = load_requirement_set(REQUIREMENT_PATH)
        cls.target = load_historical_fit_target(TARGET_PATH)
        cls.candidate = resolve_candidate(cls.requirement, candidate_id="EXTERNAL-POSE-REFERENCE")
        cls.generated = generate_candidate_geometry(cls.baseline, cls.requirement, cls.candidate)

    def _assert_manifest_rejected(self, manifest_text: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "bad.toml"
            manifest.write_text(manifest_text, encoding="utf-8")
            (root / SOURCE_CSV_PATH.name).write_text(
                SOURCE_CSV_PATH.read_text(encoding="utf-8"), encoding="utf-8"
            )
            with self.assertRaises(ExternalPoseAdapterError):
                load_external_pose_table(manifest)

    def test_exchange_fixture_reconstructs_canonical_pose_values(self) -> None:
        actual = self.imported.pose_set
        expected = self.reference
        self.assertEqual(expected.nominal_state_id, actual.nominal_state_id)
        self.assertEqual([item.state_id for item in expected.states], [item.state_id for item in actual.states])
        for expected_state, actual_state in zip(expected.states, actual.states):
            self.assertEqual(
                [(item.id, item.value, item.unit) for item in expected_state.coordinates],
                [(item.id, item.value, item.unit) for item in actual_state.coordinates],
            )
            self.assertEqual(expected_state.left_transform.rotation, actual_state.left_transform.rotation)
            self.assertEqual(expected_state.right_transform.rotation, actual_state.right_transform.rotation)
            self.assertEqual(expected_state.left_transform.translation_m, actual_state.left_transform.translation_m)
            self.assertEqual(expected_state.right_transform.translation_m, actual_state.right_transform.translation_m)

    def test_external_pose_table_preserves_multistate_analyzer_response(self) -> None:
        expected = evaluate_candidate_over_pose_set(
            self.baseline,
            self.requirement,
            self.candidate,
            self.target,
            self.reference,
        )
        actual = evaluate_candidate_over_pose_set(
            self.baseline,
            self.requirement,
            self.candidate,
            self.target,
            self.imported.pose_set,
        )
        self.assertEqual(expected.feasible, actual.feasible)
        self.assertEqual([item.state_id for item in expected.states], [item.state_id for item in actual.states])
        for expected_state, actual_state in zip(expected.states, actual.states):
            self.assertEqual(expected_state.feasible, actual_state.feasible)
            self.assertEqual(expected_state.left_total_heading_deg, actual_state.left_total_heading_deg)
            self.assertEqual(expected_state.right_total_heading_deg, actual_state.right_total_heading_deg)
            self.assertEqual(
                expected_state.center_left_side_local_toe_out_change_deg,
                actual_state.center_left_side_local_toe_out_change_deg,
            )
            self.assertEqual(
                expected_state.center_right_side_local_toe_out_change_deg,
                actual_state.center_right_side_local_toe_out_change_deg,
            )

    def test_manifest_provenance_is_required_and_retained(self) -> None:
        self.assertEqual("external_rigid_upright_pose_csv_v0.1.0", self.imported.adapter_id)
        self.assertTrue(self.imported.source_revision)
        self.assertTrue(self.imported.frame_id)
        self.assertIn("Software adapter verification", self.imported.authority)
        self.assertEqual(self.imported.authority, self.imported.pose_set.authority)

    def test_source_that_includes_tie_rod_steering_is_rejected(self) -> None:
        original = MANIFEST_PATH.read_text(encoding="utf-8")
        self._assert_manifest_rejected(
            original.replace(
                "tie_rod_steering_response_included = false",
                "tie_rod_steering_response_included = true",
            )
        )

    def test_missing_source_revision_is_rejected(self) -> None:
        original = MANIFEST_PATH.read_text(encoding="utf-8")
        self._assert_manifest_rejected(
            original.replace(
                'source_revision = "PR24 synthetic pose fixture copied into canonical external exchange form"\n',
                "",
            )
        )

    def test_noncanonical_translation_unit_is_rejected(self) -> None:
        original = MANIFEST_PATH.read_text(encoding="utf-8")
        self._assert_manifest_rejected(
            original.replace('translation_unit = "m"', 'translation_unit = "mm"')
        )


if __name__ == "__main__":
    unittest.main()
