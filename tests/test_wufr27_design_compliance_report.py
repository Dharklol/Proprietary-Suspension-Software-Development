"""Report smoke and provenance checks for WUFR-27 nominal steering compliance."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Wufr27DesignReportTests(unittest.TestCase):
    def test_report_has_real_source_identity_and_valid_sweeps(self):
        buffer = io.StringIO()
        script = ROOT / "scripts/run_wufr27_design_compliance_benchmarks.py"
        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as stopped:
                runpy.run_path(str(script), run_name="__main__")
        self.assertEqual(stopped.exception.code, 0)
        report = json.loads(buffer.getvalue())
        self.assertEqual(
            report["evidence_role"],
            "nominal_design_source_not_installed_or_as_built",
        )
        self.assertEqual(report["source_parameter_id"], "PAR-STEER-0001")
        self.assertEqual(report["geometry_id"], "WUFR27_STEERING_BASELINE_V0")
        self.assertAlmostEqual(report["rack_m_per_input_radian"],
                               3.5 * .0254 / (2 * 3.141592653589793))
        self.assertIn("not measured driver torque", report["torque_source"])
        rows = report["states"]
        self.assertEqual(len(rows), 36)
        self.assertTrue(all(row["rigid_and_loaded_closure_valid"] for row in rows))
        self.assertTrue(all(row["left_unavailable_reason"] is None for row in rows))
        self.assertTrue(all(row["right_unavailable_reason"] is None for row in rows))
        base = [r for r in rows if r["load_scenario"] == "zero_torque_rigid_baseline"]
        self.assertEqual(len(base), 9)
        for row in base:
            self.assertEqual(row["rigid_rack_mm"], row["loaded_rack_mm"])
            self.assertEqual(row["left_loaded_minus_rigid_incremental_deg"], 0.0)
            self.assertEqual(row["right_loaded_minus_rigid_incremental_deg"], 0.0)
        center = [r for r in base if r["driver_command_deg"] == 0][0]
        self.assertAlmostEqual(center["left_rigid_total_deg"], -1.0, places=5)
        self.assertAlmostEqual(center["right_rigid_total_deg"], 1.0, places=5)
        loaded = [
            r for r in rows
            if r["load_scenario"] == "calculated_factored_parked_column_moment"
            and r["driver_command_deg"] > 0
        ]
        self.assertTrue(all(r["free_span_elastic_twist_deg"] > 0 for r in loaded))
        self.assertTrue(all(r["loaded_rack_mm"] < r["rigid_rack_mm"] for r in loaded))
        self.assertTrue(any(
            abs(r["left_loaded_minus_rigid_incremental_deg"]) > 0
            for r in loaded
        ))


if __name__ == "__main__":
    unittest.main()
