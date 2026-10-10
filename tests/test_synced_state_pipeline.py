from dataclasses import replace
import unittest

import test_motion_aware_force_demand_targets as fixtures
from pssd_vehicle.operating_states import (
    TurnDirection, VehicleOperatingState, VehicleStateRole, VehicleStateError,
    WheelOperatingState, WheelPosition,
)
from pssd_vehicle.synced_state import (
    CANONICAL_FRAME, StateSourceStamp, SyncedStateSweep, compose_synced_state_sample,
)
from pssd_vehicle.synced_tire_readiness import (
    magnitude_branch_readiness, signed_runtime_readiness,
)
from pssd_tire.steady_state_lateral_benchmarks import (
    peak_post_peak_table, SYNTHETIC_SOURCE, CANONICAL_CONVENTION,
)
from pssd_steering.optimization.synced_state_targets import build_synced_sweep_target_set
from pssd_steering.optimization.targets import TargetDefinitionError


class SyncedPipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.MotionAwareForceDemandTargetTests()
        self.fixture.setUp()
        f = self.fixture
        schedule = f._motion_schedule("nominal", -f.planar_geometry.cg_to_rear_axle_m)
        samples = []
        for index, (rack, motion) in enumerate(zip(f.sampling.rack_displacements, schedule.samples)):
            wheels = []
            for position in WheelPosition:
                inside = ((position is WheelPosition.FRONT_LEFT and motion.turn_direction is not TurnDirection.RIGHT)
                          or (position is WheelPosition.FRONT_RIGHT and motion.turn_direction is TurnDirection.RIGHT))
                point = f.inside_point if inside else f.outside_point
                force = f.inside_force[index] if inside else f.outside_force[index]
                sign = -1.0 if motion.turn_direction is TurnDirection.RIGHT else 1.0
                wheels.append(WheelOperatingState(position, point.normal_load_n,
                                                  point.inclination_deg, point.pressure_kpa,
                                                  sign * force))
            vehicle = VehicleOperatingState(
                "nominal", VehicleStateRole.DESIGN_INPUT, motion.turn_direction,
                0.0, 0.0, motion.body_speed_mps, tuple(wheels), state_weight=1.0,
                suspension_pose_state_id="nominal", authority="synthetic software test only",
            )
            stamp = StateSourceStamp("synthetic", "nominal", f"sample_{index}", "v1",
                                     CANONICAL_FRAME, "synthetic_fixture", "v1",
                                     "synthetic software test only", "synthetic")
            samples.append(compose_synced_state_sample(
                rack_displacement_m=rack, vehicle=vehicle, pose=f.pose_set.state("nominal"),
                motion=motion, vehicle_source=stamp, pose_source=stamp, motion_source=stamp,
            ))
        self.sweep = SyncedStateSweep("synthetic_sweep", tuple(f.sampling.rack_displacements),
                                      tuple(samples), "synthetic software test only")

    def target(self, sweep=None):
        f = self.fixture
        return build_synced_sweep_target_set(
            sweep or self.sweep, f.sampling, f.pose_set, f.planar_geometry, f.branch_set,
            target_set_id="synthetic_synced", version="0.1.0", normalization_scale_deg=1.0,
        )

    def test_ordered_sweep_matches_existing_motion_target_oracle(self):
        f = self.fixture
        expected = fixtures.build_motion_aware_force_demand_operating_target_set(
            f.sampling, f.pose_set, f.planar_geometry, f.branch_set,
            (f._definition("nominal", -f.planar_geometry.cg_to_rear_axle_m),),
            target_set_id="oracle", version="0.1.0", authority="synthetic",
        )
        actual = self.target()
        self.assertEqual(actual.state_targets[0].left_outputs, expected.state_targets[0].left_outputs)
        self.assertEqual(actual.state_targets[0].right_outputs, expected.state_targets[0].right_outputs)
        self.assertEqual(self.sweep.motion_schedule().samples,
                         tuple(sample.motion for sample in self.sweep.samples))

    def test_reordered_grid_and_duplicate_ids_reject(self):
        with self.assertRaises(VehicleStateError):
            replace(self.sweep, samples=tuple(reversed(self.sweep.samples)))
        sample = self.sweep.samples[1]
        stamp = replace(sample.vehicle_source, sample_id=self.sweep.samples[0].vehicle_source.sample_id)
        bad = replace(sample, vehicle_source=stamp, pose_source=stamp, motion_source=stamp)
        with self.assertRaises(VehicleStateError):
            replace(self.sweep, samples=(self.sweep.samples[0], bad, *self.sweep.samples[2:]))

    def test_evidence_is_not_promoted_to_objective(self):
        samples = tuple(replace(sample, vehicle=replace(sample.vehicle,
                        role=VehicleStateRole.EVIDENCE_ONLY, state_weight=0.0))
                        for sample in self.sweep.samples)
        with self.assertRaisesRegex(TargetDefinitionError, "design_input"):
            self.target(replace(self.sweep, samples=samples))

    def test_sample_varying_tire_points_are_not_frozen(self):
        sample = self.sweep.samples[-1]
        wheel = replace(sample.vehicle.wheels[0], normal_load_n=333.0)
        bad = replace(sample, vehicle=replace(sample.vehicle,
                      wheels=(wheel, *sample.vehicle.wheels[1:])))
        with self.assertRaisesRegex(TargetDefinitionError, "sample-varying"):
            self.target(replace(self.sweep, samples=(*self.sweep.samples[:-1], bad)))

    def test_exact_branch_readiness_preserves_provider_result(self):
        results = magnitude_branch_readiness(self.sweep.samples[-1], self.fixture.branch_set)
        self.assertTrue(all(result.status == "magnitude_branch_ready" for result in results))
        self.assertTrue(all(result.provider_result is not None for result in results))
        self.assertTrue(all(result.provider_source is self.fixture.branch_set for result in results))

    def test_missing_domain_and_force_failures_are_distinct(self):
        sample = self.sweep.samples[-1]
        for changes, expected in (
            ({"pressure_kpa": None}, "missing_inputs"),
            ({"normal_load_n": 99999.0}, "exact_branch_unavailable"),
            ({"lateral_force_demand_n": 99999.0}, "force_demand_infeasible"),
        ):
            with self.subTest(expected=expected):
                wheel = replace(sample.vehicle.wheels[0], **changes)
                changed = replace(sample, vehicle=replace(sample.vehicle,
                                  wheels=(wheel, *sample.vehicle.wheels[1:])))
                result = magnitude_branch_readiness(changed, self.fixture.branch_set)[0]
                self.assertEqual(result.status, expected)
                self.assertTrue(result.reasons)
                self.assertIsNone(result.provider_result)

    def test_opposite_signed_demand_is_not_silently_magnituded(self):
        sample = self.sweep.samples[-1]
        wheel = replace(sample.vehicle.wheels[0], lateral_force_demand_n=-300.0)
        changed = replace(sample, vehicle=replace(sample.vehicle,
                          wheels=(wheel, *sample.vehicle.wheels[1:])))
        with self.assertRaisesRegex(TargetDefinitionError, "turn-consistent"):
            self.target(replace(self.sweep, samples=(*self.sweep.samples[:-1], changed)))

    def test_varying_pose_is_not_silently_frozen(self):
        sample = self.sweep.samples[-1]
        pose = replace(self.fixture.pose_set.state("symmetric_bump_5mm"), state_id="nominal")
        changed = replace(sample, pose=pose)
        with self.assertRaisesRegex(TargetDefinitionError, "unchanged pose"):
            self.target(replace(self.sweep, samples=(*self.sweep.samples[:-1], changed)))

    def test_sweep_cannot_mix_configurations(self):
        sample = self.sweep.samples[-1]
        stamp = replace(sample.vehicle_source, configuration_id="another_configuration")
        changed = replace(sample, vehicle_source=stamp, pose_source=stamp, motion_source=stamp)
        with self.assertRaisesRegex(VehicleStateError, "mixes configurations"):
            replace(self.sweep, samples=(*self.sweep.samples[:-1], changed))

    def test_signed_inverse_keeps_multiple_roots_and_out_of_domain_reason(self):
        sample = self.sweep.samples[-1]
        table = peak_post_peak_table()
        table = replace(table, curves=tuple(replace(curve, pressure_Pa=83000.0)
                                            for curve in table.curves))
        wheels = tuple(replace(wheel, normal_load_n=1000.0, inclination_deg=0.0,
                               pressure_kpa=83.0, lateral_force_demand_n=700.0)
                       for wheel in sample.vehicle.wheels)
        sample = replace(sample, vehicle=replace(sample.vehicle, wheels=wheels))
        results = signed_runtime_readiness(sample, table,
                    source_tire_id=SYNTHETIC_SOURCE, source_convention_id=CANONICAL_CONVENTION)
        self.assertTrue(all(result.status == "multiple_roots" for result in results))
        self.assertEqual(len(results[0].provider_result.candidates), 2)
        bad = replace(wheels[0], normal_load_n=99999.0)
        sample = replace(sample, vehicle=replace(sample.vehicle, wheels=(bad, *wheels[1:])))
        results = signed_runtime_readiness(sample, table,
                    source_tire_id=SYNTHETIC_SOURCE, source_convention_id=CANONICAL_CONVENTION)
        self.assertEqual(results[0].status, "provider_failure")
        self.assertIn("out_of_domain", results[0].reasons[0][0])


if __name__ == "__main__":
    unittest.main()
