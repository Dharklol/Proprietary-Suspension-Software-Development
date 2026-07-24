from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from pssd_viz import (
    EngineeringFigureSpec,
    FigureAvailability,
    FigureContractError,
    FigureMetadata,
    SeriesSpec,
    artifact_record,
    sha256_file,
    write_figure_manifest,
    write_report_manifest,
)


HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


def metadata(figure_id: str = "FIG-TEST-001") -> FigureMetadata:
    return FigureMetadata(
        figure_id=figure_id,
        title="Test Figure",
        x_quantity="Input",
        x_unit="deg",
        y_quantity="Output",
        y_unit="deg",
        model_id="MOD-TEST-0001",
        configuration_id="TEST_CONFIG_V0",
        authority="synthetic_test_only",
        state_ids=("state_a",),
        source_ids=("source_a",),
    )


class VisualizationContractTests(unittest.TestCase):
    def test_available_figure_requires_series(self) -> None:
        with self.assertRaises(FigureContractError):
            EngineeringFigureSpec(metadata=metadata())

    def test_unavailable_figure_requires_reason_and_no_series(self) -> None:
        with self.assertRaises(FigureContractError):
            EngineeringFigureSpec(
                metadata=metadata(),
                availability=FigureAvailability.UNAVAILABLE,
            )

        with self.assertRaises(FigureContractError):
            EngineeringFigureSpec(
                metadata=metadata(),
                series=(SeriesSpec(label="a", x=(0.0,), y=(0.0,)),),
                availability=FigureAvailability.UNAVAILABLE,
                unavailable_reason="missing source",
            )

    def test_nonfinite_or_mismatched_series_rejected(self) -> None:
        with self.assertRaises(FigureContractError):
            SeriesSpec(label="bad", x=(0.0, 1.0), y=(0.0,))
        with self.assertRaises(FigureContractError):
            SeriesSpec(label="bad", x=(0.0,), y=(float("nan"),))

    def test_fingerprint_is_stable_for_equal_specs(self) -> None:
        first = EngineeringFigureSpec(
            metadata=metadata(),
            series=(SeriesSpec(label="series", x=(0.0, 1.0), y=(1.0, 2.0)),),
        )
        second = EngineeringFigureSpec(
            metadata=metadata(),
            series=(SeriesSpec(label="series", x=(0.0, 1.0), y=(1.0, 2.0)),),
        )
        self.assertEqual(first.fingerprint(), second.fingerprint())

    def test_manifest_hashes_rendered_artifact_bytes(self) -> None:
        spec = EngineeringFigureSpec(
            metadata=metadata(),
            series=(SeriesSpec(label="series", x=(0.0,), y=(1.0,)),),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "figure.svg"
            artifact.write_text("<svg>test</svg>\n", encoding="utf-8")
            record = artifact_record(artifact, root=root)
            manifest = write_figure_manifest(
                spec,
                (record,),
                root / "figure.manifest.json",
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifacts"][0]["path"], "figure.svg")
            self.assertEqual(payload["artifacts"][0]["sha256"], sha256_file(artifact))
            self.assertEqual(payload["figure_fingerprint_sha256"], spec.fingerprint())

            report = write_report_manifest(
                report_id="TEST_REPORT",
                figure_manifests=(manifest,),
                output_path=root / "report.manifest.json",
            )
            report_payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["report_id"], "TEST_REPORT")
            self.assertEqual(report_payload["figure_manifests"][0]["path"], manifest.name)


@unittest.skipUnless(HAS_MATPLOTLIB, "visualization backend optional dependency not installed")
class MatplotlibRendererTests(unittest.TestCase):
    def test_available_and_unavailable_figures_render_nonblank_svg_and_png(self) -> None:
        from pssd_viz.matplotlib_renderer import render_engineering_figure

        available = EngineeringFigureSpec(
            metadata=metadata("FIG-TEST-RENDER-001"),
            series=(
                SeriesSpec(label="left", x=(-1.0, 0.0, 1.0), y=(-2.0, 0.0, 2.0)),
                SeriesSpec(label="right", x=(-1.0, 0.0, 1.0), y=(-1.8, 0.0, 1.8)),
            ),
        )
        unavailable = EngineeringFigureSpec(
            metadata=metadata("FIG-TEST-RENDER-002"),
            availability=FigureAvailability.UNAVAILABLE,
            unavailable_reason="No reviewed source supplied.",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_outputs = render_engineering_figure(
                available,
                root / "available",
                formats=("svg", "png"),
            )
            unavailable_outputs = render_engineering_figure(
                unavailable,
                root / "unavailable",
                formats=("svg", "png"),
            )

            for path in (*first_outputs, *unavailable_outputs):
                self.assertGreater(path.stat().st_size, 500)

            available_svg = first_outputs[0].read_text(encoding="utf-8")
            unavailable_svg = unavailable_outputs[0].read_text(encoding="utf-8")
            self.assertIn("FIG-TEST-RENDER-001", available_svg)
            self.assertIn("FIGURE UNAVAILABLE", unavailable_svg)
            self.assertIn("No reviewed source supplied", unavailable_svg)

    def test_svg_is_deterministic_for_same_spec(self) -> None:
        from pssd_viz.matplotlib_renderer import render_engineering_figure

        spec = EngineeringFigureSpec(
            metadata=metadata("FIG-TEST-DETERMINISM-001"),
            series=(SeriesSpec(label="series", x=(0.0, 1.0), y=(0.0, 1.0)),),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = render_engineering_figure(spec, root / "figure", formats=("svg",))[0]
            first_hash = sha256_file(path)
            path.unlink()
            path = render_engineering_figure(spec, root / "figure", formats=("svg",))[0]
            self.assertEqual(first_hash, sha256_file(path))


if __name__ == "__main__":
    unittest.main()
