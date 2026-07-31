from __future__ import annotations

import unittest

from scripts.audit_r25b_runtime_source import audit_channels


def _linspace(start: float, stop: float, count: int) -> tuple[float, ...]:
    step = (stop - start) / (count - 1)
    return tuple(start + step * index for index in range(count))


def _point_count(fz: float, pressure: float, inclination: float) -> int:
    count = 100
    if fz >= 667.0:
        count += 30
    if pressure >= 68.9:
        count += 30
    if inclination <= 2.0:
        count += 30
    return count


def _exact_generator_channels() -> dict[str, tuple[float, ...]]:
    rows: dict[str, list[float]] = {
        name: []
        for name in ("ET", "FX", "FY", "FZ", "IA", "MX", "MZ", "N", "P", "SA", "SL", "V")
    }
    row_index = 0
    for fz in (222.0, 445.0, 667.0, 890.0, 1112.0):
        for pressure in (96.5, 82.7, 68.9, 55.2):
            for inclination in (0.0, 2.0, 4.0):
                count = _point_count(fz, pressure, inclination)
                for slip in _linspace(-12.0, 12.0, count):
                    row_index += 1
                    rows["ET"].append(row_index * 0.01)
                    rows["FX"].append(0.0)
                    rows["FY"].append(-100.0 * slip + 10.0 * inclination)
                    rows["FZ"].append(fz)
                    rows["IA"].append(inclination)
                    rows["MX"].append(0.0)
                    rows["MZ"].append(0.0)
                    rows["N"].append(470.0)
                    rows["P"].append(pressure)
                    rows["SA"].append(slip)
                    rows["SL"].append(0.0)
                    rows["V"].append(40.2)
    return {name: tuple(values) for name, values in rows.items()}


def _historical_april_channels() -> dict[str, tuple[float, ...]]:
    rows: dict[str, list[float]] = {
        name: []
        for name in ("ET", "FX", "FY", "FZ", "IA", "MX", "MZ", "N", "P", "SA", "SL", "V")
    }
    row_index = 0
    for fz in (222.0, 445.0, 667.0, 1112.0):
        for pressure in (68.9, 82.7, 96.5):
            for inclination in (0.0, 2.0, 4.0):
                for slip in _linspace(-12.0, 12.0, 100):
                    row_index += 1
                    rows["ET"].append(row_index * 0.01)
                    rows["FX"].append(0.0)
                    rows["FY"].append(-100.0 * slip + 10.0 * inclination)
                    rows["FZ"].append(fz)
                    rows["IA"].append(inclination)
                    rows["MX"].append(0.0)
                    rows["MZ"].append(0.0)
                    rows["N"].append(470.0)
                    rows["P"].append(pressure)
                    rows["SA"].append(slip)
                    rows["SL"].append(0.0)
                    rows["V"].append(40.2)
    return {name: tuple(values) for name, values in rows.items()}


class R25bRuntimeSourceAuditTests(unittest.TestCase):
    def test_exact_live_script_shape_is_accepted(self) -> None:
        audit = audit_channels(_exact_generator_channels())
        self.assertTrue(audit.exact_generator_profile_matches_binary)
        self.assertFalse(audit.historical_april_profile_matches_binary)
        self.assertEqual(audit.total_rows, 9630)
        self.assertEqual(audit.state_count, 60)
        self.assertEqual(
            audit.rows_per_state_histogram,
            ((100, 2), (130, 13), (160, 27), (190, 18)),
        )
        self.assertEqual(audit.prepeak_rejected_state_count, 0)
        self.assertTrue(audit.all_state_slip_grids_strictly_increasing)
        self.assertTrue(audit.all_state_slip_grids_span_minus12_to_plus12_deg)

    def test_historical_april_profile_is_retained_but_non_governing(self) -> None:
        audit = audit_channels(_historical_april_channels())
        self.assertFalse(audit.exact_generator_profile_matches_binary)
        self.assertTrue(audit.historical_april_profile_matches_binary)
        self.assertEqual(audit.total_rows, 3600)
        self.assertTrue(any("row count" in reason for reason in audit.mismatch_reasons))

    def test_changed_load_plane_fails_profile_match_without_data_repair(self) -> None:
        mutable = {name: list(values) for name, values in _exact_generator_channels().items()}
        first_state_rows = _point_count(222.0, 96.5, 0.0)
        mutable["FZ"][:first_state_rows] = [1557.0] * first_state_rows

        audit = audit_channels(mutable)
        self.assertFalse(audit.exact_generator_profile_matches_binary)
        self.assertIn(1557.0, audit.normal_load_values_n)
        self.assertTrue(any("FZ lattice" in reason for reason in audit.mismatch_reasons))

    def test_nonmonotonic_prepeak_state_is_reported_not_repaired(self) -> None:
        mutable = {name: list(values) for name, values in _exact_generator_channels().items()}
        state_indices = [
            index
            for index, (fz, ia, pressure) in enumerate(
                zip(mutable["FZ"], mutable["IA"], mutable["P"])
            )
            if fz == 222.0 and ia == 0.0 and pressure == 68.9
        ]
        negative_indices = [index for index in state_indices if mutable["SA"][index] < 0.0]
        mutable["FY"][negative_indices[-11]] = mutable["FY"][negative_indices[-10]] - 1.0

        audit = audit_channels(mutable)
        self.assertEqual(audit.prepeak_rejected_state_count, 1)
        self.assertIn("Fz=222N;IA=0deg;P=68.9kPa", audit.prepeak_rejected_states[0])


if __name__ == "__main__":
    unittest.main()
