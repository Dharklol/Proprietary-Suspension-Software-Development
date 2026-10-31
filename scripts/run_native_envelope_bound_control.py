#!/usr/bin/env python3
"""Separate numerical sideslip-bound control; never replace the original envelope."""
from dataclasses import asdict, replace
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pssd_vehicle.steady_cornering import CorneringCase, solve_cornering
from scripts.run_wufr_steady_cornering_benchmarks import _sample
from tests.wufr_cornering_fixture import providers, solver_config


def widen_sideslip_bound(config, bound_rad):
    if not math.isfinite(bound_rad) or bound_rad <= max(abs(config.lower_bounds[3]),abs(config.upper_bounds[3])):
        raise ValueError('Explicit finite sideslip bound must strictly widen the original bound')
    lower=tuple(-bound_rad if i==3 else x for i,x in enumerate(config.lower_bounds))
    upper=tuple(bound_rad if i==3 else x for i,x in enumerate(config.upper_bounds))
    return replace(config,lower_bounds=lower,upper_bounds=upper)


def build_control(report, bound_rad):
    summary=report['summary']
    if len(summary['branches'])!=1 or len(report['branches'])!=1:
        raise ValueError('One original signed envelope report required')
    if (summary['objective_weight']!=0. or summary['design_ranking_permitted'] is not False
            or summary['physical_limit_or_stability_claim'] is not False):
        raise ValueError('Unpromoted development report required')
    for p,expected in summary['source_hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=expected:
            raise ValueError('Original envelope source changed: '+p)
    branch=summary['branches'][0]
    accepted=branch['last_accepted_magnitude_per_m']
    failed=branch['first_failed_magnitude_per_m']
    if accepted is None or failed is None:
        raise ValueError('Original accepted/failed bracket required')
    attempts=report['branches'][0]['attempts']
    seed=next(a['result'] for a in attempts
              if a['result']['ok'] and abs(a['result']['case']['curvature_per_m'])==accepted)
    original=next(a['result'] for a in reversed(attempts)
                  if not a['result']['ok'] and abs(a['result']['case']['curvature_per_m'])==failed)
    values=dict(original['case'])
    for key in ('pressures_pa','accepted_assumptions'):values[key]=tuple(values[key])
    c=replace(CorneringCase(**values),state_id=values['state_id']+':sideslip_bound_control')
    geometry,tire=providers()
    if (c.geometry_revision!=geometry.geometry_revision or c.setup_revision!=geometry.setup_revision
            or c.tire_revision!=tire.tire_revision):
        raise ValueError('Current providers do not match original envelope revisions')
    baseline=solver_config()
    # Compare serialized values so JSON lists and runtime tuples are equivalent.
    if json.loads(json.dumps(asdict(baseline)))!=summary['solver_config']:
        raise ValueError('Original solver controls changed')
    widened=widen_sideslip_bound(baseline,bound_rad)
    result=solve_cornering(c,tuple(seed['coordinates']),geometry_provider=geometry,
                          tire_provider=tire,config=widened)
    same_branch=(result.evaluation is not None and
                 tuple(result.evaluation.branch_signature)==tuple(branch['reference_branch_signature']))
    passed=result.ok and same_branch
    return {'status':'pass' if passed else 'fail',
        'scope':'single_changed_numerical_sideslip_bound_control_only',
        'direction_sign':branch['direction_sign'],'case':asdict(c),
        'original_solver_config':asdict(baseline),'control_solver_config':asdict(widened),
        'initial_coordinates':seed['coordinates'],'original_failed_case':original['case'],
        'original_failure_code':original['failure_code'],
        'original_failed_coordinates':original['coordinates'],
        'same_source_branch':same_branch,'original_envelope_not_replaced':True,
        'result':_sample(result),'objective_weight':0.,'physical_limit_or_stability_claim':False,
        'source_hashes':{**summary['source_hashes'],
            'scripts/run_native_envelope_bound_control.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'tests/test_native_envelope_bound_control.py':hashlib.sha256(
                (ROOT/'tests/test_native_envelope_bound_control.py').read_bytes()).hexdigest()}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--sideslip-bound',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=build_control(json.loads(args.report.read_text()),args.sideslip_bound)
    report['original_report_sha256']=hashlib.sha256(args.report.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'direction':report['direction_sign'],
        'curvature':report['case']['curvature_per_m'],
        'sideslip':report['result']['coordinates'][3],'same_source_branch':report['same_source_branch'],
        'failure':report['result']['failure_code']},indent=2))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())
