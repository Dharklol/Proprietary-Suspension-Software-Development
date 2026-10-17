#!/usr/bin/env python3
"""Reproduce native-source development fixtures; no user setup defaults."""
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

from pssd_vehicle.steady_cornering import continue_cornering
from pssd_vehicle.steady_cornering_tire import SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY
from tests.wufr_cornering_fixture import providers, case, initial, solver_config


SOURCE_FILES = (
    'src/pssd_vehicle/wufr_steady_cornering_geometry.py',
    'src/pssd_vehicle/steady_cornering_upright.py',
    'src/pssd_vehicle/steady_cornering_tire.py',
    'src/pssd_vehicle/steady_cornering.py',
    'src/pssd_vehicle/steady_cornering_motion.py',
    'tests/wufr_cornering_fixture.py',
    'tests/test_wufr_steady_cornering_geometry.py',
    'tests/test_steady_cornering_tire.py',
    'tests/test_steady_cornering_upright.py',
    'scripts/run_wufr_steady_cornering_benchmarks.py',
    'data_catalog/wufr27_static_equilibrium_composition_v1.toml',
    'data_catalog/wufr26_road_contact_reference_v0.toml',
    'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',
    'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml',
    'configurations/steering/WUFR27_STEERING_BASELINE_V0.toml',
    'configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml',
    'data_catalog/wufr26_whole_vehicle_frame_v0.toml',
    'data_catalog/wufr27_static_gravity_allocation_v0.toml',
    'data_catalog/wufr27_spring_package_v0.toml',
    'benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml',
    'authorizations/vehicle/AUTH-VEH-0012.toml',
    'registry/records/assumptions/ASM-VEH-0009.toml',
)


def _sample(result):
    record = asdict(result)
    if result.evaluation is None:
        return record
    for tire in record['evaluation']['tires']:
        evidence = {}
        source_ids = []
        for value in tire['source_ids']:
            key, _, payload = value.partition(':')
            if key in ('requested_query', 'source_response', 'source_segment_labels'):
                evidence[key] = json.loads(payload)
            else:
                source_ids.append(value)
        tire['source_ids'] = source_ids
        tire['lookup_evidence'] = evidence
    record['physical_force_norm_n'] = math.hypot(*result.evaluation.physical_wrench.resultant_force_N)
    record['physical_moment_norm_nm'] = math.hypot(*result.evaluation.physical_wrench.resultant_moment_Nm)
    return record


def run_benchmarks():
    suite = unittest.defaultTestLoader.loadTestsFromNames((
        'tests.test_steady_cornering_upright', 'tests.test_steady_cornering_tire',
        'tests.test_wufr_steady_cornering_geometry'))
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    geometry, tire = providers()
    config = solver_config()
    branches = []
    for sign in (-1, 1):
        cases = tuple(case(geometry, tire, sign*k, state_id=f'native_verification_{sign}_{k}')
                      for k in (0., .005, .01, .02))
        result = continue_cornering(cases, initial(), branch_id=f'native_source_fixture_{sign}',
            geometry_provider=geometry, tire_provider=tire, config=config)
        branches.append({'branch_id': result.branch_id, 'complete': result.complete,
                         'samples': [_sample(s) for s in result.results]})
    samples = [sample for branch in branches for sample in branch['samples']]
    evaluated = [sample for sample in samples if sample.get('physical_force_norm_n') is not None]
    passed = (tests.wasSuccessful() and len(samples) == 8 and all(branch['complete'] for branch in branches)
        and all(s['ok'] and s['physical_force_norm_n'] <= 1e-6
                and s['physical_moment_norm_nm'] <= 1e-6 for s in evaluated) and len(evaluated) == 8)
    return {
        'record_id': 'WUFR_STEADY_CORNERING_NATIVE_DEVELOPMENT_V1',
        'authorization_id': 'AUTH-VEH-0012', 'model_id': 'MOD-VEH-0009',
        'benchmark_ids': ['BENCH-VEH-0018', 'BENCH-VEH-0019', 'BENCH-VEH-0020'],
        'scope': 'explicit_native_source_integration_verification_fixtures_only',
        'status': 'pass' if passed else 'fail',
        'assumed_tire_extension': {'assumption_id': SYMMETRY_ASSUMPTION_ID, 'policy': SYMMETRY_POLICY,
            'negative_IA_measured': False, 'zero_IA_boundary_crossing_permitted': False},
        'geometry_revision': geometry.geometry_revision, 'setup_revision': geometry.setup_revision,
        'tire_revision': tire.tire_revision,
        'source_hashes': {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in SOURCE_FILES},
        'solver_config': asdict(config), 'native_provider_config': asdict(geometry.road.config),
        'native_contact_internal_q_L_bounds_rad': geometry._bounds,
        'native_material_derivative_q_L_steps_rad': (2e-4, 1e-4),
        'tests': {'count': tests.testsRun, 'successful': tests.wasSuccessful(), 'log': log.getvalue()},
        'summary': {'sample_count': len(samples), 'mass_kg': geometry.components.gravity.total_mass_kg,
            'maximum_force_norm_n': max((s['physical_force_norm_n'] for s in evaluated), default=None),
            'maximum_moment_norm_nm': max((s['physical_moment_norm_nm'] for s in evaluated), default=None),
            'force_limit_n': 1e-6, 'moment_limit_nm': 1e-6,
            'native_source_composition_fixture_verified': passed,
            'user_maneuver_or_installed_validation': False,
            'synchronized_steering_exchange_verified': False,
            'predictive_or_setup_authority': False},
        'branches': branches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run_benchmarks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': report['status'], 'tests': report['tests']['count'], **report['summary']}, indent=2))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
