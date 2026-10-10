from dataclasses import replace
from pathlib import Path
import unittest

from pssd_steering.optimization.poses import load_pose_set
from pssd_vehicle.operating_states import (
    TurnDirection, VehicleOperatingState, VehicleStateError, VehicleStateRole,
    WheelOperatingState, WheelPosition,
)
from pssd_vehicle.planar_kinematics import PlanarMotionSample
from pssd_vehicle.synced_state import (
    CANONICAL_FRAME, StateSourceStamp, compose_synced_state_sample,
)


class SyncedStateTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.pose = load_pose_set(
            root / "benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml"
        ).state("nominal")
        self.vehicle = VehicleOperatingState(
            state_id="synthetic", role=VehicleStateRole.EVIDENCE_ONLY,
            turn_direction=TurnDirection.LEFT, ax_g=0.0, ay_g=0.0,
            speed_mps=10.0, suspension_pose_state_id="nominal",
            authority="software verification only",
            wheels=tuple(WheelOperatingState(
                position=p, normal_load_n=667.0, inclination_deg=0.0,
                pressure_kpa=82.7, lateral_force_demand_n=800.0,
            ) for p in WheelPosition),
        )
        self.stamp = StateSourceStamp(
            "synthetic_config", "synthetic", "rack_0", "sync_v1", CANONICAL_FRAME,
            "synthetic_fixture", "v1", "software verification only", "synthetic",
        )

    def compose(self, **changes):
        values = dict(rack_displacement_m=0.0, vehicle=self.vehicle,
                      pose=self.pose, motion=PlanarMotionSample(10.0, 0.0, 1.0),
                      vehicle_source=self.stamp, pose_source=self.stamp,
                      motion_source=self.stamp)
        values.update(changes)
        return compose_synced_state_sample(**values)

    def test_source_objects_and_evidence_role_are_preserved(self):
        sample = self.compose()
        self.assertIs(sample.vehicle, self.vehicle)
        self.assertIs(sample.pose, self.pose)
        self.assertTrue(sample.front_inputs_complete)
        self.assertEqual(sample.vehicle.state_weight, 0.0)
        self.assertEqual(sample, self.compose())

    def test_each_synchronization_key_mismatch_rejects_atomic_publication(self):
        for field in ("configuration_id", "state_id", "sample_id", "synchronization_revision"):
            for source in ("pose_source", "motion_source"):
                with self.subTest(field=field, source=source):
                    with self.assertRaisesRegex(VehicleStateError, "synchronization mismatch"):
                        self.compose(**{source: replace(self.stamp, **{field: "different"})})

    def test_component_sources_can_have_distinct_revisions(self):
        pose_source = replace(self.stamp, source_revision="pose_v7", source_path="pose")
        self.assertEqual(self.compose(pose_source=pose_source).pose_source, pose_source)

    def test_missing_pressure_is_preserved_without_nominal_default(self):
        wheel = replace(self.vehicle.wheels[0], pressure_kpa=None,
                        missing_reasons=(("pressure_kpa", "not measured"),))
        vehicle = replace(self.vehicle, wheels=(wheel, *self.vehicle.wheels[1:]))
        sample = self.compose(vehicle=vehicle)
        self.assertFalse(sample.front_inputs_complete)
        self.assertEqual(sample.missing_front_inputs,
                         (("front_left", "pressure_kpa", "not measured"),))
        self.assertIsNone(sample.vehicle.wheels[0].pressure_kpa)

    def test_pose_motion_and_vehicle_mismatches_are_rejected(self):
        bad = (
            dict(vehicle=replace(self.vehicle, state_id="other")),
            dict(vehicle=replace(self.vehicle, suspension_pose_state_id="other")),
            dict(motion=PlanarMotionSample(9.0, 0.0, 1.0)),
            dict(motion=PlanarMotionSample(10.0, 0.0, -1.0)),
            dict(rack_displacement_m=float("nan")),
        )
        for changes in bad:
            with self.subTest(changes=changes):
                with self.assertRaises(VehicleStateError):
                    self.compose(**changes)

    def test_empty_source_or_noncanonical_frame_is_rejected(self):
        for changes in (dict(source_revision=""), dict(frame="other_frame")):
            with self.assertRaises(VehicleStateError):
                replace(self.stamp, **changes)

    def test_complete_inputs_do_not_assert_tire_domain_or_design_authority(self):
        wheel = replace(self.vehicle.wheels[0], normal_load_n=2000.0)
        sample = self.compose(vehicle=replace(
            self.vehicle, wheels=(wheel, *self.vehicle.wheels[1:])))
        self.assertTrue(sample.front_inputs_complete)
        self.assertEqual(sample.vehicle.wheels[0].normal_load_n, 2000.0)
        self.assertIs(sample.vehicle.role, VehicleStateRole.EVIDENCE_ONLY)

    def test_zero_contact_load_is_incomplete_for_tire_query(self):
        wheel = replace(self.vehicle.wheels[0], normal_load_n=0.0)
        sample = self.compose(vehicle=replace(
            self.vehicle, wheels=(wheel, *self.vehicle.wheels[1:])))
        self.assertFalse(sample.front_inputs_complete)


if __name__ == "__main__":
    unittest.main()
