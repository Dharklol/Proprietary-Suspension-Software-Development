#!/usr/bin/env python3
"""Verify native per-state steering replay without publishing optimizer targets."""
from dataclasses import asdict
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pssd_steering.optimization.varying_state_evidence import consume_native_steering_evidence
from tests.varying_state_evidence_fixture import bundle, series
from tests.wufr_cornering_fixture import solver_config


def run_evidence():
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_varying_state_steering_evidence')
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    geometry, tire, native = bundle()
    packets = series(tuple((branch, slot) for branch in range(2) for slot in range(4)))
    result = consume_native_steering_evidence(packets, geometry_provider=geometry,
                                            tire_provider=tire, solver_config=solver_config())
    samples = []
    heading_errors, force_errors, center_errors = [], [], []
    for sample in result.samples:
        original = sample.packet.equilibrium.evaluation
        fronts = []
        for i, wheel in enumerate(sample.front_wheels):
            force_error = abs(wheel.forward_response.lateral_force_n-original.tires[i].lateral_force_n)
            center_error = math.dist(wheel.center_heading_m, original.geometry.wheels[i].center.point.position_m)
            matched_error = max((abs(wheel.inverse.roots[j].required_heading_rad-wheel.wheel_heading_rad)
                                 for j in wheel.observed_root_indices), default=None)
            force_errors.append(force_error)
            center_errors.append(center_error)
            if matched_error is not None:
                heading_errors.append(matched_error)
            fronts.append({'corner_id': wheel.corner_id, 'center_heading_m': wheel.center_heading_m,
                'wheel_heading_rad': wheel.wheel_heading_rad, 'velocity_heading_rad': wheel.velocity_heading_rad,
                'slip_angle_rad': wheel.slip_angle_rad, 'inclination_rad': wheel.inclination_rad,
                'normal_load_n': wheel.forward_response.query.normal_load_n,
                'pressure_pa': wheel.forward_response.query.pressure_pa,
                'lateral_force_n': wheel.forward_response.lateral_force_n,
                'reflected': wheel.inverse.reflected, 'all_root_count': len(wheel.inverse.roots),
                'observed_root_indices': wheel.observed_root_indices,
                'all_required_headings_rad': [root.required_heading_rad for root in wheel.inverse.roots],
                'root_selection_applied': wheel.inverse.source_result.branch_selection_applied,
                'forward_force_error_n': force_error, 'center_error_m': center_error,
                'matched_heading_error_rad': matched_error})
        samples.append({'sample_id': sample.sample_id, 'ok': sample.ok, 'failure_code': sample.failure_code,
            'message': sample.message, 'state_id': sample.packet.equilibrium.case.state_id,
            'curvature_per_m': sample.packet.equilibrium.case.curvature_per_m,
            'rack_displacement_m': sample.packet.sample.rack_displacement_m,
            'body_coordinates': sample.packet.equilibrium.coordinates[:3],
            'role': sample.result_role, 'objective_weight': sample.objective_weight, 'front_wheels': fronts})
    passed = tests.wasSuccessful() and result.complete and len(samples) == 8 and len(force_errors) == 16
    native_path = 'benchmarks/vehicle/wufr_steady_cornering_native_development_v0.1.0.json'
    source_paths = ('src/pssd_steering/optimization/varying_state_evidence.py',
        'tests/test_varying_state_steering_evidence.py', 'tests/varying_state_evidence_fixture.py',
        'scripts/run_varying_state_steering_evidence.py', 'src/pssd_vehicle/steady_cornering_export.py')
    summary = {'status': 'pass' if passed else 'fail', 'scope': 'native_baseline_varying_state_steering_evidence_only',
        'tests': {'count': tests.testsRun, 'successful': tests.wasSuccessful()},
        'sample_count': len(samples), 'front_wheel_replay_count': len(force_errors),
        'maximum_forward_force_error_n': max(force_errors, default=None),
        'maximum_center_error_m': max(center_errors, default=None),
        'maximum_observed_heading_error_rad': max(heading_errors, default=None),
        'source_hashes': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
        'native_input_evidence_sha256': hashlib.sha256((ROOT/native_path).read_bytes()).hexdigest(),
        'geometry_revision': geometry.geometry_revision, 'setup_revision': geometry.setup_revision,
        'tire_revision': tire.tire_revision, 'optimizer_target_publication_permitted': False,
        'design_ranking_or_setup_authority': False, 'samples': samples}
    report = {'summary': summary, 'tests_log': log.getvalue(), 'evidence': asdict(result)}
    return report, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary-output', type=Path, required=True)
    args = parser.parse_args()
    report, summary = run_evidence()
    for path, data in ((args.output, report), (args.summary_output, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('samples', 'source_hashes')}, indent=2))
    return 0 if summary['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
