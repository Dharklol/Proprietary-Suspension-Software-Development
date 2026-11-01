from dataclasses import replace
from pathlib import Path
import math
import unittest
from pssd_suspension import load_optimumk_geometry_snapshot, load_wufr26_wheel_reference_profile, build_nominal_wheel_reference
from pssd_suspension.spring_force import load_wufr27_spring_package
from pssd_suspension.native_spring_port import bind_front_spring_port
from pssd_suspension.generalized_forces import evaluate_ports
from pssd_suspension.geometry import ActuationAttachment

ROOT=Path(__file__).resolve().parents[1]


class NativeSpringPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry=load_optimumk_geometry_snapshot(ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml')
        cls.wheel=load_wufr26_wheel_reference_profile(ROOT/'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml')
        cls.package=load_wufr27_spring_package(ROOT/'data_catalog/wufr27_spring_package_v0.toml')

    def bind(self,side,q):
        return bind_front_spring_port(self.geometry.corner('front',side),build_nominal_wheel_reference(self.wheel,'front',side),self.package,q,
            geometry_id=self.geometry.geometry_id,source_authority=self.geometry.authority)

    def test_reference_and_authority(self):
        b=self.bind('left',0.)
        self.assertAlmostEqual(b.port.deformation_m,.1857-b.actuation_state.current_coilover_length_m,places=14)
        self.assertAlmostEqual(b.spring_state.force_N,759.6235061219563,places=7)
        self.assertFalse(b.installed_as_built_authority)
        self.assertIn('ASM-SUSP-0002',b.assumption_ids)

    def test_energy_gradient_independent(self):
        q=.02;h=.0001;b=self.bind('left',q)
        force=evaluate_ports((b.port,),(0.,)*4).generalized_force[2]
        numerical=-(self.bind('left',q+h).spring_state.stored_energy_J-self.bind('left',q-h).spring_state.stored_energy_J)/(2*h)
        self.assertAlmostEqual(force,numerical,delta=1e-4)

    def test_reflection_and_rigid_motion(self):
        left=self.bind('left',.02);right=self.bind('right',-.02)
        self.assertAlmostEqual(left.port.deformation_m,right.port.deformation_m,places=12)
        self.assertAlmostEqual(left.port.gradient[2],-right.port.gradient[3],places=12)
        self.assertEqual(left.port.gradient[:2],(0.,0.))
        self.assertEqual(evaluate_ports((left.port,),(2.,3.,0.,0.)).dissipation_W,0.)

    def test_source_and_coordinate_rejections(self):
        front=self.geometry.corner('front','left');nominal=build_nominal_wheel_reference(self.wheel,'front','left')
        for q,gid in ((math.nan,self.geometry.geometry_id),(0.,'')):
            with self.assertRaises(ValueError):
                bind_front_spring_port(front,nominal,self.package,q,geometry_id=gid,source_authority=self.geometry.authority)
        with self.assertRaisesRegex(ValueError,'Front linear'):
            bind_front_spring_port(self.geometry.corner('rear','left'),nominal,self.package,0.,geometry_id=self.geometry.geometry_id,source_authority=self.geometry.authority)
        altered=replace(front,actuation=replace(front.actuation,attachment=ActuationAttachment.LOWER_ARM))
        with self.assertRaises(ValueError):
            bind_front_spring_port(altered,nominal,self.package,0.,geometry_id=self.geometry.geometry_id,source_authority=self.geometry.authority)


if __name__=='__main__': unittest.main()
