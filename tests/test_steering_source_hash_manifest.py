from __future__ import annotations

from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data_catalog" / "steering_source_hash_manifest.toml"
CONTRACT = ROOT / "schemas" / "source_artifact_hash_contract.toml"
PROGRESS = ROOT / "registry" / "progress.toml"
REVIEW = ROOT / "docs" / "reviews" / "phase0_steering_source_hash_review.md"


class SteeringSourceHashManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.artifacts = cls.manifest["artifacts"]
        cls.by_id = {artifact["artifact_id"]: artifact for artifact in cls.artifacts}

    def test_manifest_identity_hash_and_lineage_states_are_consistent(self) -> None:
        contract = tomllib.loads(CONTRACT.read_text(encoding="utf-8"))
        required = set(contract["required_fields"]["artifact"])
        states = set(contract["enums"]["freeze_state"])
        seen: set[str] = set()

        for artifact in self.artifacts:
            self.assertTrue(required.issubset(artifact))
            artifact_id = artifact["artifact_id"]
            self.assertNotIn(artifact_id, seen)
            seen.add(artifact_id)
            self.assertRegex(artifact_id, r"^SRC-STEER-[0-9]{4}$")
            self.assertIn(artifact["freeze_state"], states)
            self.assertGreaterEqual(artifact["size_bytes"], 0)
            self.assertTrue(artifact["provider_file_id"])
            self.assertTrue(artifact["provider_version_id"])

            provider_sha1 = artifact["provider_sha1"]
            if provider_sha1:
                self.assertRegex(provider_sha1, r"^[0-9a-f]{40}$")

            project_sha256 = artifact["project_sha256"]
            if artifact["freeze_state"] == "sha256_verified":
                self.assertRegex(project_sha256, r"^[0-9a-f]{64}$")
            else:
                self.assertEqual("", project_sha256)

            if artifact["freeze_state"] == "formally_unavailable":
                self.assertTrue(artifact.get("formal_disposition"))

            for parent_id in artifact.get("parent_artifact_ids", []):
                self.assertIn(parent_id, self.by_id)
                self.assertNotEqual(parent_id, artifact_id)

        self.assertEqual(
            {f"SRC-STEER-{number:04d}" for number in range(1, 22)},
            seen,
        )

    def test_all_blocking_artifacts_are_sha256_verified(self) -> None:
        blocking = [artifact for artifact in self.artifacts if artifact["blocking_for_task"]]
        self.assertGreater(len(blocking), 0)
        self.assertTrue(all(item["freeze_state"] == "sha256_verified" for item in blocking))

    def test_critical_hashes_and_provider_corrections_are_frozen(self) -> None:
        expected_sha256 = {
            "SRC-STEER-0001": "025872abaf731bdb37cae3bc94f4f8785c9c7f504c467b2db811bdf03e7ef78a",
            "SRC-STEER-0002": "76ec8d0a318786fe4a5fe352e5821ea600992c9bf554478d4450ac500688469b",
            "SRC-STEER-0003": "d2259359b2f83fb28a8e316e6179751995ffca67f4d057c94f7a7147738d06d2",
            "SRC-STEER-0004": "43d8f1e2aa2859b2d784539f6ee728b8f254b0e4f55594f807718213a29f16ab",
            "SRC-STEER-0005": "2ae4546dc1f60f775ccd914b64a198da9993818132511016c058d1d90d2797e7",
            "SRC-STEER-0006": "87a7c1ba37d130fc8a9aa5fd6b1cbe90bdb0c4cd3394e23ccacd6059801666b5",
            "SRC-STEER-0008": "e33ddb1e3e2dd700de38245c54798463a93f10197246d94858ee6593c082cb41",
            "SRC-STEER-0009": "2d2ed2d3e434c4cba5ab34f0965c00be95b725ed8ccfafaf978ce29b10b19987",
            "SRC-STEER-0010": "ec91ea3b37dfe4718a35ae49f66b5e3ca73ff1d2f289b09bbe74af4de9d4d8b4",
        }
        for artifact_id, digest in expected_sha256.items():
            with self.subTest(artifact_id=artifact_id):
                self.assertEqual(digest, self.by_id[artifact_id]["project_sha256"])

        self.assertEqual("2139121467727", self.by_id["SRC-STEER-0003"]["provider_version_id"])
        self.assertEqual("2140326128861", self.by_id["SRC-STEER-0004"]["provider_version_id"])
        self.assertEqual("2236834892996", self.by_id["SRC-STEER-0006"]["provider_version_id"])
        self.assertEqual(18692, self.by_id["SRC-STEER-0005"]["size_bytes"])

    def test_historical_test3_native_part_has_bounded_formal_disposition(self) -> None:
        artifact = self.by_id["SRC-STEER-0011"]
        self.assertEqual("formally_unavailable", artifact["freeze_state"])
        self.assertFalse(artifact["blocking_for_task"])
        self.assertIn("not the final geometry authority", artifact["formal_disposition"])

    def test_drive_exports_do_not_claim_native_raw_bytes(self) -> None:
        for artifact_id, expected_format in (
            ("SRC-STEER-0007", "xlsx"),
            ("SRC-STEER-0008", "pdf"),
        ):
            artifact = self.by_id[artifact_id]
            self.assertEqual("provider_export_snapshot", artifact["capture_kind"])
            self.assertFalse(artifact["native_bytes_available"])
            self.assertEqual(expected_format, artifact["export_format"])

    def test_progress_and_review_close_the_task_without_closing_physical_work(self) -> None:
        progress = tomllib.loads(PROGRESS.read_text(encoding="utf-8"))
        tasks = {item["id"]: item for item in progress["phase_0"]["tasks"]}
        self.assertEqual("complete", tasks["P0-STR-002"]["status"])
        self.assertNotIn("remaining_gate", tasks["P0-STR-002"])
        self.assertEqual("active", tasks["P0-STR-006"]["status"])
        self.assertEqual("active", tasks["P0-STR-011"]["status"])

        review = REVIEW.read_text(encoding="utf-8")
        self.assertIn("`Default` is the steering-geometry authority", review)
        self.assertIn("`FSA` is retained as a full-car-assembly optimized configuration", review)
        self.assertIn("SOLIDWORKS **Design Studies**", review)
        self.assertIn("must not be added to the measured approximately `4 deg`", review)

    def test_hash_script_uses_sha256_and_binary_reads(self) -> None:
        script = (ROOT / "scripts" / "hash_source_artifacts.py").read_text(encoding="utf-8")
        self.assertIn("hashlib.sha256", script)
        self.assertIn('path.open("rb")', script)
        self.assertNotIn("openpyxl", script)


if __name__ == "__main__":
    unittest.main()
