"""Explicit source-integration verification controls, not user maneuver inputs."""
from pathlib import Path

from pssd_tire.r25b_runtime import R25B_CANONICAL_SOURCE_CONVENTION_ID
from pssd_tire.r25b_source_native import EXPECTED_SOURCE_TIRE_ID, EXPECTED_INTENDED_TIRE_ID
from pssd_vehicle.steady_cornering import ASSUMPTIONS, CorneringCase, CorneringSolverConfig
from pssd_vehicle.steady_cornering_tire import R25BDevelopmentCorneringTireProvider, SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY
from pssd_vehicle.wufr_steady_cornering_geometry import WUFRCorneringGeometryProvider, HEADING_FRAME_ID, ROAD_ORIGIN_ID
from pssd_vehicle.wufr_static_equilibrium import load_wufr_static_equilibrium_provider

ROOT = Path(__file__).resolve().parents[1]


def providers():
    components = load_wufr_static_equilibrium_provider(
        source_path=ROOT/'data_catalog/wufr27_static_equilibrium_composition_v1.toml',
        road_contact_source_path=ROOT/'data_catalog/wufr26_road_contact_reference_v0.toml',
        suspension_geometry_path=ROOT/'data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml',
        wheel_profile_path=ROOT/'benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml',
        steering_geometry_path=ROOT/'configurations/steering/WUFR27_STEERING_BASELINE_V0.toml',
        whole_vehicle_path=ROOT/'data_catalog/wufr26_whole_vehicle_frame_v0.toml',
        gravity_path=ROOT/'data_catalog/wufr27_static_gravity_allocation_v0.toml',
        spring_package_path=ROOT/'data_catalog/wufr27_spring_package_v0.toml',
        zbar_fixture_path=ROOT/'benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml',
    )
    return WUFRCorneringGeometryProvider(components), R25BDevelopmentCorneringTireProvider(
        accepted_assumption_id=SYMMETRY_ASSUMPTION_ID, policy=SYMMETRY_POLICY)


def case(geometry, tire, curvature=0., state_id='native_source_verification'):
    # V=8 m/s, source gauge pressure=68.9 kPa, and discrete setting 1 are
    # deliberately selected fixture controls. They are not user setup defaults.
    return CorneringCase(state_id, geometry.components.source.configuration_id,
        geometry.geometry_revision, geometry.setup_revision, tire.tire_revision,
        HEADING_FRAME_ID, ROAD_ORIGIN_ID, 8., curvature, (68900.,)*4,
        geometry.components.gravity.g_mps2, 1, 1,
        geometry.components.spring_package.reference.reference_id,
        EXPECTED_SOURCE_TIRE_ID, EXPECTED_INTENDED_TIRE_ID, R25B_CANONICAL_SOURCE_CONVENTION_ID,
        ASSUMPTIONS, 'uniform_acceleration_current_mass_lumps',
        'virtual_tangential_force_at_current_total_cg', 'fixed_radius_zero_width_rigid_circle',
        'evidence_only', 0.)


def solver_config():
    # Bounds retain the native local geometry and transformed tire domains.
    return CorneringSolverConfig(
        (.005,.005,.005,.05,.005,100.,750.,750.,750.,750.),
        (3000.,1500.,1500.,750.,750.,750.,750.,3000.,3000.,1500.),
        (-.009,-.009,-.009,-.08,-.015,-500.,223.,223.,223.,223.),
        (.009,.009,.009,.08,.015,500.,1111.,1111.,1111.,1111.),
        (2e-6,2e-6,2e-6,2e-6,2e-6,.001,.001,.001,.001,.001),
        1e-10, 1e-9, 20, 20)


def initial():
    return (0.,0.,0.,0.,0.,0.,800.,800.,700.,700.)
