from __future__ import annotations

from pathlib import Path
import unittest

from pssd_vehicle import wufr_static_equilibrium_core as core
from pssd_vehicle import wufr_static_equilibrium_runtime as runtime
from pssd_vehicle.quasi_static import (
    QuasiStaticStatus,
    SuspensionGeneralizedForceState,
    recover_active_contact_normal_reactions,
)
from pssd_vehicle.wufr_static_equilibrium import (
    evaluate_wufr_unsprung_gravity_reduction,
    load_wufr_static_equilibrium_provider,
)


ROOT = Path(__file__).resolve().parents[1]
OLD_PROBE_Q = (
    -0.0026807702741682574,
    -0.00008013635009263544,
    0.0026941883103072345,
)


def _provider():
    return load_wufr_static_equilibrium_provider(
        source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v1.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


class WUFRUnsprungGravityReductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = _provider()
        cls.cache = runtime._CompatibilityCache(cls.provider)
        cls.compatibility = cls.cache.state(OLD_PROBE_Q)
        cls.road = cls.cache.evaluation(OLD_PROBE_Q)
        cls.pose = core._pose_from_q(cls.provider, OLD_PROBE_Q)
        cls.wheel_gravity = tuple(
            float(item.value) for item in cls.road.unsprung_gravity_forces
        )
        cls.reduction = evaluate_wufr_unsprung_gravity_reduction(
            cls.provider,
            cls.pose,
            cls.road.compatibility,
            cls.compatibility.J_wb,
            cls.wheel_gravity,
        )

    def test_direct_and_mapped_terms_are_retained_once(self) -> None:
        result = self.reduction
        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.wheel_generalized_force, self.wheel_gravity)
        self.assertEqual(len(result.corner_direct_contributions), 4)
        self.assertAlmostEqual(result.body_direct_generalized_force[0], -196.2, places=10)
        for direct, mapped, reduced in zip(
            result.body_direct_generalized_force,
            result.body_mapped_generalized_force,
            result.body_reduced_generalized_force,
        ):
            self.assertAlmostEqual(reduced, direct + mapped, places=12)
        for sprung, reduced, total in zip(
            result.sprung_generalized_force,
            result.body_reduced_generalized_force,
            result.total_body_external_generalized_force,
        ):
            self.assertAlmostEqual(total, sprung + reduced, places=12)

    def test_corrected_reduced_residual_matches_independent_wrench(self) -> None:
        suspension = core.evaluate_wufr_suspension_composition(
            self.provider,
            self.road.compatibility.wheel_coordinates_m,
            front_arb_setting=1,
            rear_arb_setting=1,
        )
        self.assertTrue(suspension.ok, suspension.message)
        mapped_suspension = tuple(
            sum(
                self.compatibility.J_wb[corner][axis]
                * suspension.generalized_suspension_force_N[corner]
                for corner in range(4)
            )
            for axis in range(3)
        )
        corrected = tuple(
            self.reduction.total_body_external_generalized_force[axis]
            + mapped_suspension[axis]
            for axis in range(3)
        )
        old = tuple(
            self.reduction.sprung_generalized_force[axis]
            + mapped_suspension[axis]
            for axis in range(3)
        )
        state = SuspensionGeneralizedForceState(
            QuasiStaticStatus.SUCCESS,
            generalized_wheel_force=suspension.generalized_suspension_force_N,
            stored_energy_J=suspension.stored_energy_J,
            coordinate_order=core.CORNER_ORDER,
            coordinate_units=core.WHEEL_UNITS,
            source_id=self.provider.source.record_id,
            configuration_id=self.provider.source.configuration_id,
        )
        contact = recover_active_contact_normal_reactions(
            state,
            wheel_external_generalized_force=self.wheel_gravity,
            contact_coefficients=tuple(
                float(item.value) for item in self.road.contact_coefficients
            ),
        )
        self.assertTrue(contact.ok, contact.message)
        closure = core.evaluate_wufr_physical_closure(
            self.provider,
            self.pose,
            self.road,
            contact,
        )
        self.assertIsNotNone(closure.resultant)
        assert closure.resultant is not None
        physical = (
            closure.resultant.resultant_force_N[2],
            closure.resultant.resultant_moment_Nm[0],
            closure.resultant.resultant_moment_Nm[1],
        )
        old_physical_mismatch = tuple(
            old_value - physical_value
            for old_value, physical_value in zip(old, physical)
        )
        self.assertGreater(max(abs(value) for value in old_physical_mismatch), 1.0)
        for reduced_value, physical_value in zip(corrected, physical):
            self.assertAlmostEqual(reduced_value, physical_value, places=7)


if __name__ == "__main__":
    unittest.main()
