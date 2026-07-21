#!/usr/bin/env python3
"""Generate the WUFR-26 canonical projected-heading Level E comparison."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from pssd_steering import load_geometry, load_wheel_angle_fits
from pssd_steering.level_e import compare_wufr26_projected_heading

SOURCE_INPUT_MIN_DEG = -102
SOURCE_INPUT_MAX_DEG = 102
RACK_TRAVEL_IN_PER_REV = 3.5
RACK_TRAVEL_M_PER_INPUT_DEG = RACK_TRAVEL_IN_PER_REV * 0.0254 / 360.0
SUMMARY_SAMPLE_INPUTS_DEG = (-102.0, -50.0, 0.0, 50.0, 102.0)


def _side_report(side) -> dict:
    return {
        "canonical_static_deg": side.canonical_static_deg,
        "historical_static_deg": side.historical_static_deg,
        "static_difference_deg": side.canonical_static_deg - side.historical_static_deg,
        "total": {
            "status": side.total.status.value,
            "metrics": asdict(side.total.metrics) if side.total.metrics is not None else None,
            "residuals_deg": list(side.total.residuals),
            "message": side.total.message,
        },
        "incremental": {
            "status": side.incremental.status.value,
            "metrics": (
                asdict(side.incremental.metrics)
                if side.incremental.metrics is not None
                else None
            ),
            "residuals_deg": list(side.incremental.residuals),
            "message": side.incremental.message,
        },
    }


def _residual_summary(inputs_deg: list[float], comparison: dict) -> dict:
    residuals = comparison["residuals_deg"]
    maximum_index = max(range(len(residuals)), key=lambda index: abs(residuals[index]))
    samples: dict[str, float] = {}
    for sample_input in SUMMARY_SAMPLE_INPUTS_DEG:
        sample_index = inputs_deg.index(sample_input)
        samples[f"{sample_input:g}"] = residuals[sample_index]
    return {
        "status": comparison["status"],
        "metrics": comparison["metrics"],
        "maximum_absolute_residual_input_deg": inputs_deg[maximum_index],
        "signed_residual_at_maximum_deg": residuals[maximum_index],
        "selected_residuals_deg": samples,
    }


def _summary_report(report: dict) -> dict:
    inputs_deg = [
        float(value)
        for value in range(
            int(report["source_input_domain_deg"][0]),
            int(report["source_input_domain_deg"][1]) + 1,
        )
    ]
    summary = {
        "geometry_id": report["geometry_id"],
        "geometry_version": report["geometry_version"],
        "authorization_id": report["authorization_id"],
        "reference_fit": report["reference_fit"],
        "sample_count": report["sample_count"],
        "source_input_domain_deg": report["source_input_domain_deg"],
        "rack_metres_per_input_degree": report["rack_metres_per_input_degree"],
        "adapter": report["adapter"],
        "comparison_status": report["comparison_status"],
        "acceptance_status": report["acceptance_status"],
        "authority_boundary": report["authority_boundary"],
    }
    for side_name in ("left", "right"):
        side = report[side_name]
        summary[side_name] = {
            "canonical_static_deg": side["canonical_static_deg"],
            "historical_static_deg": side["historical_static_deg"],
            "static_difference_deg": side["static_difference_deg"],
            "total": _residual_summary(inputs_deg, side["total"]),
            "incremental": _residual_summary(inputs_deg, side["incremental"]),
        }
    return summary


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    geometry = load_geometry(root / "configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml")
    fits = load_wheel_angle_fits(
        root / "benchmarks/steering/wufr26_desmos_wheel_angle_fits.toml"
    )
    source_inputs_deg = tuple(
        float(value) for value in range(SOURCE_INPUT_MIN_DEG, SOURCE_INPUT_MAX_DEG + 1)
    )
    result = compare_wufr26_projected_heading(
        geometry,
        fits["test3"],
        source_inputs_deg,
        rack_metres_per_input_degree=RACK_TRAVEL_M_PER_INPUT_DEG,
    )

    return {
        "geometry_id": geometry.geometry_id,
        "geometry_version": geometry.version,
        "authorization_id": "AUTH-STEER-0001",
        "reference_fit": "test3",
        "sample_count": len(source_inputs_deg),
        "source_input_domain_deg": [source_inputs_deg[0], source_inputs_deg[-1]],
        "rack_metres_per_input_degree": RACK_TRAVEL_M_PER_INPUT_DEG,
        "adapter": asdict(result.adapter),
        "left": _side_report(result.left),
        "right": _side_report(result.right),
        "comparison_status": "numerical_design_source_comparison_available",
        "acceptance_status": "pending_residual_review_and_tolerance_freeze",
        "authority_boundary": (
            "Cross-tool nominal design evidence only; not independent validation or an as-built claim"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print metrics, extrema, and selected residuals instead of all 205 residuals.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optionally write the selected JSON payload to this path.",
    )
    arguments = parser.parse_args()

    report = build_report()
    payload = _summary_report(report) if arguments.summary else report
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
