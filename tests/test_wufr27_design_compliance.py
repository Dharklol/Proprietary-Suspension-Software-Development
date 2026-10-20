"""Source/zero/sign/range tests for nominal WUFR-27 steering compliance bridge."""
from __future__ import annotations

import math
from pathlib import Path
import unittest
from unittest.mock import patch

from pssd_steering.compliance import (
    ComplianceDefinitionError, wufr27_provisional_circular_spans,
)
from pssd_steering.compliance_bridge import PrescribedTorqueInput
from pssd_steering.core import FailureCode, solve_sweep
from pssd_steering.wufr27_design_compliance import (
    evaluate_wufr27_design_source_sweep, load_wufr27_design_source,
)

ROOT = Path(__file__).resolve().parents[1]
SPANS = wufr27_provisional_circular_spans()


def case(angle_deg: float, torque_nm: float) -> PrescribedTorqueInput:
    return PrescribedTorqueInput(
        math.radians(angle_deg), torque_nm,
        "prescribed test input torque, not a physical measurement",
    )


class Wufr27DesignSourceComplianceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_wufr27_design_source(ROOT)

    def test_frozen_input_mapping_and_provenance(self):
        src = self.source
        self.assertEqual(src.geometry.geometry_id, "WUFR27_STEERING_BASELINE_V0")
        self.assertEqual(src.source_parameter_id, "PAR-STEER-0001")
        self.assertEqual(src.evidence_role, "nominal_design_source_not_installed_or_as_built")
        self.assertIn("not physically installed", src.left_reference.source_role)
        self.assertAlmostEqual(src.transmission.rack_m_per_pinion_rad,
                               3.5 * .0254 / (2 * math.pi), places=15)
        self.assertAlmostEqual(src.transmission.pinion_angle_per_input_rad, 1.0)
        self.assertEqual(src.geometry.rack.axis.direction, (0.0, 1.0, 0.0))

    def test_zero_torque_matches_rigid_and_centered_toe(self):
        cases = (case(-80, 0), case(0, 0), case(80, 0))
        rows = evaluate_wufr27_design_source_sweep(
            self.source, cases, spans=SPANS
        )
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertTrue(row.comparison.both_mechanisms_valid)
            for side in ("left", "right"):
                heading = getattr(row, side)
                self.assertIsNone(heading.unavailable_reason)
                self.assertEqual(heading.delta_incremental_rad, 0.0)
                self.assertEqual(heading.rigid_total_rad, heading.loaded_total_rad)
                self.assertEqual(heading.rigid_incremental_rad,
                                 heading.loaded_incremental_rad)
        self.assertAlmostEqual(math.degrees(rows[1].left.rigid_total_rad), -1, places=6)
        self.assertAlmostEqual(math.degrees(rows[1].right.rigid_total_rad), 1, places=6)
        self.assertAlmostEqual(rows[1].left.rigid_incremental_rad, 0.0, delta=1e-8)
        self.assertAlmostEqual(rows[1].right.rigid_incremental_rad, 0.0, delta=1e-8)

    def test_known_design_study_input_and_explicit_loaded_angle(self):
        cases = (case(80, 0), case(80, 23.69800619),
                 case(-80, -23.69800619))
        with patch("pssd_steering.compliance_bridge.solve_sweep",
                   wraps=solve_sweep) as rigid_solver:
            rows = evaluate_wufr27_design_source_sweep(
                self.source, cases, spans=SPANS
            )
        self.assertEqual(rigid_solver.call_count, 2)
        self.assertAlmostEqual(
            rows[0].comparison.rigid_transmission.rack_displacement,
            80 * 3.5 * .0254 / 360,
            places=14,
        )
        self.assertEqual(rows[0].comparison.rigid_transmission.rack_displacement,
                         rows[0].comparison.elastic_transmission.rack_displacement)
        plus = rows[1]
        self.assertTrue(plus.comparison.both_mechanisms_valid)
        self.assertLess(plus.comparison.elastic_transmission.rack_displacement,
                        plus.comparison.rigid_transmission.rack_displacement)
        self.assertGreater(plus.comparison.elastic_twist.twist_rad, 0)
        self.assertIsNotNone(plus.left.delta_incremental_rad)
        self.assertIsNotNone(plus.right.delta_incremental_rad)
        minus = rows[2]
        self.assertGreater(minus.comparison.elastic_transmission.rack_displacement,
                           minus.comparison.rigid_transmission.rack_displacement)
        self.assertLess(minus.comparison.elastic_twist.twist_rad, 0)

    def test_unavailable_on_out_of_domain_not_clipped(self):
        rows = evaluate_wufr27_design_source_sweep(
            self.source, (case(120, 0),), spans=SPANS
        )
        row = rows[0]
        self.assertFalse(row.comparison.both_mechanisms_valid)
        self.assertEqual(row.comparison.left.rigid_position.failure_code,
                         FailureCode.INPUT_OUTSIDE_DOMAIN)
        self.assertIsNone(row.left.delta_incremental_rad)
        self.assertIsNotNone(row.left.unavailable_reason)

    def test_reviewed_transmission_not_automatically_installed(self):
        self.assertIn("design-source only", self.source.transmission.authority)
        # Never allow callers to represent a physically calibrated variant
        # simply by changing the evidence label on the same source object.
        from dataclasses import replace
        suspect = replace(self.source, evidence_role="installed_as_built")
        with self.assertRaises(ComplianceDefinitionError):
            evaluate_wufr27_design_source_sweep(
                suspect, (case(0, 0),), spans=SPANS
            )


if __name__ == "__main__":
    unittest.main()
