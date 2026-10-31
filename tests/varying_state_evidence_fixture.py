"""Current-provider replay of explicit, hash-checked native verification seeds."""
from dataclasses import replace
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from pssd_vehicle.steady_cornering import CorneringCase, solve_cornering
from pssd_vehicle.steady_cornering_export import NativeCorneringExportSeries, export_native_cornering
from tests.wufr_cornering_fixture import providers, solver_config

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def bundle():
    path = ROOT/'benchmarks/vehicle/wufr_steady_cornering_native_development_v0.1.0.json'
    report = json.loads(path.read_text())
    if report['status'] != 'pass':
        raise AssertionError('Passing native benchmark required')
    for source, expected in report['source_hashes'].items():
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest() != expected:
            raise AssertionError(f'Native benchmark source changed: {source}')
    geometry, tire = providers()
    return geometry, tire, report


@lru_cache(maxsize=8)
def packet(branch, slot):
    geometry, tire, report = bundle()
    seed = report['branches'][branch]['samples'][slot]
    values = dict(seed['case'])
    for field in ('pressures_pa', 'accepted_assumptions'):
        values[field] = tuple(values[field])
    case = replace(CorneringCase(**values), geometry_revision=geometry.geometry_revision,
                   setup_revision=geometry.setup_revision, tire_revision=tire.tire_revision)
    result = solve_cornering(case, tuple(seed['coordinates']), geometry_provider=geometry,
                            tire_provider=tire, config=solver_config())
    if not result.ok:
        raise AssertionError(f'{result.failure_code}: {result.message}')
    return export_native_cornering(result, geometry_provider=geometry, tire_provider=tire,
        solver_config=solver_config(), sample_id=case.state_id,
        synchronization_revision='native_varying_state_steering_verification_v1')


def series(indices=((0, 0), (1, 2), (0, 2))):
    return NativeCorneringExportSeries('native_varying_state_steering_verification',
                                       tuple(packet(*index) for index in indices))
