from types import SimpleNamespace
from copy import deepcopy
import unittest
from pssd_vehicle.analytical_workflow import (
    ROOT,DEFAULT_PLAN,load_plan,solver_config,recovery_eligible,recovery_seed,same_local_recovery,combine_reports,
)


class AnalyticalNumericalRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        plan=load_plan(ROOT/DEFAULT_PLAN)
        cls.config=solver_config(plan);cls.controls=plan['numerical_recovery']

    def result(self,**changes):
        values=dict(ok=False,failure_code='line_search_failure',scaled_residual_norm=1.3e-10,
            coordinates=(0.,0.,0.,0.,0.,0.,500.,500.,500.,500.),iterations=3,
            evaluation=SimpleNamespace(branch_signature=('same_branch',)))
        values.update(changes)
        return SimpleNamespace(**values)

    def test_only_near_root_numerical_failures_are_eligible(self):
        self.assertTrue(recovery_eligible(self.result(),self.config,self.controls))
        for changes in ({'ok':True},{'failure_code':'tire_domain_failure'},
                {'scaled_residual_norm':1e-5},{'scaled_residual_norm':float('nan')},
                {'scaled_residual_norm':None},{'evaluation':None}):
            self.assertFalse(recovery_eligible(self.result(**changes),self.config,self.controls))

    def test_common_seed_is_explicit_and_cannot_be_clipped(self):
        base=self.result().coordinates
        changed=recovery_seed(base,self.config,self.controls)
        self.assertEqual(changed,tuple(x+d for x,d in zip(base,self.controls['coordinate_offsets'])))
        bad=list(base);bad[0]=self.config.upper_bounds[0]
        with self.assertRaises(ValueError):recovery_seed(tuple(bad),self.config,self.controls)

    def test_success_requires_iteration_same_branch_and_same_local_root(self):
        first=self.result()
        self.assertTrue(same_local_recovery(first,self.result(ok=True),self.config,self.controls)[0])
        for changes in ({'ok':False},{'ok':True,'iterations':0},
                {'ok':True,'evaluation':SimpleNamespace(branch_signature=('different',))},
                {'ok':True,'coordinates':(.001,0.,0.,0.,0.,0.,500.,500.,500.,500.)}):
            self.assertFalse(same_local_recovery(first,self.result(**changes),self.config,self.controls)[0])

    def test_packager_requires_declared_seed_and_valid_recovery_proof(self):
        from tests.test_analytical_design_workflow import manufactured_reports
        plan=load_plan(ROOT/DEFAULT_PLAN);reports=manufactured_reports(plan)
        cell=reports[1]['cells'][0]
        original=deepcopy(cell['result']);original.update(ok=False,failure_code='line_search_failure',scaled_residual_norm=1.3e-10)
        guess=(0.,0.,0.,0.,0.,0.,500.,500.,500.,500.)
        seed=recovery_seed(guess,self.config,self.controls)
        cell['initial_coordinates']=seed
        cell['numerical_recovery']={'first_result':original,'first_initial_coordinates':guess,
            'recovery_result':deepcopy(cell['result']),'recovery_initial_coordinates':seed,
            'attempted':True,'accepted_as_same_local_root':True,'same_source_branch':True}
        self.assertEqual(combine_reports(reports,verify=False)['status'],'pass')
        for key,value in [('same_source_branch',False),('recovery_initial_coordinates',guess)]:
            altered=deepcopy(reports);altered[1]['cells'][0]['numerical_recovery'][key]=value
            with self.assertRaises(ValueError):combine_reports(altered,verify=False)


if __name__=='__main__':unittest.main()
