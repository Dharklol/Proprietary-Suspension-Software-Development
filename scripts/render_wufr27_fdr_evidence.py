#!/usr/bin/env python3
"""Regenerate source-labeled WUFR-27 nominal FDR steering performance figures.

Accepts ONLY the independent nominal WUFR-27 prescribed-torque JSON report.
This is an engineering design-source comparison and NOT physical correlation,
tire aligning-moment prediction, installed rack travel or structural approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


EXPECTED_REPORT = "WUFR27_NOMINAL_DESIGN_SOURCE_COMPLIANCE_V1"
EXPECTED_ROLE = "nominal_design_source_not_installed_or_as_built"
LABELS = {
    "zero_torque_rigid_baseline": "0 N m (rigid baseline)",
    "calculated_cornering_column_moment": "14.444 N m: cornering",
    "calculated_unfactored_parked_column_moment": "23.698 N m: parked, unfactored",
    "calculated_factored_parked_column_moment": "35.547 N m: parked, factored",
}
PHYSICAL_DISCLAIMER = (
    "Nominal design-source / prescribed calculated column torque, not "
    "measured as-built response or tire aligning moment"
)


def load_source(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        source = json.load(f)
    if source.get("report") != EXPECTED_REPORT or source.get("evidence_role") != EXPECTED_ROLE:
        raise ValueError("Unsupported steering evidence source or authority")
    if source.get("geometry_id") != "WUFR27_STEERING_BASELINE_V0":
        raise ValueError("Unexpected nominal steering geometry ID")
    if source.get("source_parameter_id") != "PAR-STEER-0001":
        raise ValueError("Missing approved design-source transmission identity")
    rows = source.get("states", [])
    if len(rows) != 36:
        raise ValueError("Expected four source load cases at nine commanded positions")
    for label in LABELS:
        group = [x for x in rows if x.get("load_scenario") == label]
        if len(group) != 9 or sorted(x["driver_command_deg"] for x in group) != (
            [-100.0, -75.0, -50.0, -25.0, 0.0, 25.0, 50.0, 75.0, 100.0]
        ):
            raise ValueError("Missing or incomplete prescribed load-case group")
    for row in rows:
        if not row["rigid_and_loaded_closure_valid"]:
            raise ValueError("Cannot plot invalid mechanism branch")
        for k in (
            "free_span_elastic_twist_deg", "rigid_rack_mm", "loaded_rack_mm",
            "left_rigid_incremental_deg", "left_loaded_incremental_deg",
            "right_rigid_incremental_deg", "right_loaded_incremental_deg",
            "left_loaded_minus_rigid_incremental_deg",
            "right_loaded_minus_rigid_incremental_deg",
        ):
            if row.get(k) is None or not math.isfinite(row[k]):
                raise ValueError(f"Unavailable or nonfinite source value: {k}")
        if row["left_unavailable_reason"] or row["right_unavailable_reason"]:
            raise ValueError("Wheel heading reported unavailable")
    return source


def grouped(rows: list[dict], name: str) -> list[dict]:
    return sorted(
        (r for r in rows if r["load_scenario"] == name),
        key=lambda x: x["driver_command_deg"],
    )


def finish(fig, path: Path) -> None:
    fig.text(0.5, 0.005, PHYSICAL_DISCLAIMER, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .055, 1, 1))
    fig.savefig(path, dpi=175)
    plt.close(fig)


def build_figures(source: dict, outdir: Path) -> list[Path]:
    rows = source["states"]
    outdir.mkdir(parents=True, exist_ok=True)
    output = []

    # 1: Both sides, projected heading from wheel-plane normal, not the folded
    # historical SolidWorks Dimension2 or simple upright rotation.
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.1), sharex=True)
    zero = grouped(rows, "zero_torque_rigid_baseline")
    for ax, side in zip(axs, ("left", "right")):
        x = [r["driver_command_deg"] for r in zero]
        ax.plot(x, [r[f"{side}_rigid_incremental_deg"] for r in zero],
                "k-o", linewidth=2, label="Rigid / 0 N m")
        for label in list(LABELS)[1:]:
            items = grouped(rows, label)
            ax.plot(x, [r[f"{side}_loaded_incremental_deg"] for r in items],
                    "-o", linewidth=1.3, markersize=3, label=LABELS[label])
        ax.set_title(f"{side.title()} projected incremental heading")
        ax.set_xlabel("Commanded design-study steering input (deg)")
        ax.set_ylabel("Road-wheel heading from centered datum (deg)")
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
    fig.suptitle("WUFR-27 nominal geometry — rigid versus prescribed elastic column twist")
    p = outdir / "FDR01_wufr27_nominal_rigid_loaded_wheel_headings.png"
    finish(fig, p)
    output.append(p)

    # 2: Explicit comparison delta is more useful than multiple overlaid
    # steering curves and does not conflate free play with elastic deflection.
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.9), sharex=True)
    for ax, side in zip(axs, ("left", "right")):
        for label in list(LABELS)[1:]:
            items = grouped(rows, label)
            ax.plot([r["driver_command_deg"] for r in items],
                    [r[f"{side}_loaded_minus_rigid_incremental_deg"]
                     for r in items], "-o", label=LABELS[label], markersize=4)
        ax.axhline(0.0, linewidth=.75, linestyle="--")
        ax.set_title(f"{side.title()} wheel: loaded minus rigid")
        ax.set_xlabel("Commanded design-study steering input (deg)")
        ax.set_ylabel("Incremental wheel-angle change (deg)")
        ax.grid(alpha=.25)
        ax.legend(fontsize=8)
    fig.suptitle("WUFR-27 nominal projected-heading sensitivity to assumed shaft torsion")
    p = outdir / "FDR02_wufr27_nominal_loaded_minus_rigid.png"
    finish(fig, p)
    output.append(p)

    # 3: Separate input-side elastic compliance from mechanical free play.
    fig, ax = plt.subplots(figsize=(8.5, 5))
    cases = []
    for label in LABELS:
        point = next(r for r in grouped(rows, label) if r["driver_command_deg"] == 25)
        cases.append((abs(point["prescribed_input_torque_nm"]),
                      point["free_span_elastic_twist_deg"]))
    cases.sort()
    ax.plot([a for a, _ in cases], [b for _, b in cases], "-o")
    for a, b in cases:
        ax.annotate(f"({a:.2f}, {b:.3f})", (a, b), xytext=(6, 7),
                    textcoords="offset points", fontsize=8)
    ax.set_xlabel("Prescribed input/column torque magnitude (N m)")
    ax.set_ylabel("Four circular free-span elastic twist (deg)")
    ax.set_title("WUFR-27 provisional column torsion (G = 80 GPa, nominal 1:1)")
    ax.grid(alpha=.25)
    p = outdir / "FDR03_wufr27_free_span_elastic_twist.png"
    finish(fig, p)
    output.append(p)

    # 4: The transmission itself, preserving canonical +y rack sign.
    fig, ax = plt.subplots(figsize=(8.5, 5.3))
    ax.plot([r["driver_command_deg"] for r in zero],
            [r["rigid_rack_mm"] for r in zero],
            "k-o", linewidth=2, label="Rigid design-source 3.5 in/rev")
    for label in list(LABELS)[1:]:
        items = grouped(rows, label)
        ax.plot([r["driver_command_deg"] for r in items],
                [r["loaded_rack_mm"] for r in items],
                "-o", markersize=3, label=LABELS[label])
    ax.set_xlabel("Commanded design-study steering input (deg)")
    ax.set_ylabel("Signed canonical +y rack displacement (mm)")
    ax.set_title("WUFR-27 nominal rack-input map, before and after free-span torsion")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8)
    p = outdir / "FDR04_wufr27_nominal_rack_displacement.png"
    finish(fig, p)
    output.append(p)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    source = load_source(args.report)
    files = build_figures(source, args.outdir)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "report": EXPECTED_REPORT,
        "authority": EXPECTED_ROLE,
        "source_parameter": source["source_parameter_id"],
        "source_geometry": source["geometry_id"],
        "source_json_sha256": digest(args.report),
        "git_sha": os.environ.get("GITHUB_SHA", "local_unrecorded"),
        "normalization": "source-radians / degrees, rack m -> mm",
        "physical_correlation": False,
        "caveat": PHYSICAL_DISCLAIMER,
        "figures": [{ "name": f.name, "sha256": digest(f) } for f in files],
    }
    (args.outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"generated {len(files)} figures and manifest in {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
