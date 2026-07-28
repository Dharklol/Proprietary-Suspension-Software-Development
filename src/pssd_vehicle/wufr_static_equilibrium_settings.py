"""Numerical settings wrapper for the cached AUTH-VEH-0009 runtime."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import wufr_static_equilibrium_core as core
from . import wufr_static_equilibrium_runtime as runtime


def default_wufr_quasi_static_config(
    road_contact: core.WUFRRoadContactProvider,
    gravity: core.WUFRStaticGravityAllocation,
) -> core.QuasiStaticSolverConfig:
    """Return declared physical-provider tolerances for the nested WUFR map.

    The generic MOD-VEH-0004 synthetic default of 1e-10 scaled residual is not
    reused as hidden physical accuracy.  The WUFR composition declares a
    1e-7 scaled absolute/relative threshold while retaining every signed
    residual for review.  At the current residual scales this is sub-millinewton
    to sub-millinewton-metre order, substantially tighter than the provider
    derivative convergence tolerances and without clipping or repair.
    """
    return replace(
        runtime.default_wufr_quasi_static_config(road_contact, gravity),
        residual_absolute_tolerance=1.0e-7,
        residual_relative_tolerance=1.0e-7,
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
