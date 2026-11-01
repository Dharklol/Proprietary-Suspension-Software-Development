from copy import deepcopy
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest

from pssd_vehicle.analytical_workflow import (
    ROOT, DEFAULT_PLAN, SCHEMA, TireGainStress, build_geometry, combine_reports,
    expected_cells, fingerprint, load_plan, metrics_from_record, verify_hashes,
)
from pssd_vehicle.steady_cornering import CorneringTireQuery, CorneringTireResponse
from pssd_vehicle.wufr_static_equilibrium import load_wufr_static_equilibrium_provider, evaluate_wufr_suspension_composition
from pssd_steering import solve_corner_position


def manufactured_reports(plan):
    reports = []
    for candidate in plan['candidates']:
        report = dict(schema=SCHEMA, plan=deepcopy(plan), plan_fingerprint=fingerprint(plan), source_hashes={},
            candidate_id=candidate['id'], status='pass', objective_weight=0., design_ranking_permitted=False, cells=[])
        for cid, aid, sid in sorted(expected_cells(plan, candidate['id'])):
            state = next(s for s in plan['cases'] if s['id'] == sid)
            case = dict(curvature_per_m=state['curvature_per_m'], speed_m_s=plan['reference']['speed_mps'],
                pressures_pa=[plan['reference']['pressure_pa']]*4, front_arb_setting=1, rear_arb_setting=1,
                state_weight=0., result_role='evidence_only', geometry_revision=cid+aid, setup_revision=cid+aid, tire_revision=aid)
            q = [0.]*10
            q[4] = 0. if cid == 'reference' else (-.001 if aid == 'front_toe_minus' else .002)
            angle = 0. if cid == 'reference' else .01
            result = dict(ok=True, case=deepcopy(case), coordinates=q, scaled_residual_norm=1e-12,
                evaluation={'geometry': {'wheels': [dict(corner_id='front_left', forward_heading=(math.cos(angle),math.sin(angle),0.)),
                    dict(corner_id='front_right', forward_heading=(1.,0.,0.))]}},
                iterations=2, failure_code=None, message='', residual_history=[.1,1e-12])
            report['cells'].append(dict(candidate_id=cid, assumption_id=aid, case_id=sid, case=case, result=result,
                metrics=metrics_from_record(result), physical_force_norm_n=1e-8, physical_moment_norm_nm=1e-8,
                geometry_revision=case['geometry_revision'], setup_revision=case['setup_revision'], tire_revision=aid,
                branch_signature=['same_connected_branch']))
        reports.append(report)
    return reports


class AnalyticalWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = load_plan(ROOT/DEFAULT_PLAN)
        cls.components = load_wufr_static_equilibrium_provider(**{k: ROOT/v for k,v in cls.plan['sources'].items()})

    def test_explicit_crossed_matrix(self):
        self.assertEqual(len(expected_cells(self.plan)), 51)
        self.assertTrue(all(len(expected_cells(self.plan,c['id'])) == 17 for c in self.plan['candidates']))

    def test_rack_candidates_preserve_axes_pickups_and_center_closure(self):
        original = self.components.road_contact.steering_geometry
        for candidate in self.plan['candidates'][1:]:
            g = build_geometry(self.plan,candidate,self.plan['assumptions'][0],self.components).road.steering_geometry
            self.assertAlmostEqual(g.rack.axis.point[0]-original.rack.axis.point[0],candidate['rack_longitudinal_offset_m'])
            for side in ('left','right'):
                self.assertEqual(getattr(g,side).steering_axis,getattr(original,side).steering_axis)
                self.assertEqual(getattr(g,side).outer_tie_rod_joint_at_center,getattr(original,side).outer_tie_rod_joint_at_center)
                result=solve_corner_position(g,side,0.)
                self.assertTrue(result.ok)
                self.assertLess(abs(result.upright_rotation),1e-10)
            self.assertEqual(g.left.tie_rod_length,g.right.tie_rod_length)

    def test_alignment_construction_and_configuration_binding(self):
        base=build_geometry(self.plan,self.plan['candidates'][0],self.plan['assumptions'][0],self.components)
        a=next(a for a in self.plan['assumptions'] if a['id']=='front_camber_plus')
        changed=build_geometry(self.plan,self.plan['candidates'][0],a,self.components)
        f=changed.road.wheel_profile.front
        self.assertEqual(changed._nominal['front_left'].center_m,(0.,f.half_track_m+f.tire_radius_m*math.sin(f.static_camber_rad),f.tire_radius_m*math.cos(f.static_camber_rad)))
        self.assertNotEqual(base.geometry_revision,changed.geometry_revision)
        self.assertNotEqual(base.setup_revision,changed.setup_revision)
        c=changed.components
        for provider in (c.road_contact.source,c.gravity,c.spring_package,c.spring_package.front,c.spring_package.reference,c.front_zbar_fixture,c.rear_zbar_fixture):
            self.assertEqual(provider.configuration_id,c.source.configuration_id)
        result=evaluate_wufr_suspension_composition(c,(0.,)*4,front_arb_setting=1,rear_arb_setting=1)
        self.assertTrue(result.ok,result.message)
        self.assertIs(changed.road.suspension_geometry,self.components.road_contact.suspension_geometry)
        self.assertIs(changed.road.wheel_profile.rear,self.components.road_contact.wheel_profile.rear)
        self.assertEqual(self.components.road_contact.config.road_gap_tolerance_m,1e-13)

    def test_tire_stress_keeps_unscaled_query_force_and_branch(self):
        class Source:
            tire_revision='original'
            def __call__(self,q):
                self.query=q
                return CorneringTireResponse(q,123.,('original_measurement',),'central')
        source=Source();wrapper=TireGainStress(source,1.05)
        q=CorneringTireQuery('s','front_left','source','intended',wrapper.tire_revision,'convention',.03,500.,-.02,68900.)
        r=wrapper(q)
        self.assertAlmostEqual(r.lateral_force_n,129.15)
        self.assertEqual(source.query,replace(q,tire_revision='original'))
        self.assertEqual(r.query,q)
        self.assertEqual(r.branch_id,'central')
        self.assertIn('unscaled_source_lateral_force_n:123.0',r.source_ids)
        self.assertEqual(TireGainStress(source,1.).tire_revision,'original')

    def test_paired_candidate_effects_retain_sign_sensitivity(self):
        r=combine_reports(manufactured_reports(self.plan),verify=False)
        self.assertTrue(all(s['effect_sign']=='sign_or_resolution_sensitive' for s in r['candidate_effect_stability'] if s['metric']=='rack_m'))
        self.assertTrue(all(s['effect_sign']=='stable_positive' for s in r['candidate_effect_stability'] if s['metric']=='front_heading_split_rad'))

    def test_failure_and_branch_change_remain_unavailable(self):
        for failure in (True,False):
            reports=manufactured_reports(self.plan)
            cell=next(c for c in reports[1]['cells'] if c['assumption_id']=='front_toe_minus')
            if failure:
                cell['result']['ok']=False;cell['metrics']=None;reports[1]['status']='fail'
            else:cell['branch_signature']=['different_reflection_branch']
            r=combine_reports(reports,verify=False)
            paired=next(c for c in r['comparisons'] if all(c[k]==cell[k] for k in ('candidate_id','assumption_id','case_id')))
            self.assertIsNone(paired['delta_from_reference'])
            self.assertTrue(all(not s['coverage_complete'] and s['minimum_effect'] is None for s in r['candidate_effect_stability'] if s['candidate_id']==cell['candidate_id'] and s['case_id']==cell['case_id']))

    def test_packaging_rejects_bad_coverage_source_authority_case_and_closure(self):
        def missing(r):r[1]['cells'].pop()
        def duplicate(r):r[1]['cells'].append(deepcopy(r[1]['cells'][0]))
        def mixed(r):r[1]['source_hashes']['different']='sha'
        def promoted(r):r[1]['design_ranking_permitted']=True
        def wrong_case(r):r[1]['cells'][0]['case']['speed_m_s']=12.
        def bad_force(r):r[1]['cells'][0]['physical_force_norm_n']=float('nan')
        def fake_success(r):r[1]['cells'][0]['result']['scaled_residual_norm']=2e-10
        def fake_metric(r):r[1]['cells'][0]['metrics']['rack_m']=99.
        for change in (missing,duplicate,mixed,promoted,wrong_case,bad_force,fake_success,fake_metric):
            reports=manufactured_reports(self.plan);change(reports)
            with self.subTest(change=change.__name__),self.assertRaises(ValueError):combine_reports(reports,verify=False)

    def test_source_hash_change_rejected(self):
        with self.assertRaises(ValueError):verify_hashes({DEFAULT_PLAN:'wrong_hash'})

    def test_report_embedded_content_escaped(self):
        from pssd_viz.analytical_workflow_report import render_comparison_html
        r=combine_reports(manufactured_reports(self.plan),verify=False)
        r['plan']['design_question']='</script><script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as directory:
            html=render_comparison_html(r,Path(directory)/'report.html').read_text()
        self.assertNotIn('</script><script>alert',html)
        self.assertIn('\\u003c/script',html)
        self.assertNotIn('innerHTML',html)


if __name__=='__main__':unittest.main()
