#!/usr/bin/env python3
"""Generate BENCH-STEER-0022 processed-TTC branch-export diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import tomllib

from pssd_tire import (
    TireDataError,
    TireOperatingPoint,
    format_lateral_force_branch_set_toml,
    load_lateral_force_branch_set,
)
from pssd_tire.ttc_cornering import (
    WUFR26_APRIL_CORNERING_TROJAN_V0,
    build_branch_set,
    export_cornering_trojan_branch,
)


def _synthetic_channels(*, nonmonotonic: bool = False) -> dict[str, tuple[float, ...]]:
    sa = (-6.0, -4.0, -2.0, -0.5, 0.5, 2.0, 4.0, 6.0)
    fy_inside = (900.0, 800.0, 500.0, 150.0, -150.0, -500.0, -800.0, -900.0)
    if nonmonotonic:
        fy_inside = (900.0, 480.0, 500.0, 150.0, -150.0, -500.0, -800.0, -900.0)
    fy_outside = (2100.0, 1900.0, 1300.0, 350.0, -350.0, -1300.0, -1900.0, -2100.0)
    return {
        "SA": sa + sa,
        "FY": fy_inside + fy_outside,
        "FZ": (222.0,) * len(sa) + (1112.0,) * len(sa),
        "IA": (0.0,) * len(sa) + (2.0,) * len(sa),
        "P": (82.7,) * (2 * len(sa)),
        "SL": (0.0,) * (2 * len(sa)),
        "V": (40.2,) * (2 * len(sa)),
    }


def _audit_dict(audit) -> dict:
    return {
        "profile_id": audit.profile_id,
        "total_source_rows": audit.total_source_rows,
        "operating_point_rows": audit.operating_point_rows,
        "selected_quadrant_rows": audit.selected_quadrant_rows,
        "prepeak_rows": audit.prepeak_rows,
        "source_peak_slip_angle_deg": audit.source_peak_slip_angle_deg,
        "source_peak_lateral_force_n": audit.source_peak_lateral_force_n,
        "minimum_exported_slip_angle_deg": audit.minimum_exported_slip_angle_deg,
        "minimum_exported_lateral_force_n": audit.minimum_exported_lateral_force_n,
        "maximum_exported_slip_angle_deg": audit.maximum_exported_slip_angle_deg,
        "maximum_exported_lateral_force_n": audit.maximum_exported_lateral_force_n,
    }


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    profile_path = root / "benchmarks/tires/WUFR26_H43105_R25B_CORNERING_TROJAN_EXPORT_PROFILE_V0.toml"
    with profile_path.open("rb") as stream:
        profile_record = tomllib.load(stream)

    channels = _synthetic_channels()
    inside = export_cornering_trojan_branch(
        channels,
        TireOperatingPoint(222.0, 0.0, 82.7),
        branch_id="synthetic_inside",
        authority="BENCH-STEER-0022 synthetic software evidence only",
        source_branch_description="synthetic Trojan-shaped inside branch",
    )
    outside = export_cornering_trojan_branch(
        channels,
        TireOperatingPoint(1112.0, 2.0, 82.7),
        branch_id="synthetic_outside",
        authority="BENCH-STEER-0022 synthetic software evidence only",
        source_branch_description="synthetic Trojan-shaped outside branch",
    )
    branch_set = build_branch_set(
        (inside, outside),
        branch_set_id="BENCH_STEER_0022_SYNTHETIC_BRANCH_SET",
        version="0.1.0",
        source_tire_id="SYNTHETIC_TROJAN_SHAPED_SOURCE",
        intended_tire_id="SYNTHETIC_TROJAN_SHAPED_INTENDED",
        authority="software_verification_only",
        source_path="generated_in_benchmark",
    )
    rendered = format_lateral_force_branch_set_toml(branch_set)
    with tempfile.TemporaryDirectory() as directory:
        roundtrip_path = Path(directory) / "roundtrip.toml"
        roundtrip_path.write_text(rendered, encoding="utf-8")
        roundtrip = load_lateral_force_branch_set(roundtrip_path)

    missing_state_rejected = False
    nonmonotonic_rejected = False
    try:
        export_cornering_trojan_branch(
            channels,
            TireOperatingPoint(500.0, 1.0, 82.7),
            branch_id="missing",
            authority="synthetic",
            source_branch_description="missing",
        )
    except TireDataError:
        missing_state_rejected = True
    try:
        export_cornering_trojan_branch(
            _synthetic_channels(nonmonotonic=True),
            TireOperatingPoint(222.0, 0.0, 82.7),
            branch_id="nonmonotonic",
            authority="synthetic",
            source_branch_description="nonmonotonic",
        )
    except TireDataError:
        nonmonotonic_rejected = True

    source = profile_record["source"]
    python_exporter = profile_record["python_exporter"]
    return {
        "benchmark_id": "BENCH-STEER-0022",
        "authority": "software composition and source-profile freeze only; no real R25B intermediate force values are generated in CI",
        "source_profile": {
            "profile_id": profile_record["profile_id"],
            "source_tire_id": profile_record["source_tire_id"],
            "intended_tire_id": profile_record["intended_tire_id"],
            "cornering_trojan_file_id": source["cornering_trojan_file_id"],
            "cornering_trojan_sha1": source["cornering_trojan_sha1"],
            "raw_cornering_run_21_sha1": source["raw_cornering_run_21_sha1"],
            "raw_cornering_run_22_sha1": source["raw_cornering_run_22_sha1"],
            "april_interpolator_sha1": source["april_interpolator_sha1"],
            "fitted_tir_sha1": source["fitted_tir_sha1"],
            "profile_constant": python_exporter["profile_constant"],
            "track_scale_applied": python_exporter["track_scale_applied"],
        },
        "synthetic_export": {
            "physical_tire_claim": False,
            "inside": _audit_dict(inside.audit),
            "outside": _audit_dict(outside.audit),
            "roundtrip_branch_count": len(roundtrip.branches),
            "roundtrip_inside_samples": len(roundtrip.branches[0].samples),
            "roundtrip_outside_samples": len(roundtrip.branches[1].samples),
        },
        "failure_paths": {
            "missing_exact_operating_point_rejected": missing_state_rejected,
            "nonmonotonic_prepeak_source_rejected": nonmonotonic_rejected,
        },
        "real_source_status": {
            "binary_source_committed_to_repository": False,
            "real_branch_table_frozen": False,
            "next_action": "Run scripts/export_r25b_cornering_force_branches.py against the hashed Box Cornering Trojan MAT source, then review peak cross-checks and promote only accepted branches.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("r25b_force_branch_export_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        source = report["source_profile"]
        synthetic = report["synthetic_export"]
        failures = report["failure_paths"]
        print(
            "BENCH-STEER-0022: "
            f"profile={source['profile_id']}, "
            f"inside_points={synthetic['inside']['prepeak_rows']}, "
            f"outside_points={synthetic['outside']['prepeak_rows']}, "
            f"missing_state_rejected={failures['missing_exact_operating_point_rejected']}, "
            f"nonmonotonic_rejected={failures['nonmonotonic_prepeak_source_rejected']}, "
            "real_branch_frozen=false"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
