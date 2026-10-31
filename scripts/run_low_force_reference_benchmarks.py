#!/usr/bin/env python3
"""Compare coupled four-wheel trim with independent manufactured small-angle limits."""
from dataclasses import asdict
from functools import lru_cache
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.low_force_reference_fixture import (
    AXLE_STIFFNESSES_N_PER_RAD, CURVATURE_STEPS_PER_M, RACK_GAIN_RAD_PER_M, SPEEDS_M_S,
    reference_inputs, single_track_reference, solve_reference_case, straight_reference,
)

# Predeclared verification limits; not native-vehicle accuracy bounds.
GRADIENT_NORMALIZED_ERROR_LIMIT = 2e-5
CONVERGENCE_FLOOR = 1e-7
CONVERGENCE_RATIO_LIMIT = .6
PHYSICAL_LIMIT = 1e-6


def _sample(result):
    ev = result.evaluation
    return {'ok': result.ok, 'failure_code': result.failure_code, 'message': result.message,
        'case': asdict(result.case), 'coordinates': result.coordinates,
        'physical_force_norm_n': math.hypot(*ev.physical_wrench.resultant_force_N) if ev else None,
        'physical_moment_norm_nm': math.hypot(*ev.physical_wrench.resultant_moment_Nm) if ev else None,
        'lateral_forces_n': [t.lateral_force_n for t in ev.tires] if ev else None,
        'iterations': result.iterations, 'scaled_residual_norm': result.scaled_residual_norm,
        'reciprocal_pivot_ratio': result.reciprocal_pivot_ratio,
        'result_role': 'evidence_only', 'objective_weight': 0.}


@lru_cache(maxsize=1)
def build_report():
    records = []
    for label, cf, cr in AXLE_STIFFNESSES_N_PER_RAD:
        for speed in SPEEDS_M_S:
            inputs = reference_inputs(speed, cf, cr)
            analytical = single_track_reference(**inputs)
            straight = solve_reference_case(speed=speed, curvature=0.,
                front_stiffness=cf, rear_stiffness=cr)
            record = {'fixture': label, 'inputs': inputs, 'analytical': analytical,
                      'straight': _sample(straight), 'steps': [], 'passed': False}
            records.append(record)
            if not straight.ok:
                continue
            expected = straight_reference(straight.case.gravity_m_s2)
            x = straight.coordinates
            straight_ok = (abs(x[0]-expected['heave_m']) <= 1e-8
                and max(abs(v) for v in x[1:6]) <= 1e-7
                and max(abs(v-expected['normal_load_n']) for v in x[6:]) <= PHYSICAL_LIMIT
                and max(abs(t.lateral_force_n) for t in straight.evaluation.tires) <= PHYSICAL_LIMIT)
            record['straight_analytical'] = expected
            record['straight_passed'] = straight_ok
            for kappa in CURVATURE_STEPS_PER_M:
                pair = [solve_reference_case(speed=speed, curvature=sign*kappa,
                    front_stiffness=cf, rear_stiffness=cr, guess=straight.coordinates)
                    for sign in (-1, 1)]
                step = {'curvature_step_per_m': kappa, 'samples': [_sample(r) for r in pair],
                        'passed': False}
                record['steps'].append(step)
                if not all(r.ok for r in pair):
                    continue
                minus, plus = pair
                measured = {
                    'steer_per_curvature_m': RACK_GAIN_RAD_PER_M*(plus.coordinates[4]-minus.coordinates[4])/(2*kappa),
                    'sideslip_per_curvature_m': (plus.coordinates[3]-minus.coordinates[3])/(2*kappa),
                    'front_force_per_curvature_nm':
                        (sum(t.lateral_force_n for t in plus.evaluation.tires[:2])-
                         sum(t.lateral_force_n for t in minus.evaluation.tires[:2]))/(2*kappa),
                    'rear_force_per_curvature_nm':
                        (sum(t.lateral_force_n for t in plus.evaluation.tires[2:])-
                         sum(t.lateral_force_n for t in minus.evaluation.tires[2:]))/(2*kappa)}
                errors = {key: abs(value-analytical[key])/max(1.,abs(analytical[key]))
                          for key, value in measured.items()}
                physical_ok = all(s['physical_force_norm_n'] <= PHYSICAL_LIMIT
                    and s['physical_moment_norm_nm'] <= PHYSICAL_LIMIT for s in step['samples'])
                step.update({'measured': measured, 'normalized_errors': errors,
                    'maximum_normalized_error': max(errors.values()), 'passed': physical_ok})
            complete = len(record['steps']) == len(CURVATURE_STEPS_PER_M) and all(
                step['passed'] for step in record['steps'])
            if complete:
                # Each response must refine or already be below the declared numerical floor.
                converges = all(fine['normalized_errors'][key] <= max(CONVERGENCE_FLOOR,
                    CONVERGENCE_RATIO_LIMIT*coarse['normalized_errors'][key])
                    for coarse, fine in zip(record['steps'],record['steps'][1:])
                    for key in fine['normalized_errors'])
                record['convergence_passed'] = converges
                record['passed'] = (straight_ok and converges and
                    record['steps'][-1]['maximum_normalized_error'] <= GRADIENT_NORMALIZED_ERROR_LIMIT)
    paths = ('scripts/run_low_force_reference_benchmarks.py', 'tests/low_force_reference_fixture.py',
             'tests/test_low_force_reference.py', 'tests/steady_cornering_fixture.py',
             'src/pssd_vehicle/steady_cornering.py', 'src/pssd_vehicle/steady_cornering_motion.py')
    return {'status': 'pass' if all(r['passed'] for r in records) else 'fail',
        'scope': 'manufactured_small_angle_single_track_limit_only',
        'limits': {'gradient_normalized_error': GRADIENT_NORMALIZED_ERROR_LIMIT,
            'convergence_floor': CONVERGENCE_FLOOR, 'convergence_ratio': CONVERGENCE_RATIO_LIMIT,
            'physical_force_n': PHYSICAL_LIMIT, 'physical_moment_nm': PHYSICAL_LIMIT},
        'case_count': sum(1+sum(len(s['samples']) for s in r['steps']) for r in records),
        'fixture_count': len(records), 'fixtures': records,
        'source_hashes': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'native_tire_or_vehicle_validation': False, 'design_ranking_permitted': False,
        'objective_weight': 0.}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary-output', type=Path)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    if args.summary_output is not None:
        summary = {key: value for key, value in report.items() if key != 'fixtures'}
        summary['fixtures'] = [{key: value for key, value in record.items()
            if key not in ('straight','steps')} | {'steps': [
                {key: value for key, value in step.items() if key != 'samples'}
                for step in record['steps']]} for record in report['fixtures']]
        samples = [r['straight'] for r in report['fixtures']]+[
            sample for r in report['fixtures'] for step in r['steps'] for sample in step['samples']]
        summary['maximum_physical_force_norm_n'] = max(
            (s['physical_force_norm_n'] for s in samples if s['physical_force_norm_n'] is not None),default=None)
        summary['maximum_physical_moment_norm_nm'] = max(
            (s['physical_moment_norm_nm'] for s in samples if s['physical_moment_norm_nm'] is not None),default=None)
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status': report['status'], 'case_count': report['case_count'],
        'fixtures': [{'fixture': r['fixture'], 'speed': r['inputs']['speed_m_s'],
            'passed': r['passed'], 'errors': [s.get('maximum_normalized_error') for s in r['steps']]}
            for r in report['fixtures']]}, indent=2))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
