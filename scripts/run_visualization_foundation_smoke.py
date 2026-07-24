"""Generate deterministic smoke figures for the engineering visualization layer."""

from __future__ import annotations

import argparse
from pathlib import Path

from pssd_viz import (
    EngineeringFigureSpec,
    FigureAvailability,
    FigureMetadata,
    SeriesSpec,
    artifact_record,
    write_figure_manifest,
    write_report_manifest,
)
from pssd_viz.matplotlib_renderer import render_engineering_figure


def build_available_spec() -> EngineeringFigureSpec:
    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id="FIG-VIZ-SMOKE-001",
            title="Visualization Foundation Smoke Figure",
            x_quantity="Steering input",
            x_unit="deg",
            y_quantity="Road-wheel heading",
            y_unit="deg",
            model_id="MOD-STEER-0001",
            configuration_id="VIZ_SMOKE_SYNTHETIC_V0",
            authority="synthetic_visualization_smoke_only",
            state_ids=("nominal",),
            source_ids=("synthetic",),
            notes=("Synthetic values exercise rendering only; they are not WUFR design evidence.",),
        ),
        series=(
            SeriesSpec.from_iterables(
                label="left",
                x=(-30.0, -15.0, 0.0, 15.0, 30.0),
                y=(-8.4, -4.1, 0.0, 4.3, 8.9),
            ),
            SeriesSpec.from_iterables(
                label="right",
                x=(-30.0, -15.0, 0.0, 15.0, 30.0),
                y=(-8.9, -4.3, 0.0, 4.1, 8.4),
            ),
        ),
    )


def build_unavailable_spec() -> EngineeringFigureSpec:
    return EngineeringFigureSpec(
        metadata=FigureMetadata(
            figure_id="FIG-VIZ-SMOKE-002",
            title="Explicit Missing-Data Figure",
            x_quantity="Body speed",
            x_unit="m/s",
            y_quantity="Yaw rate",
            y_unit="rad/s",
            model_id="MOD-VEH-0002",
            configuration_id="VIZ_SMOKE_MISSING_SOURCE_V0",
            authority="missing_source_demonstration",
            state_ids=("pending_vehicle_motion_state",),
            source_ids=(),
        ),
        availability=FigureAvailability.UNAVAILABLE,
        unavailable_reason=(
            "No reviewed synchronized planar-motion source was supplied. "
            "The visualization layer refuses to render an empty or inferred curve."
        ),
    )


def render_spec(spec: EngineeringFigureSpec, output_dir: Path) -> Path:
    stem = output_dir / spec.metadata.figure_id
    outputs = render_engineering_figure(spec, stem, formats=("svg", "png"))
    records = tuple(artifact_record(path, root=output_dir) for path in outputs)
    manifest = output_dir / f"{spec.metadata.figure_id}.manifest.json"
    return write_figure_manifest(spec, records, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/generated/visualization_foundation_smoke"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifests = [
        render_spec(build_available_spec(), args.output_dir),
        render_spec(build_unavailable_spec(), args.output_dir),
    ]
    report_path = write_report_manifest(
        report_id="VIZ_FOUNDATION_SMOKE_V0",
        figure_manifests=manifests,
        output_path=args.output_dir / "report.manifest.json",
    )
    print(report_path)


if __name__ == "__main__":
    main()
