"""Numerical settings wrapper for the cached AUTH-VEH-0010 runtime."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import wufr_static_equilibrium_core as core
from . import wufr_static_equilibrium_runtime as runtime


def default_wufr_quasi_static_config(
    road_contact: core.WUFRRoadContactProvider,
    gravity: core.WUFRStaticGravityAllocation,
) -> core.QuasiStaticSolverConfig:
    """Return the deterministic AUTH-VEH-0010 convergence settings.

    The 2e-10 scaled residual threshold keeps the unchanged physical closure
    gates reachable without treating numerical convergence as physical proof.
    Every signed residual is retained and independently checked in the road
    frame after the generic MOD-VEH-0004 solve.
    """
    return replace(
        runtime.default_wufr_quasi_static_config(road_contact, gravity),
        residual_absolute_tolerance=2.0e-10,
        residual_relative_tolerance=2.0e-10,
    )


def load_wufr_static_equilibrium_provider(
    *,
    source_path: str | Path,
    road_contact_source_path: str | Path,
    suspension_geometry_path: str | Path,
    wheel_profile_path: str | Path,
    steering_geometry_path: str | Path,
    whole_vehicle_path: str | Path,
    gravity_path: str | Path,
    spring_package_path: str | Path,
    zbar_fixture_path: str | Path,
    road_contact_config=None,
    rocker_derivative: core.RockerWheelDerivativeConfig | None = None,
    quasi_static_config: core.QuasiStaticSolverConfig | None = None,
    config: core.WUFRStaticEquilibriumConfig | None = None,
) -> core.WUFRStaticEquilibriumProvider:
    provider = runtime.load_wufr_static_equilibrium_provider(
        source_path=source_path,
        road_contact_source_path=road_contact_source_path,
        suspension_geometry_path=suspension_geometry_path,
        wheel_profile_path=wheel_profile_path,
        steering_geometry_path=steering_geometry_path,
        whole_vehicle_path=whole_vehicle_path,
        gravity_path=gravity_path,
        spring_package_path=spring_package_path,
        zbar_fixture_path=zbar_fixture_path,
        road_contact_config=road_contact_config,
        rocker_derivative=rocker_derivative,
        quasi_static_config=quasi_static_config,
        config=config,
    )
    if quasi_static_config is None:
        provider = replace(
            provider,
            quasi_static_config=default_wufr_quasi_static_config(
                provider.road_contact,
                provider.gravity,
            ),
        )
    return provider


solve_wufr_static_equilibrium = runtime.solve_wufr_static_equilibrium
