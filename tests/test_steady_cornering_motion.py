import math
import unittest

from pssd_vehicle.steady_cornering_motion import steady_cornering_motion, virtual_speed_hold


class SteadyCorneringMotionTests(unittest.TestCase):
    def test_rotating_heading_acceleration_matches_inertial_trajectory(self):
        # Differentiate the exact inertial-frame CG velocity then rotate back.
        for curvature in (-0.04, 0.04):
            beta, speed, dt = 0.23, 12.0, 1e-5
            motion = steady_cornering_motion(speed_m_s=speed, curvature_per_m=curvature,
                                             sideslip_rad=beta)
            r = speed * curvature
            derivative = tuple((speed * fn(beta + r*dt) - speed * fn(beta-r*dt))/(2*dt)
                               for fn in (math.cos, math.sin))
            for actual, expected in zip(motion.acceleration_m_s2, (*derivative, 0.0)):
                self.assertAlmostEqual(actual, expected, places=8)
            ax, ay, _ = motion.acceleration_m_s2
            self.assertAlmostEqual(math.hypot(ax, ay), speed**2*abs(curvature))
            self.assertAlmostEqual(ax*motion.forward_velocity_m_s +
                                   ay*motion.lateral_velocity_m_s, 0.0)

    def test_zero_curvature_and_explicit_holder_power(self):
        motion = steady_cornering_motion(speed_m_s=8, curvature_per_m=0, sideslip_rad=-0.31)
        self.assertEqual(motion.acceleration_m_s2, (0.0, 0.0, 0.0))
        for force in (-17, 0, 17):
            hold = virtual_speed_hold(motion, force_n=force,
                                      policy="virtual_tangential_force_at_current_total_cg")
            dot = sum(f*v for f,v in zip(hold.force_heading_n,
                      (motion.forward_velocity_m_s, motion.lateral_velocity_m_s, 0)))
            self.assertAlmostEqual(hold.power_w, dot)
            self.assertEqual(hold.power_w, force*8)
        with self.assertRaises(ValueError):
            virtual_speed_hold(motion, force_n=1, policy="drivetrain")

    def test_rejects_invalid_inputs_and_overflow(self):
        for speed, curvature, beta in ((0,0,0),(-1,0,0),(math.nan,0,0),
                                       (1,math.inf,0),(1,0,math.nan),(1e308,1e308,0)):
            with self.assertRaises(ValueError):
                steady_cornering_motion(speed_m_s=speed, curvature_per_m=curvature,
                                         sideslip_rad=beta)


class ManeuverInertiaTests(unittest.TestCase):
    def test_resultant_and_moment_about_current_cg(self):
        from pssd_vehicle.steady_cornering_motion import CurrentMassPoint, maneuver_inertia
        motion = steady_cornering_motion(speed_m_s=11, curvature_per_m=-0.03, sideslip_rad=0.19)
        points = (CurrentMassPoint("synthetic_sprung", 73, (0.2, 0.1, 0.5)),
                  CurrentMassPoint("synthetic_wheel", 7, (-0.9, -0.7, 0.2)))
        result = maneuver_inertia(motion, mass_points=points,
                                  policy="uniform_acceleration_current_mass_lumps")
        for i in range(3):
            self.assertAlmostEqual(sum(f[i] for f in result.forces_heading_n),
                                   -80*motion.acceleration_m_s2[i])
        moment = [0., 0., 0.]
        for p, f in zip(points, result.forces_heading_n):
            d = tuple(x-c for x,c in zip(p.position_heading_m, result.current_total_cg_heading_m))
            cross = (d[1]*f[2]-d[2]*f[1], d[2]*f[0]-d[0]*f[2], d[0]*f[1]-d[1]*f[0])
            moment = [m+c for m,c in zip(moment,cross)]
        for m in moment:
            self.assertAlmostEqual(m, 0., places=12)
        self.assertEqual(result.mass_source_ids, ("synthetic_sprung", "synthetic_wheel"))

    def test_requires_mass_and_policy_authority(self):
        from pssd_vehicle.steady_cornering_motion import CurrentMassPoint, maneuver_inertia
        motion = steady_cornering_motion(speed_m_s=1, curvature_per_m=0, sideslip_rad=0)
        for points in ((), (CurrentMassPoint("",1,(0,0,0)),),
                       (CurrentMassPoint("x",-1,(0,0,0)),),
                       (CurrentMassPoint("x",1,(0,0,0)),)*2):
            with self.assertRaises(ValueError):
                maneuver_inertia(motion,mass_points=points,
                                 policy="uniform_acceleration_current_mass_lumps")
        with self.assertRaises(ValueError):
            maneuver_inertia(motion, mass_points=(CurrentMassPoint("x",1,(0,0,0)),),policy="gravity_only")
