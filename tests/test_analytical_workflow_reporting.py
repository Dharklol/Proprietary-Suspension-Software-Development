from copy import deepcopy
import unittest

from scripts.package_analytical_design_workflow import add_assumption_responses
from pssd_vehicle.analytical_workflow import ROOT, DEFAULT_PLAN, load_plan, combine_reports
from tests.test_analytical_design_workflow import manufactured_reports


class AssumptionResponseReportingTests(unittest.TestCase):
    def test_pairs_same_candidate_and_operating_case(self):
        plan = load_plan(ROOT/DEFAULT_PLAN)
        report = add_assumption_responses(combine_reports(manufactured_reports(plan), verify=False))
        changed = next(r for r in report['assumption_responses'] if r['candidate_id']=='rack_aft_5mm'
            and r['assumption_id']=='front_toe_minus' and r['case_id']=='left_high')
        self.assertTrue(changed['comparison_supported'])
        self.assertAlmostEqual(changed['delta_from_nominal']['rack_m'], -.003)
        self.assertEqual(changed['delta_from_nominal']['front_heading_split_rad'], 0.)

    def test_branch_transition_and_failure_cannot_become_zero_sensitivity(self):
        plan = load_plan(ROOT/DEFAULT_PLAN)
        base = combine_reports(manufactured_reports(plan), verify=False)
        for failure in (True, False):
            report = deepcopy(base)
            cell = next(c for c in report['cells'] if c['assumption_id']=='front_toe_minus')
            if failure:
                cell['result']['ok'] = False
                cell['metrics'] = None
            else:
                cell['branch_signature'] = ['changed_branch']
            response = next(r for r in add_assumption_responses(report)['assumption_responses']
                if all(r[k]==cell[k] for k in ('candidate_id','assumption_id','case_id')))
            self.assertFalse(response['comparison_supported'])
            self.assertIsNone(response['delta_from_nominal'])


if __name__ == '__main__':
    unittest.main()
