from __future__ import annotations

import json
from pathlib import Path
import unittest

from pssd_tire.r25b_branch_classification_audit import (
    audit_r25b_branch_classification,
    build_r25b_branch_classification_result,
)


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "benchmarks/tires/r25b_branch_classification_audit_v0.1.0.json"


class R25bBranchClassificationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = audit_r25b_branch_classification()
        cls.result = build_r25b_branch_classification_result()

    def test_exact_source_coverage_and_zero_knot_boundary(self) -> None:
        self.assertEqual(self.audit.curve_count, 60)
        self.assertEqual(self.audit.sample_count, 9630)
        self.assertEqual(len(self.audit.side_audits), 120)
        self.assertEqual(self.audit.exact_zero_slip_knot_curve_count, 0)

    def test_reversal_counts_match_exact_source_audit(self) -> None:
        positive = self.result["positive_side"]
        negative = self.result["negative_side"]
        combined = self.result["combined"]
        self.assertEqual(positive["reversal_affected_curve_count"], 4)
        self.assertEqual(positive["reversal_segment_count"], 7)
        self.assertEqual(negative["reversal_affected_curve_count"], 9)
        self.assertEqual(negative["reversal_segment_count"], 13)
        self.assertEqual(combined["reversal_affected_side_count"], 13)
        self.assertEqual(combined["reversal_affected_curve_count"], 12)

    def test_boundary_extrema_and_maximum_policy_costs_are_frozen(self) -> None:
        self.assertEqual(self.result["positive_side"]["peak_at_source_boundary_count"], 13)
        self.assertEqual(self.result["negative_side"]["peak_at_source_boundary_count"], 18)
        combined = self.result["combined"]
        self.assertAlmostEqual(
            combined["maximum_local_reversal_N"],
            0.48474469855204916,
            places=12,
        )
        self.assertAlmostEqual(
            combined["maximum_strict_prefix_force_shortfall_N"],
            6.812387228250657,
            places=12,
        )
        self.assertAlmostEqual(
            combined["maximum_strict_prefix_relative_force_shortfall"],
            0.013213031258643019,
            places=15,
        )
        self.assertAlmostEqual(
            combined["maximum_strict_prefix_slip_truncation_deg"],
            1.9622641509433962,
            places=12,
        )
        self.assertAlmostEqual(
            combined["maximum_global_extremum_ambiguous_force_span_N"],
            0.7573035179882481,
            places=12,
        )
        self.assertEqual(combined["maximum_side_local_root_count"], 3)

    def test_policy_options_preserve_no_repair_boundary(self) -> None:
        policies = self.result["policy_candidates"]
        self.assertFalse(
            policies["strict_monotonic_prefix"]["source_sample_values_modified"]
        )
        self.assertTrue(
            policies["strict_monotonic_prefix"]["unique_monotonic_side_inverse"]
        )
        self.assertFalse(
            policies["global_extremum_positional"]["source_sample_values_modified"]
        )
        self.assertTrue(
            policies["global_extremum_positional"][
                "multiple_named_prepeak_roots_possible"
            ]
        )
        self.assertTrue(
            policies["tolerance_or_isotonic_repair"]["source_sample_values_modified"]
        )
        self.assertFalse(
            policies["tolerance_or_isotonic_repair"][
                "compatible_with_current_no_repair_authorization"
            ]
        )

    def test_audit_does_not_assign_or_authorize_branch_ids(self) -> None:
        self.assertEqual(
            self.result["status"], "review_required_no_branch_ids_assigned"
        )
        self.assertEqual(len(self.result["unresolved_decisions"]), 4)

    def test_frozen_json_matches_deterministic_regeneration(self) -> None:
        frozen = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertEqual(frozen, self.result)


if __name__ == "__main__":
    unittest.main()
