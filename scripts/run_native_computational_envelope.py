#!/usr/bin/env python3
"""Map warm-started solver reachability under explicit native fixture controls.

No physical grip/stability limit is inferred from a failed solve. Every coarse
and refinement attempt is retained, with its initial point and raw failure codes.
"""
from collections import Counter
from dataclasses import asdict, dataclass, replace
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pssd_vehicle.steady_cornering import CorneringSolveResult, solve_cornering
from scripts.run_wufr_steady_cornering_benchmarks import SOURCE_FILES, _sample
from tests.varying_state_evidence_fixture import bundle, packet
from tests.wufr_cornering_fixture import solver_config


@dataclass(frozen=True)
class EnvelopeControls:
    curvature_magnitudes_per_m: tuple[float, ...]
    refinement_steps: int
    curvature_resolution_per_m: float

    def __post_init__(self):
        grid = self.curvature_magnitudes_per_m
        if (not grid or not all(math.isfinite(k) and k > 0 for k in grid)
                or any(a >= b for a,b in zip(grid,grid[1:]))):
            raise ValueError('Explicit positive strictly increasing curvature magnitudes required')
        if type(self.refinement_steps) is not int or self.refinement_steps < 0:
            raise ValueError('Nonnegative integer refinement budget required')
        if not math.isfinite(self.curvature_resolution_per_m) or self.curvature_resolution_per_m <= 0:
            raise ValueError('Positive finite curvature resolution required')


def failure_category(result, reference_signature=None):
    """Classify terminal evidence only; trial failures remain separate diagnostics."""
    if result.ok:
        return 'accepted'
    code = result.failure_code
    if code == 'branch_change':
        current = result.evaluation.branch_signature if result.evaluation is not None else None
        if reference_signature is not None and current is not None:
            for old,new in zip(reference_signature[1:],current[1:]):
                if old.split(':')[0] != new.split(':')[0] and {
                    old.split(':')[0],new.split(':')[0]} == {
                        'direct_nonnegative_IA','reflected_negative_IA'}:
                    return 'confirmed_reflection_boundary'
        return 'branch_transition'
    if code in ('operating_state_out_of_domain','slip_out_of_domain',
                'interpolation_cell_incomplete','force_demand_out_of_domain'):
        return 'tire_source_domain'
    if code in ('road_root_unbracketed','road_root_ambiguous','derivative_domain_failure',
                'contact_coefficient_degenerate','coordinate_derivative_degenerate',
                'compatibility_failure','suspension_force_failure','singular_contact'):
        return 'geometry_contact_or_suspension'
    if code == 'bounds_failure':
        return 'declared_solver_bounds'
    if code == 'physical_closure_failure':
        return 'physical_closure_rejection'
    if code in ('source_mismatch','tire_source_mismatch','frame_error',
                'assumptions_not_authorized','symmetry_not_authorized'):
        return 'source_configuration'
    if code in ('nonconvergence','line_search_failure','singular_tangent',
                'tangent_provider_failure','derivative_not_converged','road_root_nonconvergence'):
        return 'numerical_or_derivative_failure'
    return 'unclassified_failure'


@dataclass(frozen=True)
class EnvelopeAttempt:
    stage: str
    curvature_magnitude_per_m: float
    initial_coordinates: tuple[float, ...]
    result: CorneringSolveResult
    category: str


@dataclass(frozen=True)
class EnvelopeBranch:
    direction_sign: int
    attempts: tuple[EnvelopeAttempt, ...]
    stopping_reason: str
    last_accepted_magnitude_per_m: float | None
    first_failed_magnitude_per_m: float | None
    first_coarse_failure_magnitude_per_m: float | None
    reference_branch_signature: tuple[str, ...] | None


def map_branch(seed_case, initial_coordinates, *, direction_sign, controls,
               geometry_provider, tire_provider, config, solver=solve_cornering, progress=None):
    """Retain all attempts; bisect only a warm-started acceptance/failure bracket.

    Refinement does not erase the first coarse failure, imply monotonic physical
    feasibility, change sources/setup/speed, or cross the accepted source branch.
    """
    if type(direction_sign) is not int or direction_sign not in (-1,1):
        raise ValueError('Explicit direction sign -1 or +1 required')
    if seed_case.curvature_per_m != 0:
        raise ValueError('Explicit zero-curvature seed case required')
    attempts, signature = [], None

    def attempt(stage, magnitude, guess):
        nonlocal signature
        c = replace(seed_case,curvature_per_m=direction_sign*magnitude,
                    state_id=f'{seed_case.state_id}:direction:{direction_sign}:{stage}:{len(attempts)}:{magnitude:.12g}')
        r = solver(c,guess,geometry_provider=geometry_provider,tire_provider=tire_provider,config=config)
        if r.case != c:
            raise ValueError('Solver returned a different requested source/control case')
        if r.ok:
            current = r.evaluation.branch_signature
            if signature is not None and current != signature:
                r = replace(r,ok=False,failure_code='branch_change',result_label=None,
                            message='Envelope solve left the original accepted source branch')
            elif signature is None:
                signature = current
        item = EnvelopeAttempt(stage,magnitude,tuple(guess),r,failure_category(r,signature))
        attempts.append(item)
        if progress is not None:
            progress(item)
        return item

    zero = attempt('seed',0.,initial_coordinates)
    if not zero.result.ok:
        return EnvelopeBranch(direction_sign,tuple(attempts),'seed_failure',None,0.,None,signature)
    low, high, coarse_failure = zero, None, None
    for magnitude in controls.curvature_magnitudes_per_m:
        current = attempt('coarse',magnitude,low.result.coordinates)
        if not current.result.ok:
            high, coarse_failure = current, magnitude
            break
        low = current
    if high is None:
        return EnvelopeBranch(direction_sign,tuple(attempts),'grid_end_no_failure',
            low.curvature_magnitude_per_m,None,None,signature)
    for _ in range(controls.refinement_steps):
        if high.curvature_magnitude_per_m-low.curvature_magnitude_per_m <= controls.curvature_resolution_per_m:
            break
        mid = (low.curvature_magnitude_per_m+high.curvature_magnitude_per_m)/2
        current = attempt('refinement',mid,low.result.coordinates)
        if current.result.ok:
            low = current
        else:
            high = current
    reason = ('resolution_reached' if high.curvature_magnitude_per_m-low.curvature_magnitude_per_m
              <= controls.curvature_resolution_per_m else 'refinement_budget_exhausted')
    return EnvelopeBranch(direction_sign,tuple(attempts),reason,
        low.curvature_magnitude_per_m,high.curvature_magnitude_per_m,coarse_failure,signature)


def _diagnostics(item, tire, config):
    r = item.result
    record = {'stage': item.stage, 'curvature_magnitude_per_m': item.curvature_magnitude_per_m,
        'signed_curvature_per_m': r.case.curvature_per_m, 'ok':r.ok,
        'category':item.category,'failure_code':r.failure_code,'message':r.message,
        'initial_coordinates':item.initial_coordinates,'coordinates':r.coordinates,
        'iterations':r.iterations,'scaled_residual_norm':r.scaled_residual_norm,
        'reciprocal_pivot_ratio':r.reciprocal_pivot_ratio,
        'trial_failure_counts':dict(Counter(code for code,_ in r.trial_failures)),
        'kinematic_acceleration_m_s2':r.case.speed_m_s**2*abs(r.case.curvature_per_m),
        'coordinate_bound_margins':tuple((x-a,b-x) for x,a,b in
            zip(r.coordinates,config.lower_bounds,config.upper_bounds)),
        'objective_weight':0.,'design_ranking_permitted':False}
    if r.evaluation is None:
        return record
    ev = r.evaluation
    record.update({'branch_signature':ev.branch_signature,'holder':asdict(ev.holder),
        'body_coordinates':r.coordinates[:3],'sideslip_rad':r.coordinates[3],
        'rack_m':r.coordinates[4], 'wheel_coordinates_m':ev.geometry.wheel_coordinates_m,
        'physical_force_norm_n':math.hypot(*ev.physical_wrench.resultant_force_N),
        'physical_moment_norm_nm':math.hypot(*ev.physical_wrench.resultant_moment_Nm)})
    curves = {c.curve_id:c for c in tire.table.curves}
    wheels = []
    for wheel,response in zip(ev.geometry.wheels,ev.tires):
        query = response.query
        source = json.loads(next(s.partition(':')[2] for s in response.source_ids
                                 if s.startswith('source_response:')))
        participating = [curves[k] for k in source['participating_curve_ids']]
        source_query = source['operating_state']
        slip_min = max(c.slip_angle_rad[0] for c in participating)
        slip_max = min(c.slip_angle_rad[-1] for c in participating)
        # Global axis extents are necessary bounds only, not proof of a complete cell.
        axes = {'normal_load_N':query.normal_load_n,'inclination_rad':abs(query.inclination_rad),
                'pressure_Pa':query.pressure_pa}
        margins = {key:(value-min(getattr(c,key) for c in tire.table.curves),
                       max(getattr(c,key) for c in tire.table.curves)-value)
                   for key,value in axes.items()}
        wheels.append({'corner_id':wheel.corner_id,'query':asdict(query),
            'source_query':source_query,'lateral_force_n':response.lateral_force_n,
            'center_heading_m':wheel.center.point.position_m,
            'heading_rad':math.atan2(wheel.forward_heading[1],wheel.forward_heading[0]),
            'reflection_boundary_distance_rad':abs(query.inclination_rad),
            'global_source_axis_margins_necessary_not_sufficient':margins,
            'participating_common_slip_domain_rad':(slip_min,slip_max),
            'participating_slip_domain_margins_rad':(source_query['slip_angle_rad']-slip_min,
                                                   slip_max-source_query['slip_angle_rad']),
            'participating_curve_ids':source['participating_curve_ids'],
            'slip_segment_ids':source['slip_segment_ids'],'branch_id':response.branch_id})
    record['wheels'] = wheels
    return record


def build_report(controls, directions, progress=None):
    if not directions or len(set(directions)) != len(directions) or any(
            type(sign) is not int or sign not in (-1,1) for sign in directions):
        raise ValueError('Explicit unique direction signs -1/+1 required')
    geometry,tire,_ = bundle()
    config = solver_config()
    branches, summaries = [], []
    for sign in directions:
        slot = 0 if sign==-1 else 1
        seed = packet(slot,0).equilibrium
        run = map_branch(seed.case,seed.coordinates,direction_sign=sign,controls=controls,
            geometry_provider=geometry,tire_provider=tire,config=config,progress=progress)
        branches.append({'direction_sign':sign,'attempts':[
            {'stage':a.stage,'initial_coordinates':a.initial_coordinates,'category':a.category,
             'result':_sample(a.result)} for a in run.attempts]})
        summaries.append({'direction_sign':sign,'stopping_reason':run.stopping_reason,
            'last_accepted_magnitude_per_m':run.last_accepted_magnitude_per_m,
            'first_failed_magnitude_per_m':run.first_failed_magnitude_per_m,
            'first_coarse_failure_magnitude_per_m':run.first_coarse_failure_magnitude_per_m,
            'reference_branch_signature':run.reference_branch_signature,
            'attempts':[_diagnostics(a,tire,config) for a in run.attempts]})
    paths = (*SOURCE_FILES,'scripts/run_native_computational_envelope.py',
             'tests/test_native_computational_envelope.py','tests/varying_state_evidence_fixture.py')
    passed = all(b['last_accepted_magnitude_per_m'] is not None and
                 b['last_accepted_magnitude_per_m'] >= controls.curvature_magnitudes_per_m[0]
                 for b in summaries)
    summary = {'status':'pass' if passed else 'fail',
        'scope':'explicit_native_fixture_warm_started_computational_reachability_only',
        'controls':asdict(controls),'solver_config':asdict(config),
        'geometry_revision':geometry.geometry_revision,'setup_revision':geometry.setup_revision,
        'tire_revision':tire.tire_revision,
        'source_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'branches':summaries,'failed_attempts_are_retained':True,
        'status_meaning':'mapping_completed_and_first_requested_nonzero_sample_recovered',
        'physical_limit_or_stability_claim':False,'objective_weight':0.,'design_ranking_permitted':False}
    return {'summary':summary,'branches':branches},summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--curvatures',type=float,nargs='+',required=True)
    parser.add_argument('--directions',type=int,nargs='+',choices=(-1,1),required=True)
    parser.add_argument('--refinement-steps',type=int,required=True)
    parser.add_argument('--curvature-resolution',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--summary-output',type=Path,required=True)
    args = parser.parse_args()
    controls = EnvelopeControls(tuple(args.curvatures),args.refinement_steps,args.curvature_resolution)
    def progress(item):
        print(json.dumps({'stage':item.stage,'kappa':item.result.case.curvature_per_m,
                          'ok':item.result.ok,'category':item.category,
                          'failure':item.result.failure_code}),flush=True)
    report,summary = build_report(controls,tuple(args.directions),progress)
    for path,value in ((args.output,report),(args.summary_output,summary)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':summary['status'],'branches':[
        {k:v for k,v in b.items() if k!='attempts'} for b in summary['branches']]},indent=2))
    return 0 if summary['status']=='pass' else 1


if __name__=='__main__':
    raise SystemExit(main())
