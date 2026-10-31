from dataclasses import dataclass
import unittest

from pssd_vehicle.steady_cornering import CorneringSolveResult
from scripts.run_native_computational_envelope import EnvelopeControls, failure_category, map_branch
from tests.steady_cornering_fixture import case, config, initial
from scripts.package_native_computational_envelope import SCOPE, combine_reports, compact_summary


@dataclass(frozen=True)
class SignatureOnlyEvaluation:
    branch_signature: tuple[str,...]


def stub_result(c,guess,ok=True,code=None,signature=('geometry','direct_nonnegative_IA:central')):
    return CorneringSolveResult(ok,c,tuple(guess),SignatureOnlyEvaluation(signature),
        0,0.,1.,(),(),code,'manufactured orchestration fixture')


class NativeEnvelopeOrchestrationTests(unittest.TestCase):
    def run_branch(self,solver,**changes):
        controls=changes.pop('controls',EnvelopeControls((.02,.04,.08),3,.001))
        return map_branch(case(),initial(),direction_sign=changes.pop('direction_sign',1),
            controls=controls,geometry_provider=None,tire_provider=None,config=config(),
            solver=solver,**changes)

    def test_refinement_keeps_first_failure_and_uses_only_accepted_warm_starts(self):
        calls=[]
        def solver(c,guess,**kwargs):
            calls.append((c,guess))
            accepted=abs(c.curvature_per_m)<.05
            coordinates=tuple(guess) if not accepted else (c.curvature_per_m,*guess[1:])
            return stub_result(c,coordinates,accepted,None if accepted else 'line_search_failure')
        run=self.run_branch(solver)
        self.assertEqual(run.first_coarse_failure_magnitude_per_m,.08)
        self.assertLess(run.last_accepted_magnitude_per_m,.05)
        self.assertGreaterEqual(run.first_failed_magnitude_per_m,.05)
        self.assertEqual(len(run.attempts),7)
        self.assertTrue(any(a.stage=='coarse' and not a.result.ok for a in run.attempts))
        self.assertEqual(run.attempts[3].category,'numerical_or_derivative_failure')
        for c,guess in calls[4:]:
            self.assertLess(guess[0],.05)
        self.assertTrue(all(c.configuration_id==calls[0][0].configuration_id for c,_ in calls))

    def test_successful_grid_end_is_not_a_failure_or_physical_limit(self):
        run=self.run_branch(lambda c,g,**kw:stub_result(c,g),direction_sign=-1)
        self.assertEqual(run.stopping_reason,'grid_end_no_failure')
        self.assertIsNone(run.first_failed_magnitude_per_m)
        self.assertEqual(run.last_accepted_magnitude_per_m,.08)
        self.assertTrue(all(a.result.case.curvature_per_m<=0 for a in run.attempts))

    def test_successful_alternate_reflection_branch_is_rejected_and_retained(self):
        def solver(c,g,**kw):
            signature=('geometry','direct_nonnegative_IA:central' if abs(c.curvature_per_m)<.03
                       else 'reflected_negative_IA:central')
            return stub_result(c,g,signature=signature)
        run=self.run_branch(solver)
        failed=[a for a in run.attempts if not a.result.ok]
        self.assertTrue(failed)
        self.assertTrue(all(a.category=='confirmed_reflection_boundary' for a in failed))
        self.assertTrue(all(a.result.failure_code=='branch_change' for a in failed))

    def test_seed_failure_stops_without_inventing_an_accepted_interval(self):
        run=self.run_branch(lambda c,g,**kw:stub_result(c,g,False,'road_root_unbracketed'))
        self.assertEqual(run.stopping_reason,'seed_failure')
        self.assertEqual(len(run.attempts),1)
        self.assertIsNone(run.last_accepted_magnitude_per_m)

    def test_terminal_numerical_failure_is_not_reclassified_by_rejected_tire_trials(self):
        from dataclasses import replace
        r=replace(stub_result(case(),initial(),False,'line_search_failure'),
                  trial_failures=(('slip_out_of_domain','rejected trial'),))
        self.assertEqual(failure_category(r),'numerical_or_derivative_failure')
        self.assertEqual(failure_category(replace(r,failure_code='operating_state_out_of_domain')),
                         'tire_source_domain')
        self.assertEqual(failure_category(replace(r,failure_code='unknown_source_code')),
                         'unclassified_failure')

    def test_invalid_controls_fail_before_a_solver_call(self):
        for values in ((0.,.01),(.02,.01),(.01,.01),(float('nan'),)):
            with self.assertRaises(ValueError):EnvelopeControls(values,3,.001)
        with self.assertRaises(ValueError):EnvelopeControls((.01,),-1,.001)
        with self.assertRaises(ValueError):EnvelopeControls((.01,),1,0.)


def packaging_fixture(sign):
    from dataclasses import asdict
    c=asdict(case(sign*.02))
    point={'stage':'coarse','ok':True,'category':'accepted','failure_code':None,
        'signed_curvature_per_m':sign*.02,'coordinates':[0.]*10,
        'initial_coordinates':[0.]*10,'coordinate_bound_margins':[[.3,.4],[.0001,.3]]+[[1.,1.]]*8}
    branch={'direction_sign':sign,'attempts':[point]}
    summary={'status':'pass','scope':SCOPE,'controls':{'grid':[.02]},
        'solver_config':{'coordinate_scales':[1.,.01]+[1.]*8},
        'geometry_revision':'geometry','setup_revision':'setup','tire_revision':'tire',
        'source_hashes':{},'status_meaning':'manufactured_packaging_fixture',
        'objective_weight':0.,'design_ranking_permitted':False,
        'physical_limit_or_stability_claim':False,'branches':[branch]}
    return {'summary':summary,'branches':[{'direction_sign':sign,'attempts':[{
        'stage':'coarse','category':'accepted','initial_coordinates':[0.]*10,
        'result':{'ok':True,'failure_code':None,'case':c,'coordinates':[0.]*10}}]}]}


class NativeEnvelopePackagingTests(unittest.TestCase):
    def test_merge_keeps_explicit_controls_and_normalizes_bound_distances(self):
        result=combine_reports([packaging_fixture(1),packaging_fixture(-1)])
        self.assertEqual([b['direction_sign'] for b in result['branches']],[-1,1])
        self.assertEqual(result['fixed_case_controls']['speed_m_s'],8.)
        bound=compact_summary(result)['branches'][0]['attempts'][0]['closest_normalized_solver_bound']
        self.assertEqual(bound['axis'],'roll_rad')
        self.assertAlmostEqual(bound['dimensionless_margin'],.01)
        self.assertFalse(result['physical_limit_or_stability_claim'])

    def test_mixed_sources_pressure_identity_and_authority_are_rejected(self):
        bad=packaging_fixture(1)
        bad['summary']['tire_revision']='other'
        with self.assertRaises(ValueError):combine_reports([packaging_fixture(-1),bad])
        bad=packaging_fixture(1)
        bad['branches'][0]['attempts'][0]['result']['case']['pressures_pa']=[80000.]*4
        with self.assertRaises(ValueError):combine_reports([packaging_fixture(-1),bad])
        bad=packaging_fixture(1)
        bad['summary']['objective_weight']=1.
        with self.assertRaises(ValueError):combine_reports([packaging_fixture(-1),bad])
        bad=packaging_fixture(1)
        bad['summary']['branches'][0]['attempts'][0]['coordinates'][0]=1.
        with self.assertRaises(ValueError):combine_reports([packaging_fixture(-1),bad])
        with self.assertRaises(ValueError):combine_reports([packaging_fixture(1),packaging_fixture(1)])


if __name__=='__main__':unittest.main()
