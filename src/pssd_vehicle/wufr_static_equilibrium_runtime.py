"""Cached runtime adapter for the AUTH-VEH-0009 WUFR static solve.

The core module owns source validation, force composition, result contracts, and
physical closure.  This module keeps those mechanics unchanged while caching
road-compatible states and aligning the outer Newton finite-difference step
with the already reviewed fine MOD-VEH-0006 body-Jacobian step.  The cache is
local to one solve and never changes, fits, clips, or interpolates a result.
"""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from typing import Sequence

from . import wufr_static_equilibrium_core as core


class _CompatibilityCache:
    def __init__(self, provider: core.WUFRStaticEquilibriumProvider) -> None:
        self.provider = provider
        self._road: dict[tuple[float, float, float], object] = {}
        self._state: dict[tuple[float, float, float], core.CompatibilityState] = {}

    @staticmethod
    def _key(q_body: Sequence[float]) -> tuple[float, float, float]:
        q = tuple(float(value) for value in q_body)
        if len(q) != 3 or not all(math.isfinite(value) for value in q):
            raise core.WUFRStaticEquilibriumError(
                core.WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
                "Cached compatibility requires finite [z_s,phi,theta] coordinates",
            )
        return q  # type: ignore[return-value]

    def road(self, q_body: Sequence[float]):
        key = self._key(q_body)
        if key not in self._road:
            pose = core._pose_from_q(self.provider, key)
            self._road[key] = core.solve_road_compatibility(self.provider.road_contact, pose)
        return self._road[key]

    def _matrix_at_steps(
        self,
        q_body: tuple[float, float, float],
        steps: tuple[float, float, float],
    ) -> tuple[tuple[float, float, float], ...]:
        columns: list[tuple[float, float, float, float]] = []
        for axis, step in enumerate(steps):
            q_minus = list(q_body)
            q_plus = list(q_body)
            q_minus[axis] -= step
            q_plus[axis] += step
            minus = self.road(q_minus)
            plus = self.road(q_plus)
            if (
                not minus.ok
                or not plus.ok
                or minus.wheel_coordinates_m is None
                or plus.wheel_coordinates_m is None
            ):
                failed = minus if not minus.ok else plus
                raise core.WUFRStaticEquilibriumError(
                    core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                    failed.message or f"Road compatibility failed for body derivative axis {axis}",
                )
            columns.append(
                tuple(
                    (right - left) / (2.0 * step)
                    for left, right in zip(
                        minus.wheel_coordinates_m,
                        plus.wheel_coordinates_m,
                    )
                )
            )
        return tuple(
            tuple(columns[column][row] for column in range(3))
            for row in range(4)
        )

    def state(self, q_body: Sequence[float]) -> core.CompatibilityState:
        try:
            key = self._key(q_body)
        except core.WUFRStaticEquilibriumError as exc:
            return core.CompatibilityState(
                core.QuasiStaticStatus.FAILURE,
                failure_code=core.QuasiStaticFailureCode.COORDINATE_CONTRACT_MISMATCH,
                message=str(exc),
            )
        if key in self._state:
            return self._state[key]
        road = self.road(key)
        if not road.ok or road.wheel_coordinates_m is None:
            result = core.CompatibilityState(
                core.QuasiStaticStatus.FAILURE,
                source_id=self.provider.road_contact.source.record_id,
                configuration_id=self.provider.source.configuration_id,
                failure_code=core.QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
                message=road.message or "WUFR road compatibility failed",
            )
            self._state[key] = result
            return result
        cfg = self.provider.road_contact.config
        coarse_steps = cfg.body_fd_steps
        fine_steps = tuple(0.5 * value for value in coarse_steps)
        try:
            coarse = self._matrix_at_steps(key, coarse_steps)
            fine = self._matrix_at_steps(key, fine_steps)  # type: ignore[arg-type]
        except core.WUFRStaticEquilibriumError as exc:
            result = core.CompatibilityState(
                core.QuasiStaticStatus.FAILURE,
                source_id=self.provider.road_contact.source.record_id,
                configuration_id=self.provider.source.configuration_id,
                failure_code=core.QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
                message=str(exc),
            )
            self._state[key] = result
            return result
        error = max(
            abs(left - right)
            for coarse_row, fine_row in zip(coarse, fine)
            for left, right in zip(coarse_row, fine_row)
        )
        scale = max(1.0, *(abs(value) for row in fine for value in row))
        tolerance = cfg.derivative_absolute_tolerance + cfg.derivative_relative_tolerance * scale
        if error > tolerance:
            result = core.CompatibilityState(
                core.QuasiStaticStatus.FAILURE,
                source_id=self.provider.road_contact.source.record_id,
                configuration_id=self.provider.source.configuration_id,
                failure_code=core.QuasiStaticFailureCode.COMPATIBILITY_PROVIDER_FAILURE,
                message=(
                    f"Cached J_wb h/h2 difference {error:.6g} exceeds "
                    f"AUTH-VEH-0008 tolerance {tolerance:.6g}"
                ),
            )
            self._state[key] = result
            return result
        result = core.CompatibilityState(
            core.QuasiStaticStatus.SUCCESS,
            wheel_coordinates=road.wheel_coordinates_m,
            J_wb=fine,
            wheel_coordinate_order=core.CORNER_ORDER,
            wheel_coordinate_units=core.WHEEL_UNITS,
            source_id=self.provider.road_contact.source.record_id,
            configuration_id=self.provider.source.configuration_id,
        )
        self._state[key] = result
        return result


def default_wufr_quasi_static_config(
    road_contact: core.WUFRRoadContactProvider,
    gravity: core.WUFRStaticGravityAllocation,
) -> core.QuasiStaticSolverConfig:
    """Return the core solver settings with an aligned 1e-4 SI tangent step.

    ``coordinate_scales=(0.005,0.005,0.005)`` and relative step ``0.02``
    produce a dimensional step of ``1e-4`` in each body coordinate, matching
    the fine AUTH-VEH-0008 body-Jacobian step.  This improves cache reuse but
    does not alter either provider equation.
    """
    return replace(
        core.default_wufr_quasi_static_config(road_contact, gravity),
        finite_difference_relative_step=0.02,
        finite_difference_min_step=1.0e-7,
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
    effective_config = config or replace(
        core.WUFRStaticEquilibriumConfig(),
        energy_gradient_absolute_tolerance=0.01,
        energy_gradient_step_multipliers=(0.02, 0.01),
    )
    provider = core.load_wufr_static_equilibrium_provider(
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
        config=effective_config,
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


def solve_wufr_static_equilibrium(
    provider: core.WUFRStaticEquilibriumProvider,
    *,
    front_arb_setting: int,
    rear_arb_setting: int,
    initial_q_body: Sequence[float] = (0.0, 0.0, 0.0),
) -> core.WUFRStaticEquilibriumResult:
    if not core._valid_setting(front_arb_setting) or not core._valid_setting(rear_arb_setting):
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            failure_code=core.WUFRStaticEquilibriumFailureCode.INVALID_ARB_SETTING,
            message="Front and rear ARB settings are required explicit integer inputs in 1..5",
        )
    q0 = tuple(float(value) for value in initial_q_body)
    if len(q0) != 3 or not core._finite(q0):
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            failure_code=core.WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
            message="Initial body state must contain three finite coordinates",
        )

    compatibility_cache = _CompatibilityCache(provider)
    suspension_cache: dict[tuple[float, ...], core.SuspensionGeneralizedForceState] = {}
    body_cache: dict[tuple[float, ...], core.BodyExternalGeneralizedForceState] = {}

    def compatibility_provider(q_body: Sequence[float]) -> core.CompatibilityState:
        return compatibility_cache.state(q_body)

    def suspension_provider(z_wheel: Sequence[float]) -> core.SuspensionGeneralizedForceState:
        key = tuple(float(value) for value in z_wheel)
        if key not in suspension_cache:
            suspension_cache[key] = core._suspension_state(
                provider,
                key,
                front_arb_setting,
                rear_arb_setting,
            )
        return suspension_cache[key]

    def body_external_provider(q_body: Sequence[float]) -> core.BodyExternalGeneralizedForceState:
        key = tuple(float(value) for value in q_body)
        if key not in body_cache:
            body_cache[key] = core._body_external_state(provider, key)
        return body_cache[key]

    solve = core.solve_quasi_static_equilibrium(
        q0,
        body_coordinate_order=core.BODY_ORDER,
        body_coordinate_units=core.BODY_UNITS,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        config=provider.quasi_static_config,
    )
    if not solve.ok:
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            failure_code=core.WUFRStaticEquilibriumFailureCode.EQUILIBRIUM_FAILURE,
            message=solve.message or "WUFR reduced quasi-static equilibrium failed",
        )

    pose = core._pose_from_q(provider, solve.q_body)
    road_contact = core.evaluate_wufr_road_contact(
        provider.road_contact,
        pose,
        provider.gravity,
    )
    if (
        not road_contact.ok
        or road_contact.compatibility.wheel_coordinates_m is None
        or any(item.value is None for item in road_contact.contact_coefficients)
        or any(item.value is None for item in road_contact.unsprung_gravity_forces)
    ):
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            road_contact=road_contact,
            failure_code=core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
            message=road_contact.message or "Final WUFR road/contact evaluation failed",
        )
    suspension = core.evaluate_wufr_suspension_composition(
        provider,
        road_contact.compatibility.wheel_coordinates_m,
        front_arb_setting=front_arb_setting,
        rear_arb_setting=rear_arb_setting,
    )
    if not suspension.ok:
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            failure_code=core.WUFRStaticEquilibriumFailureCode.SUSPENSION_FAILURE,
            message=suspension.message,
        )
    suspension_state = core.SuspensionGeneralizedForceState(
        core.QuasiStaticStatus.SUCCESS,
        generalized_wheel_force=suspension.generalized_suspension_force_N,
        stored_energy_J=suspension.stored_energy_J,
        coordinate_order=core.CORNER_ORDER,
        coordinate_units=core.WHEEL_UNITS,
        source_id=provider.source.record_id,
        configuration_id=provider.source.configuration_id,
    )
    contact = core.recover_active_contact_normal_reactions(
        suspension_state,
        wheel_external_generalized_force=tuple(
            float(item.value) for item in road_contact.unsprung_gravity_forces
        ),
        contact_coefficients=tuple(
            float(item.value) for item in road_contact.contact_coefficients
        ),
    )
    if not contact.ok or any(
        abs(value) > provider.config.wheel_equilibrium_residual_tolerance_N
        for value in contact.wheel_equilibrium_residual
    ):
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            contact_recovery=contact,
            failure_code=core.WUFRStaticEquilibriumFailureCode.CONTACT_RECOVERY_FAILURE,
            message=contact.message or "Wheel/contact equilibrium residual exceeds tolerance",
        )

    energy = core.check_total_potential_gradient(
        solve.q_body,
        body_coordinate_order=core.BODY_ORDER,
        body_coordinate_units=core.BODY_UNITS,
        compatibility_provider=compatibility_provider,
        suspension_provider=suspension_provider,
        body_external_provider=body_external_provider,
        config=provider.quasi_static_config,
        relative_step_multipliers=provider.config.energy_gradient_step_multipliers,
        absolute_tolerance=provider.config.energy_gradient_absolute_tolerance,
    )
    if not energy.ok:
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            contact_recovery=contact,
            energy_gradient=energy,
            failure_code=core.WUFRStaticEquilibriumFailureCode.ENERGY_GRADIENT_FAILURE,
            message=energy.message,
        )
    closure = core.evaluate_wufr_physical_closure(provider, pose, road_contact, contact)
    if not closure.ok:
        return core.WUFRStaticEquilibriumResult(
            core.WUFRStaticEquilibriumStatus.FAILURE,
            front_arb_setting,
            rear_arb_setting,
            solve=solve,
            suspension=suspension,
            road_contact=road_contact,
            contact_recovery=contact,
            energy_gradient=energy,
            physical_closure=closure,
            failure_code=core.WUFRStaticEquilibriumFailureCode.PHYSICAL_CLOSURE_FAILURE,
            message=closure.message,
        )
    return core.WUFRStaticEquilibriumResult(
        core.WUFRStaticEquilibriumStatus.SUCCESS,
        front_arb_setting,
        rear_arb_setting,
        solve=solve,
        suspension=suspension,
        road_contact=road_contact,
        contact_recovery=contact,
        energy_gradient=energy,
        physical_closure=closure,
        complete_static_road_reaction=True,
        installed_as_built_authority=False,
        historical_scale_reconstruction_used=False,
        message="WUFR uncorrelated design-intent static-gravity equilibrium converged",
    )
