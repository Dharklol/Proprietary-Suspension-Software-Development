from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_suspension.rocker_included_load import RockerPointLoad, evaluate_rocker_included_load


def _vector(values):
    return [float(value) for value in values]


def build_report() -> dict:
    frame = "BENCH-SUSP-0026_FRAME"
    configuration = "BENCH-SUSP-0026_CONFIG"
    load_case = "BENCH-SUSP-0026_CASE"
    loads = (
        RockerPointLoad("one", (0.4, -0.2, 0.3), (10.0, 20.0, -5.0), "HAND_ONE", frame, configuration, load_case),
        RockerPointLoad("two", (0.1, 0.2, 0.3), (-4.0, 3.0, 8.0), "HAND_TWO", frame, configuration, load_case),
        RockerPointLoad("three", (0.1, -0.2, 0.8), (2.0, -6.0, 1.0), "HAND_THREE", frame, configuration, load_case),
    )
    result = evaluate_rocker_included_load(
        rocker_pivot_m=(0.1, -0.2, 0.3),
        rocker_axis=(0.0, 0.0, 2.0),
        loads=loads,
        missing_load_ids=("not_modeled",),
        frame_id=frame,
        configuration_id=configuration,
        load_case_id=load_case,
    )
    if not result.ok:
        raise RuntimeError(result.message)
    return {
        "version": "0.1.0",
        "benchmark_ids": ["BENCH-SUSP-0026", "BENCH-SUSP-0027"],
        "authorization_id": "AUTH-SUSP-0016",
        "status": "pass",
        "complete_hardware_reaction": result.complete_hardware_reaction,
        "included_load_ids": list(result.included_load_ids),
        "missing_load_ids": list(result.missing_load_ids),
        "included_resultant_force_N": _vector(result.included_resultant_force_N),
        "included_resultant_moment_Nm": _vector(result.included_resultant_moment_Nm),
        "pivot_force_contribution_N": _vector(result.pivot_force_contribution_N),
        "pivot_moment_contribution_Nm": _vector(result.pivot_moment_contribution_Nm),
        "free_axis_moment_residual_Nm": result.free_axis_moment_residual_Nm,
        "final_force_residual_N": _vector(result.final_force_residual_N),
        "final_moment_residual_Nm": _vector(result.final_moment_residual_Nm),
        "perpendicular_moment_residual_Nm": _vector(result.perpendicular_moment_residual_Nm),
        "support_axis_moment_component_Nm": result.support_axis_moment_component_Nm,
        "force_residual_inf_norm_N": result.force_residual_inf_norm_N,
        "perpendicular_moment_residual_inf_norm_Nm": result.perpendicular_moment_residual_inf_norm_Nm,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("rocker_included_load_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        print(
            f"status={report['status']} tau_axis={report['free_axis_moment_residual_Nm']:.6g} "
            f"complete={report['complete_hardware_reaction']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
