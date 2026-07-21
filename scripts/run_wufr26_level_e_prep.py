#!/usr/bin/env python3
"""Generate the WUFR-26 canonical projected-heading Level E comparison."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from pssd_steering import load_geometry, load_wheel_angle_fits
from pssd_steering.level_e import compare_wufr26_projected_heading

SOURCE_INPUT_MIN_DEG = -102
SOURCE_INPUT_MAX_DEG = 102
RACK_TRAVEL_IN_PER_REV = 3.5
RACK_TRAVEL_M_PER_INPUT_DEG = RACK_TRAVEL_IN_PER_REV * 0.0254 / 360.0


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


def main() -> int:
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

    report = {
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
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
