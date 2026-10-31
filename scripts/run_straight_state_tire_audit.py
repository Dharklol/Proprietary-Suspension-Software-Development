#!/usr/bin/env python3
"""Explain the native straight fixture through conditional source-table probes.

No probe changes vehicle equilibrium, removes source bias or selects a tire root.
Negative-IA decomposition stays on the accepted reflected side, including its
one-sided zero-IA limit; the direct zero-IA query is reported separately.
"""
from dataclasses import asdict, replace
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pssd_tire.steady_state_lateral import SteadyStateLateralOperatingState, evaluate_table
from tests.varying_state_evidence_fixture import bundle, packet


def finite_difference_decomposition(f00, fa0, f0g, fag):
    """An exact four-query identity, not an additive tire constitutive law."""
    return {'source_bias_n': f00, 'slip_increment_at_zero_IA_n': fa0-f00,
            'inclination_increment_at_zero_slip_n': f0g-f00,
            'interaction_n': fag-fa0-f0g+f00}


def audit_query(query, tire_provider):
    actual = tire_provider(query)  # preserve existing source/revision/domain gates
    reflected = query.inclination_rad < 0
    sign = -1 if reflected else 1
    source = SteadyStateLateralOperatingState(
        sign*query.slip_angle_rad, query.normal_load_n,
        sign*query.inclination_rad, query.pressure_pa, query.state_id,
        query.source_tire_id, query.convention_id)
    states = {'both_zero': replace(source, slip_angle_rad=0., inclination_rad=0.),
              'zero_IA': replace(source, inclination_rad=0.),
              'zero_slip': replace(source, slip_angle_rad=0.), 'actual': source}
    responses = {name: evaluate_table(tire_provider.table, state)
                 for name, state in states.items()}
    values = {name: sign*value.lateral_force_N for name, value in responses.items()}
    terms = finite_difference_decomposition(values['both_zero'], values['zero_IA'],
                                           values['zero_slip'], values['actual'])
    direct_zero = tire_provider(replace(query, inclination_rad=0.))
    direct_both_zero = tire_provider(replace(query, slip_angle_rad=0., inclination_rad=0.))
    return {'requested_query': asdict(query), 'reflected': reflected,
        'actual_lateral_force_n': actual.lateral_force_n,
        'actual_branch': actual.branch_id,
        'actual_source_ids': actual.source_ids,
        'source_probes': {name: {'source_state': asdict(states[name]),
            'source_response': asdict(response),
            'physical_force_on_original_side_n': values[name]}
            for name, response in responses.items()},
        'decomposition_n': terms,
        'decomposition_reconstruction_error_n': abs(sum(terms.values())-actual.lateral_force_n),
        'direct_zero_IA_force_n': direct_zero.lateral_force_n,
        'direct_zero_slip_zero_IA_force_n': direct_both_zero.lateral_force_n,
        'original_side_zero_IA_limit_force_n': values['zero_IA'],
        'zero_IA_boundary_jump_at_fixed_slip_n': values['zero_IA']-direct_zero.lateral_force_n,
        'original_side_zero_slip_force_n': values['zero_slip'],
        'probe_role': 'conditional_table_queries_not_vehicle_equilibria',
        'zero_IA_probe_rule': 'reflected_side_limit' if reflected else 'direct_source',
        'objective_weight': 0., 'design_ranking_permitted': False}


def build_report():
    geometry, tire, _ = bundle()
    state = packet(0, 0)  # current providers re-solve the hash-checked native seed
    result = state.equilibrium
    if not result.ok or result.case.curvature_per_m != 0.:
        raise ValueError('Passing zero-curvature fixture required')
    evaluation = result.evaluation
    wheels = []
    total = [0., 0., 0.]
    for wheel, response in zip(evaluation.geometry.wheels, evaluation.tires):
        query = response.query
        audit = audit_query(query, tire)
        # Independent explicit projection of a local pure-lateral tire force.
        heading = math.atan2(wheel.forward_heading[1], wheel.forward_heading[0])
        force = (-response.lateral_force_n*math.sin(heading),
                 response.lateral_force_n*math.cos(heading), 0.)
        total = [a+b for a, b in zip(total, force)]
        audit.update({'corner_id': wheel.corner_id,
            'wheel_heading_deg': math.degrees(heading),
            'velocity_heading_deg': math.degrees(heading-query.slip_angle_rad),
            'slip_angle_deg': math.degrees(query.slip_angle_rad),
            'inclination_deg': math.degrees(query.inclination_rad),
            'force_heading_n': force})
        wheels.append(audit)
    holder = evaluation.holder.force_heading_n
    balance = tuple(a+b for a, b in zip(total, holder))
    weight = sum(m.mass_kg for m in evaluation.geometry.masses)*result.case.gravity_m_s2
    normal_balance = sum(result.coordinates[6:])-weight
    # Reuse the established 1e-6 N physical balance limit, without loosening it.
    passed = (max(w['decomposition_reconstruction_error_n'] for w in wheels) <= 1e-6
              and math.dist(balance, (0., 0., 0.)) <= 1e-6
              and abs(normal_balance) <= 1e-6)
    sources = ('scripts/run_straight_state_tire_audit.py',
        'tests/test_straight_state_tire_audit.py',
        'src/pssd_vehicle/steady_cornering_tire.py',
        'tests/varying_state_evidence_fixture.py', 'tests/wufr_cornering_fixture.py',
        'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml',
        'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
    return {'status': 'pass' if passed else 'fail',
        'scope': 'straight_fixture_conditional_tire_diagnostics_only',
        'state_id': result.case.state_id, 'configuration_id': result.case.configuration_id,
        'geometry_revision': geometry.geometry_revision, 'setup_revision': geometry.setup_revision,
        'tire_revision': tire.tire_revision,
        'source_hashes': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
        'case': asdict(result.case), 'wheels': wheels,
        'tire_force_sum_heading_n': total, 'holder': asdict(evaluation.holder),
        'independent_horizontal_balance_n': balance,
        'independent_vertical_balance_n': normal_balance,
        'source_equilibrium_physical_wrench': asdict(evaluation.physical_wrench),
        'objective_weight': 0., 'design_ranking_permitted': False,
        'interpretation': 'Exact conditional finite differences; no additive tire model, '
            'bias correction, setup recommendation or independent physical validation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary-output', type=Path)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    if args.summary_output is not None:
        summary = {key: value for key, value in report.items() if key != 'wheels'}
        summary['source_equilibrium_physical_wrench'] = {
            key: value for key, value in report['source_equilibrium_physical_wrench'].items()
            if key != 'contributions'}
        summary['wheels'] = [{key: value for key, value in wheel.items()
                             if key not in ('source_probes', 'actual_source_ids')}
                            for wheel in report['wheels']]
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': report['status'], 'wheel_count': len(report['wheels']),
        'holder': report['holder'], 'horizontal_balance_n': report['independent_horizontal_balance_n'],
        'vertical_balance_n': report['independent_vertical_balance_n']}, indent=2))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
