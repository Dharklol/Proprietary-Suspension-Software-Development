from __future__ import annotations

import math
import unittest

from pssd_steering.comparison import (
    ComparisonStatus,
    MonitorNormalization,
    SeriesError,
    SignalSeries,
    compare_series,
    level_e_missing_metadata,
    normalize_periodic_monitor,
    parse_transposed_csv_text,
    unwrap_periodic,
)


class TransposedCSVTests(unittest.TestCase):
    def test_parse_preserves_order_and_identity(self) -> None:
        text = "Steer Input,-2,-1,0,1,2\nDimension2,31,31.5,32,32.5,33\n"
        series = parse_transposed_csv_text(
            text,
            source_id="TEST-CAD-001",
            input_row_label="Steer Input",
            output_row_label="Dimension2",
            input_quantity_id="CAD-SIGNAL-STEER-INPUT",
            output_quantity_id="CAD-SIGNAL-DIMENSION2",
            input_unit="deg",
            output_unit="deg",
        )
        self.assertEqual(series.inputs, (-2.0, -1.0, 0.0, 1.0, 2.0))
        self.assertEqual(series.outputs[2], 32.0)
        self.assertIn("without reordering", series.processing_notes[0])

    def test_rejects_nonmonotonic_input(self) -> None:
        text = "Steer Input,0,2,1\nDimension2,0,1,2\n"
        with self.assertRaises(SeriesError):
            parse_transposed_csv_text(
                text,
                source_id="BAD",
                input_row_label="Steer Input",
                output_row_label="Dimension2",
                input_quantity_id="input",
                output_quantity_id="output",
                input_unit="deg",
                output_unit="deg",
            )


class MonitorNormalizationTests(unittest.TestCase):
    def test_periodic_unwrap(self) -> None:
        self.assertEqual(
            unwrap_periodic((350.0, 355.0, 1.0, 5.0), period=360.0),
            (350.0, 355.0, 361.0, 365.0),
        )

    def test_sign_and_center_are_explicit(self) -> None:
        raw = SignalSeries(
            source_id="CAD",
            input_quantity_id="CAD-INPUT",
            output_quantity_id="CAD-MONITOR",
            input_unit="deg",
            output_unit="deg",
            inputs=(-1.0, 0.0, 1.0),
            outputs=(359.0, 0.0, 1.0),
        )
        normalized = normalize_periodic_monitor(
            raw,
            MonitorNormalization(
                output_sign=-1.0,
                period=360.0,
                center_input=0.0,
                subtract_center=True,
                description="synthetic declared monitor orientation",
            ),
            normalized_output_quantity_id="INCREMENTAL-MONITOR-ANGLE",
        )
        self.assertEqual(normalized.outputs, (1.0, 0.0, -1.0))
        self.assertEqual(normalized.output_quantity_id, "INCREMENTAL-MONITOR-ANGLE")
        self.assertTrue(any("subtracted value" in note for note in normalized.processing_notes))


class ComparisonTests(unittest.TestCase):
    def test_exact_and_nonzero_residual_metrics(self) -> None:
        reference = SignalSeries(
            source_id="REFERENCE",
            input_quantity_id="QTY-STEER-0004",
            output_quantity_id="UPRIGHT-ROTATION",
            input_unit="m",
            output_unit="rad",
            inputs=(-1.0, 0.0, 1.0),
            outputs=(-2.0, 0.0, 2.0),
        )
        candidate = SignalSeries(
            source_id="CANDIDATE",
            input_quantity_id="QTY-STEER-0004",
            output_quantity_id="UPRIGHT-ROTATION",
            input_unit="m",
            output_unit="rad",
            inputs=(-0.5, 0.0, 0.5),
            outputs=(-0.9, 0.0, 0.9),
        )
        result = compare_series(reference, candidate)
        self.assertEqual(result.status, ComparisonStatus.AVAILABLE)
        self.assertIsNotNone(result.metrics)
        assert result.metrics is not None
        self.assertAlmostEqual(result.metrics.mean_error, 0.0, places=15)
        self.assertAlmostEqual(result.metrics.rmse, math.sqrt(0.02 / 3.0), places=15)
        self.assertAlmostEqual(result.metrics.maximum_absolute_error, 0.1, places=15)

    def test_quantity_mismatch_is_unavailable(self) -> None:
        reference = SignalSeries(
            source_id="REFERENCE",
            input_quantity_id="rack",
            output_quantity_id="upright_rotation",
            input_unit="m",
            output_unit="rad",
            inputs=(0.0, 1.0),
            outputs=(0.0, 1.0),
        )
        candidate = SignalSeries(
            source_id="CAD",
            input_quantity_id="steer_input",
            output_quantity_id="dimension2",
            input_unit="deg",
            output_unit="deg",
            inputs=(0.0, 1.0),
            outputs=(0.0, 1.0),
        )
        result = compare_series(reference, candidate)
        self.assertEqual(result.status, ComparisonStatus.UNAVAILABLE)
        self.assertIn("input_quantity_id", result.missing_or_conflicting_items)
        self.assertIn("output_quantity_id", result.missing_or_conflicting_items)

    def test_extrapolation_is_not_permitted(self) -> None:
        reference = SignalSeries(
            source_id="REFERENCE",
            input_quantity_id="x",
            output_quantity_id="y",
            input_unit="m",
            output_unit="rad",
            inputs=(0.0, 1.0),
            outputs=(0.0, 1.0),
        )
        candidate = SignalSeries(
            source_id="CANDIDATE",
            input_quantity_id="x",
            output_quantity_id="y",
            input_unit="m",
            output_unit="rad",
            inputs=(-0.1, 0.5),
            outputs=(0.0, 0.5),
        )
        result = compare_series(reference, candidate)
        self.assertEqual(result.status, ComparisonStatus.UNAVAILABLE)
        self.assertEqual(
            result.missing_or_conflicting_items,
            ("overlapping_domain_without_extrapolation",),
        )


class ReadinessGateTests(unittest.TestCase):
    def test_level_e_gate_lists_only_unresolved_items(self) -> None:
        metadata = {
            "source_file_id_and_version": "box:2357045252883/v2611346929683",
            "source_hash": "69d71c0977287a13385683204344e78816b48512",
            "active_solidworks_configuration": "unresolved",
            "motion_study_name_and_settings": "unresolved",
            "input_signal_identity": "unresolved",
            "output_signal_identity": "unresolved",
            "input_sign_and_unit": "deg; sign unresolved",
            "output_sign_unit_and_monitor_definition": "unresolved",
            "rack_center_or_zero_input_definition": "input zero observed; construction unresolved",
            "static_toe_and_wheel_plane_reference": "unresolved",
            "evaluated_domain_and_stop_state": "-102 to 102 deg export; physical stops unresolved",
        }
        missing = level_e_missing_metadata(metadata)
        self.assertNotIn("source_hash", missing)
        self.assertIn("active_solidworks_configuration", missing)
        self.assertIn("output_signal_identity", missing)


if __name__ == "__main__":
    unittest.main()
