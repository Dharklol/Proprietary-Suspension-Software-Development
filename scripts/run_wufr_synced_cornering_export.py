#!/usr/bin/env python3
"""Revalidate native benchmark seeds and export atomic development evidence."""
from dataclasses import asdict, replace
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pssd_vehicle.steady_cornering import CorneringCase, solve_cornering
from pssd_vehicle.steady_cornering_export import NativeCorneringExportSeries, export_native_cornering
from tests.wufr_cornering_fixture import providers, solver_config

NATIVE_REPORT = 'benchmarks/vehicle/wufr_steady_cornering_native_development_v0.1.0.json'


def run_export():
    raw = (ROOT/NATIVE_REPORT).read_bytes()
    native = json.loads(raw)
    if native['status'] != 'pass':
        raise ValueError('Passing native source-integration evidence required')
    for path, expected in native['source_hashes'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Native evidence source changed: {path}')
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_steady_cornering_export')
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise ValueError(log.getvalue())
    geometry, tire = providers()
    packets, summaries = [], []
    for branch in native['branches']:
        for record in branch['samples']:
            values = dict(record['case'])
            for field in ('pressures_pa', 'accepted_assumptions'):
                values[field] = tuple(values[field])
            # Parent coordinates are seeds, not imported solved states. Exact
            # source hashes above gate the inputs. Bind current loader-derived
            # revisions (which may differ across Python numerical runtimes),
            # then re-solve and revalidate every result under current providers.
            case = replace(CorneringCase(**values), geometry_revision=geometry.geometry_revision,
                           setup_revision=geometry.setup_revision, tire_revision=tire.tire_revision)
            result = solve_cornering(case, tuple(record['coordinates']), geometry_provider=geometry,
                                    tire_provider=tire, config=solver_config())
            packet = export_native_cornering(result, geometry_provider=geometry, tire_provider=tire,
                solver_config=solver_config(), sample_id=case.state_id,
                synchronization_revision='native_cornering_export_verification_v1')
            packets.append(packet)
            summaries.append({
                'sample_id': packet.sample.vehicle_source.sample_id, 'state_id': case.state_id,
                'continuation_branch_id': branch['branch_id'], 'curvature_per_m': case.curvature_per_m,
                'rack_displacement_m': packet.sample.rack_displacement_m,
                'body_coordinates': result.coordinates[:3],
                'current_total_cg_heading_m': result.evaluation.inertia.current_total_cg_heading_m,
                'pose_state_id': packet.sample.pose.state_id,
                'steering_dof_rule': packet.sample.pose.steering_dof_rule,
                'vehicle_role': packet.sample.vehicle.role.value, 'state_weight': packet.sample.vehicle.state_weight,
                'wheel_inputs_complete': packet.sample.front_inputs_complete,
                'normal_loads_n': [w.normal_load_n for w in packet.sample.vehicle.wheels],
                'inclinations_deg': [w.inclination_deg for w in packet.sample.vehicle.wheels],
                'lateral_forces_n': [w.lateral_force_demand_n for w in packet.sample.vehicle.wheels],
                'pressures_kpa': [w.pressure_kpa for w in packet.sample.vehicle.wheels],
            })
    series = NativeCorneringExportSeries('native_cornering_export_verification_v1', tuple(packets))
    payload = {'contract': series.packets[0].consumer_contract, 'native_seed_report': NATIVE_REPORT,
               'native_seed_report_sha256': hashlib.sha256(raw).hexdigest(), 'series': asdict(series)}
    summary = {'status': 'pass', 'scope': 'native_source_verification_fixture_exports_only',
        'packet_count': len(packets), 'tests': {'count': tests.testsRun, 'successful': True},
        'native_seed_report_sha256': payload['native_seed_report_sha256'],
        'geometry_revision': geometry.geometry_revision, 'setup_revision': geometry.setup_revision,
        'tire_revision': tire.tire_revision, 'consumer_contract': payload['contract'],
        'heading_frame_id': packets[0].body_pose.inertial_frame_id,
        'heading_origin_id': packets[0].body_pose.inertial_origin_id,
        'source_hashes': {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in (
            'src/pssd_vehicle/steady_cornering_export.py', 'tests/test_steady_cornering_export.py',
            'src/pssd_steering/optimization/native_poses.py', 'scripts/run_wufr_synced_cornering_export.py')},
        'legacy_fixed_sweep_consumption_permitted': False,
        'design_ranking_or_setup_authority': False, 'samples': summaries}
    return payload, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary-output', type=Path, required=True)
    args = parser.parse_args()
    payload, summary = run_export()
    for path, record in ((args.output, payload), (args.summary_output, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: summary[key] for key in ('status', 'packet_count', 'tests', 'consumer_contract')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
