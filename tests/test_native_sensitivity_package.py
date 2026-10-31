from copy import deepcopy
import unittest

from scripts.package_native_sensitivity_study import combine_signed_reports


def fixture(sign,recovery=False):
    r={'status':'pass','scope':'manufactured_packaging_fixture','controls':{},
       'source_hashes':{},'stored_seed_revisions':{},'current_provider_revisions':{},
       'controls_sha256':'control','seed_report_sha256':'seed','objective_weight':0.,
       'physical_or_ranking_authority':False,'coordinate_order':[],'coordinate_offsets':[],
       'difference_limit':1e-5,'recovery_controls_sha256':'recovery_control'}
    r.update(road_gap_tolerance_m=1e-14,comparison_road_gap_tolerance_m=5e-15,
        geometry_revision='physical_geometry',primary_precision_setup_revision='precision_1',
        comparison_precision_setup_revision='precision_2')
    d={'direction_sign':sign}
    if recovery:d['variants']=[{}, {}, {}, {}]
    else:
        d['physical']=[{'tag':str(i)} for i in range(7)]
        d['numerical']=[{'tag':t} for t in ('numerical_anchor','wider_sideslip_box','half_fd_steps')]
    r['directions']=[d]
    return r


class NativeSensitivityPackageTests(unittest.TestCase):
    def test_both_directions_and_separate_experiments_are_preserved(self):
        report=combine_signed_reports([fixture(1),fixture(-1)],[fixture(-1,True),fixture(1,True)])
        self.assertEqual(report['status'],'pass')
        self.assertEqual([d['direction_sign'] for d in report['study']['directions']],[-1,1])
        self.assertEqual([d['direction_sign'] for d in report['off_root_recovery']['directions']],[-1,1])
        self.assertFalse(report['physical_or_ranking_authority'])

    def test_duplicate_mixed_controls_and_promoted_reports_are_rejected(self):
        studies=[fixture(-1),fixture(1)]; recoveries=[fixture(-1,True),fixture(1,True)]
        for field,value in (('source_hashes',{'changed':'hash'}),('controls_sha256','changed'),
                             ('objective_weight',1.)):
            bad=deepcopy(studies);bad[1][field]=value
            with self.assertRaises(ValueError):combine_signed_reports(bad,recoveries)
        with self.assertRaises(ValueError):combine_signed_reports([fixture(1),fixture(1)],recoveries)

    def test_missing_cases_fail_and_valid_failed_experiment_stays_failed(self):
        studies=[fixture(-1),fixture(1)];recoveries=[fixture(-1,True),fixture(1,True)]
        bad=deepcopy(studies);bad[1]['directions'][0]['physical'].pop()
        with self.assertRaises(ValueError):combine_signed_reports(bad,recoveries)
        recoveries[1]['status']='fail'
        self.assertEqual(combine_signed_reports(studies,recoveries)['status'],'fail')


if __name__=='__main__':unittest.main()
