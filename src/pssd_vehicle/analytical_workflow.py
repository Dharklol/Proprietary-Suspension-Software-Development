"""Explicit unranked native comparisons; the plan owns all study inputs."""
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import re
import tomllib

from pssd_steering.optimization import generate_candidate_geometry, load_requirement_set, resolve_candidate
from .steady_cornering import CorneringCase, CorneringSolverConfig, solve_cornering
from .steady_cornering_tire import R25BDevelopmentCorneringTireProvider, SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY
from .wufr_static_equilibrium import load_wufr_static_equilibrium_provider
from .wufr_steady_cornering_geometry import WUFRCorneringGeometryProvider

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'pssd.analytical-design-workflow.v1'
DEFAULT_PLAN = 'configurations/vehicle/ANALYTICAL_DESIGN_WORKFLOW_V0.toml'
CORNERS = ('front_left', 'front_right', 'rear_left', 'rear_right')
COORDINATES = ('body_heave_m','roll_rad','pitch_rad','sideslip_rad','rack_m','holder_force_n',
               'Fz_front_left_n','Fz_front_right_n','Fz_rear_left_n','Fz_rear_right_n')
METRICS = {
    'rack_m': ('Rack demand', 'm', 1e-8),
    'front_heading_split_rad': ('Left minus right front heading', 'rad', 1e-7),
    'sideslip_rad': ('Body sideslip', 'rad', 1e-7),
    'roll_rad': ('Body roll', 'rad', 1e-7),
    'holder_force_n': ('Virtual holding force', 'N', 1e-4),
    **{f'Fz_{c}_n': (c+' normal reaction', 'N', 1e-4) for c in CORNERS},
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False,
                                    separators=(',', ':')).encode()).hexdigest()


def solver_config(plan):
    raw = dict(plan['solver'])
    for key in ('coordinate_scales', 'residual_scales', 'lower_bounds', 'upper_bounds', 'fd_steps'):
        raw[key] = tuple(raw[key])
    config = CorneringSolverConfig(**raw)
    if config.scaled_residual_tolerance != 1e-10:
        raise ValueError('Original Newton acceptance required')
    return config


def load_plan(path, root=ROOT):
    plan = tomllib.loads(Path(path).read_text())
    required = {'version', 'plan_id', 'configuration_role', 'design_question', 'seed_report',
        'requirement_set', 'objective_weight', 'design_ranking_permitted', 'reference',
        'sources', 'solver', 'cases', 'candidates', 'assumptions', 'numerical_recovery'}
    if set(plan) != required or plan['version'] != '0.1.0':
        raise ValueError('Unsupported or incomplete plan')
    if plan['objective_weight'] != 0. or plan['design_ranking_permitted'] is not False:
        raise ValueError('Only zero-weight unranked evidence is supported')
    if plan['configuration_role'] != 'provisional_source_reference_not_installed_or_recommended_setup':
        raise ValueError('Explicit provisional source-reference role required')
    fields = {'cases': {'id', 'curvature_per_m', 'assumption_study'},
        'candidates': {'id', 'rack_longitudinal_offset_m'},
        'assumptions': {'id', 'front_toe_delta_deg', 'front_camber_delta_deg', 'lateral_force_gain'}}
    for group, keys in fields.items():
        items = plan[group]
        if not items or len({i['id'] for i in items}) != len(items):
            raise ValueError('Unique nonempty '+group+' required')
        for item in items:
            if set(item) != keys or not re.fullmatch(r'[a-z][a-z0-9_]*', item['id']):
                raise ValueError('Invalid '+group+' record')
            for key, value in item.items():
                if key not in ('id', 'assumption_study') and (
                        type(value) not in (float, int) or not math.isfinite(value)):
                    raise ValueError('Finite explicit study inputs required')
    if any(type(s['assumption_study']) is not bool or abs(s['curvature_per_m']) > .1 for s in plan['cases']):
        raise ValueError('Explicit stress coverage within |curvature|<=0.10/m required')
    nominal = next((a for a in plan['assumptions'] if a['id'] == 'nominal'), None)
    reference = next((c for c in plan['candidates'] if c['id'] == 'reference'), None)
    if nominal != dict(id='nominal', front_toe_delta_deg=0., front_camber_delta_deg=0., lateral_force_gain=1.):
        raise ValueError('Unchanged nominal assumption required')
    if reference != dict(id='reference', rack_longitudinal_offset_m=0.):
        raise ValueError('Unchanged reference rack required')
    for a in plan['assumptions']:
        changed = sum((a['front_toe_delta_deg'] != 0., a['front_camber_delta_deg'] != 0., a['lateral_force_gain'] != 1.))
        if changed != (0 if a['id'] == 'nominal' else 1):
            raise ValueError('One-at-a-time stresses required')
        if abs(a['front_toe_delta_deg']) > .2 or abs(a['front_camber_delta_deg']) > .5 or not .95 <= a['lateral_force_gain'] <= 1.05:
            raise ValueError('Stress outside first-study bounds')
    if any(abs(c['rack_longitudinal_offset_m']) > .005 for c in plan['candidates']):
        raise ValueError('Rack outside first-study bounds')
    ref = plan['reference']
    if set(ref) != {'mass_kg', 'speed_mps', 'pressure_pa', 'front_arb_setting', 'rear_arb_setting', 'road_gap_tolerance_m'}:
        raise ValueError('Incomplete reference controls')
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in ref.values()):
        raise ValueError('Positive finite reference controls required')
    if any(type(ref[k]) is not int or ref[k] not in range(1, 6) for k in ('front_arb_setting', 'rear_arb_setting')):
        raise ValueError('Discrete ARB settings required')
    if ref['road_gap_tolerance_m'] > 1e-14:
        raise ValueError('Explicit refined study contact precision required')
    for name in (*plan['sources'].values(), plan['seed_report'], plan['requirement_set']):
        p = (root/name).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file():
            raise ValueError('Repository-local source required: '+name)
    solver_config(plan)
    recovery=plan['numerical_recovery']
    if set(recovery)!={'coordinate_order','coordinate_offsets','maximum_initial_scaled_residual','maximum_scaled_coordinate_difference'}:
        raise ValueError('Complete explicit numerical recovery controls required')
    if tuple(recovery['coordinate_order'])!=COORDINATES:
        raise ValueError('Recovery coordinate order mismatch')
    offsets=recovery['coordinate_offsets']
    if len(offsets)!=10 or not all(type(v) in (int,float) and math.isfinite(v) for v in offsets) or not any(offsets):
        raise ValueError('Finite nonzero ten-coordinate recovery perturbation required')
    for key,limit in (('maximum_initial_scaled_residual',1e-8),('maximum_scaled_coordinate_difference',1e-5)):
        if not math.isfinite(recovery[key]) or not 0<recovery[key]<=limit:
            raise ValueError('Recovery guard exceeds declared numerical scope')
    return plan


def expected_cells(plan, candidate=None):
    return {(c['id'], a['id'], s['id']) for c in plan['candidates'] if candidate is None or c['id'] == candidate
            for a in plan['assumptions'] for s in plan['cases'] if a['id'] == 'nominal' or s['assumption_study']}


def verify_hashes(hashes, root=ROOT):
    for name, expected in hashes.items():
        path = (root/name).resolve()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Source changed: '+name)


def source_manifest(plan, plan_path, root=ROOT):
    seed = json.loads((root/plan['seed_report']).read_text())
    paths = set(seed['source_hashes']) | set(plan['sources'].values()) | {
        plan['seed_report'], plan['requirement_set'], str(Path(plan_path).resolve().relative_to(root.resolve())),
        'scripts/run_analytical_design_workflow.py', 'tests/test_analytical_design_workflow.py',
        'tests/test_analytical_numerical_recovery.py'}
    paths.update(str(p.relative_to(root)) for p in (root/'src').rglob('*.py') if 'pssd_viz' not in p.parts)
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(paths)}


class TireGainStress:
    """Declared analytical stress retaining unscaled query, force and provenance."""
    def __init__(self, source, gain):
        if not math.isfinite(gain) or not .95 <= gain <= 1.05:
            raise ValueError('Explicit bounded gain required')
        self.source, self.gain = source, gain
        self.tire_revision = source.tire_revision if gain == 1. else fingerprint(
            {'source_tire_revision': source.tire_revision, 'analytical_gain': gain})

    def __call__(self, query):
        if query.tire_revision != self.tire_revision:
            raise ValueError('Stress tire revision mismatch')
        result = self.source(replace(query, tire_revision=self.source.tire_revision))
        if self.gain == 1.:
            return result
        return replace(result, query=query, lateral_force_n=result.lateral_force_n*self.gain,
            source_ids=(*result.source_ids, 'analytical_lateral_force_gain:'+str(self.gain),
                        'unscaled_source_lateral_force_n:'+str(result.lateral_force_n),
                        'stress_only_not_measured_tire_data'))


def build_geometry(plan, candidate, assumption, components, root=ROOT):
    road = components.road_contact
    steering = road.steering_geometry
    if candidate['rack_longitudinal_offset_m'] != 0.:
        requirements = load_requirement_set(root/plan['requirement_set'])
        resolved = resolve_candidate(requirements, {'rack_longitudinal_offset': candidate['rack_longitudinal_offset_m']},
                                     candidate_id=candidate['id'])
        steering = generate_candidate_geometry(steering, requirements, resolved).geometry
    profile = road.wheel_profile
    if assumption['front_toe_delta_deg'] != 0. or assumption['front_camber_delta_deg'] != 0.:
        front = replace(profile.front,
            static_toe_out_rad=profile.front.static_toe_out_rad+math.radians(assumption['front_toe_delta_deg']),
            static_camber_rad=profile.front.static_camber_rad+math.radians(assumption['front_camber_delta_deg']))
        profile = replace(profile, front=front, fixture_id=plan['plan_id']+':'+assumption['id'],
                          authority='analytical_setup_family_not_historical_or_installed')
    identity = plan['plan_id']+':'+candidate['id']+':'+assumption['id']
    road = replace(road, steering_geometry=steering, wheel_profile=profile,
        source=replace(road.source, configuration_id=identity),
        config=replace(road.config, road_gap_tolerance_m=plan['reference']['road_gap_tolerance_m']))
    # Preserve physical numbers and source record IDs; bind the new study context
    # consistently across the existing component identity checks.
    springs = components.spring_package
    return WUFRCorneringGeometryProvider(replace(components,
        source=replace(components.source, configuration_id=identity), road_contact=road,
        gravity=replace(components.gravity, configuration_id=identity),
        spring_package=replace(springs, configuration_id=identity,
            front=replace(springs.front, configuration_id=identity), rear=replace(springs.rear, configuration_id=identity),
            reference=replace(springs.reference, configuration_id=identity)),
        front_zbar_fixture=replace(components.front_zbar_fixture, configuration_id=identity),
        rear_zbar_fixture=replace(components.rear_zbar_fixture, configuration_id=identity)))


def metrics_from_record(record):
    if not record['ok'] or record['evaluation'] is None:
        return None
    q = record['coordinates']
    headings = {w['corner_id']: math.atan2(w['forward_heading'][1], w['forward_heading'][0])
                for w in record['evaluation']['geometry']['wheels']}
    return {'rack_m': q[4], 'front_heading_split_rad': headings['front_left']-headings['front_right'],
        'sideslip_rad': q[3], 'roll_rad': q[1], 'holder_force_n': q[5],
        **dict(zip((f'Fz_{c}_n' for c in CORNERS), q[6:]))}


def recovery_eligible(result,config,controls):
    return (not result.ok and result.failure_code in ('line_search_failure','nonconvergence')
        and result.evaluation is not None and result.scaled_residual_norm is not None
        and math.isfinite(result.scaled_residual_norm)
        and config.scaled_residual_tolerance<result.scaled_residual_norm<=controls['maximum_initial_scaled_residual'])


def recovery_seed(guess,config,controls):
    seed=tuple(x+d for x,d in zip(guess,controls['coordinate_offsets']))
    if len(seed)!=10 or not all(math.isfinite(x) and lo<=x<=hi
            for x,lo,hi in zip(seed,config.lower_bounds,config.upper_bounds)):
        raise ValueError('Recovery perturbation leaves the declared box; clipping is prohibited')
    return seed


def same_local_recovery(first,recovered,config,controls):
    delta=max(abs(x-y)/s for x,y,s in zip(first.coordinates,recovered.coordinates,config.coordinate_scales))
    same=(first.evaluation is not None and recovered.evaluation is not None
          and first.evaluation.branch_signature==recovered.evaluation.branch_signature)
    return (recovered.ok and recovered.iterations>0 and same and math.isfinite(delta)
            and delta<=controls['maximum_scaled_coordinate_difference']),delta,same


def run_candidate(plan, candidate_id, seed, hashes, root=ROOT, progress=None):
    verify_hashes(hashes, root)
    verify_hashes(seed['source_hashes'], root)
    if seed['objective_weight'] != 0. or seed['design_ranking_permitted'] is not False or seed['physical_limit_or_stability_claim'] is not False:
        raise ValueError('Unpromoted source seeds required')
    config = solver_config(plan)
    if fingerprint(asdict(config)) != fingerprint(seed['solver_config']):
        raise ValueError('Original seed solver controls must remain unchanged')
    if hashlib.sha256((root/'scripts/package_native_computational_envelope.py').read_bytes()).hexdigest() != seed['packager_sha256']:
        raise ValueError('Seed packager changed')
    candidate = next(c for c in plan['candidates'] if c['id'] == candidate_id)
    components = load_wufr_static_equilibrium_provider(**{k: root/v for k, v in plan['sources'].items()})
    if abs(components.gravity.total_mass_kg-plan['reference']['mass_kg']) > 1e-9:
        raise ValueError('Mass source differs from reference')
    source_tire = R25BDevelopmentCorneringTireProvider(accepted_assumption_id=SYMMETRY_ASSUMPTION_ID, policy=SYMMETRY_POLICY)
    report = dict(schema=SCHEMA, plan=plan, plan_fingerprint=fingerprint(plan), source_hashes=hashes,
        candidate_id=candidate_id, status='incomplete', objective_weight=0., design_ranking_permitted=False, cells=[])
    nominal = {}
    for assumption in sorted(plan['assumptions'], key=lambda a: a['id'] != 'nominal'):
        geometry = build_geometry(plan, candidate, assumption, components, root)
        tire = TireGainStress(source_tire, assumption['lateral_force_gain'])
        for state in plan['cases']:
            if assumption['id'] != 'nominal' and not state['assumption_study']:
                continue
            k = state['curvature_per_m']
            branch = next(b for b in seed['branches'] if b['direction_sign'] == (-1 if k < 0 else 1))
            saved = min((s for s in branch['attempts'] if s['ok']), key=lambda s: abs(s['signed_curvature_per_m']-k))
            guess = nominal.get(state['id'], tuple(saved['coordinates']))
            raw = dict(seed['fixed_case_controls'])
            for key in ('pressures_pa', 'accepted_assumptions'):
                raw[key] = tuple(raw[key])
            ref = plan['reference']
            raw.update(state_id=':'.join((plan['plan_id'], candidate_id, assumption['id'], state['id'])),
                configuration_id=geometry.components.source.configuration_id, geometry_revision=geometry.geometry_revision,
                setup_revision=geometry.setup_revision, tire_revision=tire.tire_revision,
                speed_m_s=ref['speed_mps'], curvature_per_m=k, pressures_pa=(ref['pressure_pa'],)*4,
                front_arb_setting=ref['front_arb_setting'], rear_arb_setting=ref['rear_arb_setting'])
            case = CorneringCase(**raw)
            result = solve_cornering(case, guess, geometry_provider=geometry, tire_provider=tire, config=config)
            recovery=None
            if recovery_eligible(result,config,plan['numerical_recovery']):
                first=result
                recovery={'first_initial_coordinates':guess,'first_result':asdict(first),
                          'attempted':False,'accepted_as_same_local_root':False}
                try:
                    retry_guess=recovery_seed(guess,config,plan['numerical_recovery'])
                except ValueError as error:
                    recovery['unavailable_reason']=str(error)
                else:
                    retry=solve_cornering(case,retry_guess,geometry_provider=geometry,tire_provider=tire,config=config)
                    accepted,delta,same=same_local_recovery(first,retry,config,plan['numerical_recovery'])
                    recovery.update(attempted=True,recovery_initial_coordinates=retry_guess,recovery_result=asdict(retry),
                        maximum_scaled_coordinate_difference=delta,same_source_branch=same,accepted_as_same_local_root=accepted)
                    if accepted:
                        result=retry
                        guess=retry_guess
            record = asdict(result)
            cell = dict(candidate_id=candidate_id, assumption_id=assumption['id'], case_id=state['id'],
                case=asdict(case), initial_coordinates=guess, result=record, metrics=metrics_from_record(record),
                branch_signature=None if result.evaluation is None else result.evaluation.branch_signature,
                geometry_revision=geometry.geometry_revision, setup_revision=geometry.setup_revision, tire_revision=tire.tire_revision,
                road_config=asdict(geometry.road.config), front_reference=asdict(geometry.road.wheel_profile.front),
                rear_reference=asdict(geometry.road.wheel_profile.rear),
                left_nominal_center_m=geometry._nominal['front_left'].center_m,
                left_tie_rod_length_m=geometry.road.steering_geometry.left.tie_rod_length,
                rack_origin_m=geometry.road.steering_geometry.rack.axis.point,
                physical_force_norm_n=None, physical_moment_norm_nm=None,numerical_recovery=recovery)
            if result.evaluation is not None:
                wrench = result.evaluation.physical_wrench
                cell.update(physical_force_norm_n=math.hypot(*wrench.resultant_force_N),
                            physical_moment_norm_nm=math.hypot(*wrench.resultant_moment_Nm))
            report['cells'].append(cell)
            if result.ok and assumption['id'] == 'nominal':
                nominal[state['id']] = result.coordinates
            if progress:
                progress(report, cell)
    verify_hashes(hashes, root)
    report['status'] = 'pass' if all(c['result']['ok'] for c in report['cells']) else 'fail'
    return report


def cell_key(cell):
    return cell['candidate_id'], cell['assumption_id'], cell['case_id']


def combine_reports(reports, root=ROOT, verify=True):
    if not reports:
        raise ValueError('Candidate reports required')
    first, cells, seen = reports[0], {}, set()
    plan = first['plan']
    if fingerprint(plan) != first['plan_fingerprint']:
        raise ValueError('Plan fingerprint mismatch')
    for report in reports:
        for key in ('schema', 'plan', 'plan_fingerprint', 'source_hashes', 'objective_weight', 'design_ranking_permitted'):
            if report[key] != first[key]:
                raise ValueError('Mixed source, plan or authority reports')
        if report['schema'] != SCHEMA or report['objective_weight'] != 0. or report['design_ranking_permitted'] is not False:
            raise ValueError('Unsupported report or authority promotion')
        candidate = report['candidate_id']
        if candidate in seen or candidate not in {c['id'] for c in plan['candidates']}:
            raise ValueError('Duplicate or unexpected candidate')
        seen.add(candidate)
        keys = [cell_key(c) for c in report['cells']]
        if len(set(keys)) != len(keys) or set(keys) != expected_cells(plan, candidate):
            raise ValueError('Missing, duplicate or unexpected cell coverage')
        if verify:
            verify_hashes(report['source_hashes'], root)
        if report['status'] != ('pass' if all(c['result']['ok'] for c in report['cells']) else 'fail'):
            raise ValueError('Inconsistent report status')
        for cell in report['cells']:
            case, result = cell['case'], cell['result']
            recovery=cell.get('numerical_recovery')
            if recovery is not None:
                first_attempt=recovery['first_result']
                norm=first_attempt['scaled_residual_norm']
                if (first_attempt['ok'] or first_attempt['failure_code'] not in ('line_search_failure','nonconvergence')
                        or first_attempt['case']!=case or norm is None or not math.isfinite(norm)
                        or not plan['solver']['scaled_residual_tolerance']<norm<=plan['numerical_recovery']['maximum_initial_scaled_residual']):
                    raise ValueError('Ineligible numerical recovery')
                if recovery['accepted_as_same_local_root']:
                    retry=recovery['recovery_result']
                    delta=max(abs(x-y)/s for x,y,s in zip(first_attempt['coordinates'],retry['coordinates'],plan['solver']['coordinate_scales']))
                    expected_seed=recovery_seed(tuple(recovery['first_initial_coordinates']),solver_config(plan),plan['numerical_recovery'])
                    if (not recovery['attempted'] or not retry['ok'] or retry['iterations']<=0 or not recovery['same_source_branch']
                            or retry['case']!=case or result!=retry or delta>plan['numerical_recovery']['maximum_scaled_coordinate_difference']
                            or tuple(recovery['recovery_initial_coordinates'])!=expected_seed
                            or tuple(cell['initial_coordinates'])!=expected_seed):
                        raise ValueError('Unverified recovery cannot supply accepted responses')
                elif result!=first_attempt:
                    raise ValueError('Rejected recovery changed the primary failed result')
            state = next(s for s in plan['cases'] if s['id'] == cell['case_id'])
            ref = plan['reference']
            if (case != result['case'] or case['curvature_per_m'] != state['curvature_per_m']
                    or case['speed_m_s'] != ref['speed_mps'] or list(case['pressures_pa']) != [ref['pressure_pa']]*4
                    or case['front_arb_setting'] != ref['front_arb_setting'] or case['rear_arb_setting'] != ref['rear_arb_setting']
                    or case['state_weight'] != 0. or case['result_role'] != 'evidence_only'
                    or any(case[k] != cell[k] for k in ('geometry_revision', 'setup_revision', 'tire_revision'))):
                raise ValueError('Cell differs from declared case/revisions')
            if result['ok']:
                for key, limit in (('physical_force_norm_n', 1e-6), ('physical_moment_norm_nm', 1e-6)):
                    if cell[key] is None or not math.isfinite(cell[key]) or cell[key] > limit:
                        raise ValueError('Accepted cell lacks physical closure')
                norm = result['scaled_residual_norm']
                if norm is None or not math.isfinite(norm) or norm > plan['solver']['scaled_residual_tolerance']:
                    raise ValueError('Accepted cell lacks numerical closure')
            if cell['metrics'] != metrics_from_record(result):
                raise ValueError('Metrics do not match solved evidence')
            if cell['metrics'] is not None and (set(cell['metrics']) != set(METRICS) or
                    not all(math.isfinite(v) for v in cell['metrics'].values())):
                raise ValueError('Invalid metrics')
            cells[cell_key(cell)] = cell
    if set(cells) != expected_cells(plan):
        raise ValueError('Incomplete candidate matrix')
    comparisons = []
    for (candidate, assumption, state), cell in cells.items():
        ref = cells['reference', assumption, state]
        comparable = cell['result']['ok'] and ref['result']['ok'] and cell['branch_signature'] == ref['branch_signature']
        comparisons.append(dict(candidate_id=candidate, assumption_id=assumption, case_id=state,
            comparison_supported=comparable, reason=None if comparable else
            ('solve_failed' if not cell['result']['ok'] or not ref['result']['ok'] else 'source_branch_changed'),
            delta_from_reference={m: cell['metrics'][m]-ref['metrics'][m] for m in METRICS} if comparable else None))
    effects = {cell_key(c): c for c in comparisons}
    stability = []
    for candidate in plan['candidates']:
        if candidate['id'] == 'reference':
            continue
        for state in plan['cases']:
            if not state['assumption_study']:
                continue
            group = [effects[candidate['id'], a['id'], state['id']] for a in plan['assumptions']]
            for metric, (_, unit, threshold) in METRICS.items():
                complete = all(c['comparison_supported'] for c in group)
                values = [c['delta_from_reference'][metric] for c in group] if complete else []
                signs = {0 if abs(v) <= threshold else (1 if v > 0 else -1) for v in values}
                status = ('unresolved_missing_or_incomparable' if not complete else
                    'below_reporting_threshold' if signs == {0} else 'stable_positive' if signs == {1}
                    else 'stable_negative' if signs == {-1} else 'sign_or_resolution_sensitive')
                stability.append(dict(candidate_id=candidate['id'], case_id=state['id'], metric=metric,
                    unit=unit, sign_threshold=threshold, coverage_complete=complete,
                    minimum_effect=min(values) if values else None, maximum_effect=max(values) if values else None, effect_sign=status))
    return dict(schema=SCHEMA, plan=plan, plan_fingerprint=first['plan_fingerprint'], source_hashes=first['source_hashes'],
        metric_definitions=METRICS, status='pass' if all(r['status'] == 'pass' for r in reports) else 'fail',
        objective_weight=0., design_ranking_permitted=False, cells=sorted(cells.values(), key=cell_key),
        comparisons=comparisons, candidate_effect_stability=stability)


def compact_report(report):
    keys=('ok','coordinates','failure_code','message','iterations','scaled_residual_norm','residual_history')
    cells=[]
    for cell in report['cells']:
        compact={**cell,'result':{k:cell['result'][k] for k in keys}}
        if cell.get('numerical_recovery') is not None:
            recovery=dict(cell['numerical_recovery'])
            for name in ('first_result','recovery_result'):
                if name in recovery:recovery[name]={k:recovery[name][k] for k in keys}
            compact['numerical_recovery']=recovery
        cells.append(compact)
    return {**report,'cells':cells}
