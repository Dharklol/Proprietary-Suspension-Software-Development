from __future__ import annotations

import unittest

from pssd_tire import TireDataError, TireOperatingPoint
from pssd_tire.ttc_cornering import (
    WUFR26_APRIL_CORNERING_TROJAN_V0,
    build_branch_set,
    export_cornering_trojan_branch,
)


def _channels(*, nonmonotonic: bool = False) -> dict[str, tuple[float, ...]]:
    # Two exact Trojan-style operating points, each with a symmetric SA sweep.  The
    # negative-SA/positive-FY side is the reviewed into-turn branch used by the WUFR
    # source profile.  Values are synthetic software evidence only.
    sa = (-6.0, -4.0, -2.0, -0.5, 0.5, 2.0, 4.0, 6.0)
    fy_a = (900.0, 800.0, 500.0, 150.0, -150.0, -500.0, -800.0, -900.0)
    if nonmonotonic:
        fy_a = (900.0, 480.0, 500.0, 150.0, -150.0, -500.0, -800.0, -900.0)
    fy_b = (2100.0, 1900.0, 1300.0, 350.0, -350.0, -1300.0, -1900.0, -2100.0)

    return {
        "SA": sa + sa,
        "FY": fy_a + fy_b,
        "FZ": (222.0,) * len(sa) + (1112.0,) * len(sa),
        "IA": (0.0,) * len(sa) + (2.0,) * len(sa),
        "P": (82.7,) * (2 * len(sa)),
        "SL": (0.0,) * (2 * len(sa)),
        "V": (40.2,) * (2 * len(sa)),
    }


class TtcCorneringExportTests(unittest.TestCase):
    def test_exports_exact_negative_sa_positive_fy_prepeak_branch(self) -> None:
        result = export_cornering_trojan_branch(
            _channels(),
            TireOperatingPoint(222.0, 0.0, 82.7),
            branch_id="inside",
            authority="synthetic_test_only",
            source_branch_description="synthetic Trojan-style branch",
        )

        self.assertEqual(result.audit.profile_id, WUFR26_APRIL_CORNERING_TROJAN_V0.profile_id)
        self.assertEqual(result.audit.total_source_rows, 16)
        self.assertEqual(result.audit.operating_point_rows, 8)
        self.assertEqual(result.audit.selected_quadrant_rows, 4)
        self.assertEqual(result.audit.prepeak_rows, 4)
        self.assertEqual(result.audit.source_peak_slip_angle_deg, -6.0)
        self.assertEqual(result.audit.source_peak_lateral_force_n, 900.0)
        self.assertEqual(
            [sample.slip_angle_magnitude_deg for sample in result.branch.samples],
            [0.5, 2.0, 4.0, 6.0],
        )
        self.assertEqual(
            [sample.lateral_force_magnitude_n for sample in result.branch.samples],
            [150.0, 500.0, 800.0, 900.0],
        )

    def test_operating_point_selection_is_exact_and_does_not_interpolate(self) -> None:
        with self.assertRaisesRegex(TireDataError, "exact requested operating point"):
            export_cornering_trojan_branch(
                _channels(),
                TireOperatingPoint(500.0, 1.0, 82.7),
                branch_id="missing",
                authority="synthetic_test_only",
                source_branch_description="missing state",
            )

    def test_rejects_nonmonotonic_source_instead_of_smoothing_or_enveloping(self) -> None:
        with self.assertRaisesRegex(TireDataError, "will not smooth"):
            export_cornering_trojan_branch(
                _channels(nonmonotonic=True),
                TireOperatingPoint(222.0, 0.0, 82.7),
                branch_id="bad",
                authority="synthetic_test_only",
                source_branch_description="synthetic nonmonotonic branch",
            )

    def test_rejects_wrong_speed_and_nonzero_slip_ratio(self) -> None:
        channels = _channels()
        channels["V"] = tuple(39.0 for _ in channels["V"])
        with self.assertRaisesRegex(TireDataError, "exact requested operating point"):
            export_cornering_trojan_branch(
                channels,
                TireOperatingPoint(222.0, 0.0, 82.7),
                branch_id="wrong-speed",
                authority="synthetic_test_only",
                source_branch_description="wrong speed",
            )

    def test_builds_generic_force_demand_branch_set_without_losing_tire_identity(self) -> None:
        inside = export_cornering_trojan_branch(
            _channels(),
            TireOperatingPoint(222.0, 0.0, 82.7),
            branch_id="inside",
            authority="synthetic_test_only",
            source_branch_description="synthetic inside",
        )
        outside = export_cornering_trojan_branch(
            _channels(),
            TireOperatingPoint(1112.0, 2.0, 82.7),
            branch_id="outside",
            authority="synthetic_test_only",
            source_branch_description="synthetic outside",
        )
        branch_set = build_branch_set(
            (inside, outside),
            branch_set_id="test-set",
            version="0.1.0",
            source_tire_id="HOOSIER_43105_18X7.5-10_R25B",
            intended_tire_id="HOOSIER_43104_18X7.5-10_R20",
            authority="synthetic_test_only",
            source_path="synthetic",
        )
        self.assertEqual(len(branch_set.branches), 2)
        self.assertEqual(branch_set.source_tire_id, "HOOSIER_43105_18X7.5-10_R25B")
        self.assertEqual(branch_set.intended_tire_id, "HOOSIER_43104_18X7.5-10_R20")
        self.assertEqual(
            branch_set.branches[1].samples[-1].lateral_force_magnitude_n,
            2100.0,
        )


if __name__ == "__main__":
    unittest.main()
