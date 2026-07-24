from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_vehicle_operating_state_benchmarks.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("vehicle_operating_state_benchmarks", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VehicleOperatingStateFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        module = _load_script()
        cls.summary = module.summary_report(module.build_report())
        cls.states = {item["state_id"]: item for item in cls.summary["states"]}

    def test_source_identity_and_state_count_are_frozen(self) -> None:
        self.assertEqual("BENCH-VEH-0001", self.summary["benchmark_id"])
        self.assertEqual("MOD-VEH-0001", self.summary["model_id"])
        self.assertEqual(
            "WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0",
            self.summary["state_set_id"],
        )
        self.assertEqual(
            "sha256:505f567a132296fe90876b1202d9bd626d8b0f302ff4c6316d013d0306ab24fc",
            self.summary["source_revision"],
        )
        self.assertEqual(2, self.summary["state_count"])

    def test_right_turn_reference_is_frozen(self) -> None:
        state = self.states["SC26_EDGE3_1P2G_RIGHT_AERO_NO_ARB"]
        self.assertEqual("evidence_only", state["role"])
        self.assertEqual("right", state["turn_direction"])
        self.assertAlmostEqual(-1.2, state["ay_g"], places=14)
        self.assertAlmostEqual(17.8816, state["speed_mps"], places=14)
        self.assertAlmostEqual(3817.0270885, state["total_normal_load_n"], places=7)
        self.assertEqual("front_right", state["front_inside_position"])
        self.assertEqual("front_left", state["front_outside_position"])
        self.assertAlmostEqual(186.2139907, state["front_inside_normal_load_n"], places=9)
        self.assertAlmostEqual(1719.575445, state["front_outside_normal_load_n"], places=9)

    def test_left_turn_reference_is_frozen(self) -> None:
        state = self.states["SC26_EDGE4_1P2G_LEFT_AERO_NO_ARB"]
        self.assertEqual("evidence_only", state["role"])
        self.assertEqual("left", state["turn_direction"])
        self.assertAlmostEqual(1.2, state["ay_g"], places=14)
        self.assertAlmostEqual(17.8816, state["speed_mps"], places=14)
        self.assertAlmostEqual(3817.0270885, state["total_normal_load_n"], places=7)
        self.assertEqual("front_left", state["front_inside_position"])
        self.assertEqual("front_right", state["front_outside_position"])
        self.assertAlmostEqual(516.8481725, state["front_inside_normal_load_n"], places=9)
        self.assertAlmostEqual(1388.941263, state["front_outside_normal_load_n"], places=9)

    def test_negative_source_state_remains_rejected_audit_evidence(self) -> None:
        rejected = self.summary["rejected_source_states"]
        self.assertEqual(1, len(rejected))
        self.assertEqual("rear_left", rejected[0]["rejected_wheel"])
        self.assertAlmostEqual(-285.3358453, rejected[0]["rejected_normal_load_n"], places=9)
        self.assertIn("physically invalid", rejected[0]["reason"])


if __name__ == "__main__":
    unittest.main()
