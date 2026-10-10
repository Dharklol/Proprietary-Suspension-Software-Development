#!/usr/bin/env python3
"""Verify the provider-neutral development kernel and report synthetic branches.

No WUFR operating case, real tire domain or native geometry validation is implied.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pssd_vehicle.steady_cornering import continue_cornering
from tests.steady_cornering_fixture import case, config, geometry, initial, tire


def run_benchmarks() -> dict:
    suite = unittest.defaultTestLoader.loadTestsFromNames(
        ("tests.test_steady_cornering_motion", "tests.test_steady_cornering"))
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    runs = []
    for sign in (-1, 1):
        cases = tuple(case(sign*k, state_id=f"synthetic_{sign}_{k}") for k in (0., .005, .01, .02))
        branch = continue_cornering(cases, initial(), branch_id=f"synthetic_curvature_sign_{sign}",
                                    geometry_provider=geometry, tire_provider=tire, config=config())
        samples = []
        for result in branch.results:
            ev = result.evaluation
            samples.append({
                "ok": result.ok, "case": asdict(result.case), "coordinates": result.coordinates,
                "result_label": result.result_label, "failure_code": result.failure_code,
                "message": result.message, "iterations": result.iterations,
                "scaled_residual_norm": result.scaled_residual_norm,
                "reciprocal_pivot_ratio": result.reciprocal_pivot_ratio,
                "residual_history": result.residual_history, "trial_failures": result.trial_failures,
                "motion": asdict(ev.motion) if ev else None,
                "holder": asdict(ev.holder) if ev else None,
                "inertia": asdict(ev.inertia) if ev else None,
                "geometry": asdict(ev.geometry) if ev else None,
                "tires": [asdict(t) for t in ev.tires] if ev else None,
                "physical_wrench": asdict(ev.physical_wrench) if ev else None,
                "physical_force_norm_n": math.hypot(*ev.physical_wrench.resultant_force_N) if ev else None,
                "physical_moment_norm_nm": math.hypot(*ev.physical_wrench.resultant_moment_Nm) if ev else None,
            })
        runs.append({"branch_id": branch.branch_id, "complete": branch.complete, "samples": samples})
    files = ("src/pssd_vehicle/steady_cornering.py", "src/pssd_vehicle/steady_cornering_motion.py",
             "tests/steady_cornering_fixture.py", "tests/test_steady_cornering.py",
             "tests/test_steady_cornering_motion.py")
    samples = [sample for run in runs for sample in run["samples"]]
    return {
        "record_id": "STEADY_CORNERING_DEVELOPMENT_SYNTHETIC_V1",
        "authorization_id": "AUTH-VEH-0012", "model_id": "MOD-VEH-0009",
        "benchmark_ids": ["BENCH-VEH-0018", "BENCH-VEH-0019", "BENCH-VEH-0020"],
        "scope": "provider_neutral_synthetic_kernel_only",
        "status": "pass" if tests.wasSuccessful() and all(run["complete"] for run in runs) else "fail",
        "source_hashes": {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in files},
        "tests": {"count": tests.testsRun, "successful": tests.wasSuccessful(), "log": log.getvalue()},
        "summary": {
            "sample_count": len(samples),
            "maximum_force_norm_n": max(s["physical_force_norm_n"] for s in samples),
            "maximum_moment_norm_nm": max(s["physical_moment_norm_nm"] for s in samples),
            "force_limit_n": 1e-6, "moment_limit_nm": 1e-6,
            "native_wufr_integration_verified": False, "real_tire_domain_verified": False,
            "predictive_or_setup_authority": False,
        },
        "branches": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_benchmarks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"status": report["status"], "tests": report["tests"]["count"],
                      **report["summary"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
