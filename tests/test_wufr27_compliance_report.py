"""Smoke-test the machine-readable WUFR-27 synthetic steering comparison report."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Wufr27ComplianceReportTest(unittest.TestCase):
    def test_json_report_preserves_role_and_baseline(self):
        output = io.StringIO()
        script = ROOT / "scripts" / "run_wufr27_compliance_benchmark.py"
        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(stopped.exception.code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"],
                         "synthetic_kinematic_benchmark_not_physical_validation")
        self.assertEqual(len(report["sample_states"]), 15)
        self.assertEqual(report["relative_fit_clearance_envelope_in"], [-.01, .01])
        self.assertIn("NOT the WUFR rack ratio",
                      report["synthetic_transmission_authority"])
        for state in report["sample_states"]:
            self.assertTrue(state["valid"])
            if state["torque_nm"] == 0:
                self.assertEqual(state["rigid_rack_m"], state["elastic_rack_m"])
                self.assertEqual(state["elastic_twist_deg"], 0)
        self.assertTrue(any(
            abs(state["left_delta_incremental_heading_deg"]) > 1e-6
            for state in report["sample_states"]
            if state["torque_nm"] != 0
        ))


if __name__ == "__main__":
    unittest.main()
