from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Phase0SteeringReviewCloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        with (ROOT / "registry" / "progress.toml").open("rb") as stream:
            self.progress = tomllib.load(stream)
        with (
            ROOT / "authorizations" / "steering" / "AUTH-STEER-0001.toml"
        ).open("rb") as stream:
            self.authorization = tomllib.load(stream)

    def test_reviewed_steering_tasks_are_complete(self) -> None:
        tasks = {
            task["id"]: task
            for task in self.progress["phase_0"]["tasks"]
        }
        completed = {
            "P0-STR-004",
            "P0-STR-005",
            "P0-PAR-001",
            "P0-STR-007",
            "P0-STR-008",
            "P0-STR-009",
            "P0-STR-010",
        }
        for task_id in completed:
            self.assertEqual(tasks[task_id]["status"], "complete", task_id)

    def test_installed_state_and_physical_tasks_remain_open(self) -> None:
        tasks = {
            task["id"]: task
            for task in self.progress["phase_0"]["tasks"]
        }
        self.assertEqual(tasks["P0-STR-006"]["status"], "active")
        self.assertEqual(tasks["P0-STR-011"]["status"], "active")

    def test_authorization_is_active_but_optimizer_remains_prohibited(self) -> None:
        self.assertEqual(
            self.authorization["status"],
            "active_reviewed_and_frozen",
        )
        prohibited = " ".join(self.authorization["prohibited"]["items"]).lower()
        self.assertIn("optimization", prohibited)
        self.assertIn("as-built", prohibited)
        self.assertIn("compliance correction", prohibited)

    def test_closeout_review_record_exists(self) -> None:
        review_path = ROOT / "docs" / "reviews" / "phase0_steering_review_closeout.md"
        self.assertTrue(review_path.is_file())
        text = review_path.read_text(encoding="utf-8")
        self.assertIn("P0-STR-004", text)
        self.assertIn("P0-STR-009", text)
        self.assertIn("Tasks intentionally left open", text)


if __name__ == "__main__":
    unittest.main()
