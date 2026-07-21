from __future__ import annotations

from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data_catalog" / "steering_source_hash_manifest.toml"
CONTRACT = ROOT / "schemas" / "source_artifact_hash_contract.toml"
PROGRESS = ROOT / "registry" / "progress.toml"


class SteeringSourceHashManifestTests(unittest.TestCase):
    def test_manifest_identity_and_hash_states_are_consistent(self) -> None:
        manifest = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        contract = tomllib.loads(CONTRACT.read_text(encoding="utf-8"))
        required = set(contract["required_fields"]["artifact"])
        states = set(contract["enums"]["freeze_state"])
        seen: set[str] = set()

        for artifact in manifest["artifacts"]:
            self.assertTrue(required.issubset(artifact))
            artifact_id = artifact["artifact_id"]
            self.assertNotIn(artifact_id, seen)
            seen.add(artifact_id)
            self.assertRegex(artifact_id, r"^SRC-STEER-[0-9]{4}$")
            self.assertIn(artifact["freeze_state"], states)
            self.assertGreaterEqual(artifact["size_bytes"], 0)
            provider_sha1 = artifact["provider_sha1"]
            if provider_sha1:
                self.assertRegex(provider_sha1, r"^[0-9a-f]{40}$")
            project_sha256 = artifact["project_sha256"]
            if artifact["freeze_state"] == "sha256_verified":
                self.assertRegex(project_sha256, r"^[0-9a-f]{64}$")
            else:
                self.assertIn(project_sha256, ("",))

        self.assertEqual(
            {f"SRC-STEER-{number:04d}" for number in range(1, 8)},
            seen,
        )

    def test_progress_does_not_overclaim_completion(self) -> None:
        progress = tomllib.loads(PROGRESS.read_text(encoding="utf-8"))
        task = next(
            item for item in progress["phase_0"]["tasks"] if item["id"] == "P0-STR-002"
        )
        self.assertEqual("review_ready", task["status"])
        self.assertIn("SHA-256", task["remaining_gate"])

    def test_hash_script_uses_sha256_and_binary_reads(self) -> None:
        script = (ROOT / "scripts" / "hash_source_artifacts.py").read_text(encoding="utf-8")
        self.assertIn("hashlib.sha256", script)
        self.assertIn('path.open("rb")', script)
        self.assertNotIn("openpyxl", script)


if __name__ == "__main__":
    unittest.main()
