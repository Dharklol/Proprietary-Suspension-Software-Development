"""Cached runtime adapter for the AUTH-VEH-0010 WUFR static solve.

The core module owns source validation, force composition, result contracts, and
physical closure.  This module keeps those mechanics unchanged while caching
road-compatible states and aligning the outer Newton finite-difference step
with the already reviewed fine MOD-VEH-0006 body-Jacobian step.  The cache is
local to one solve and never changes, fits, clips, or interpolates a result.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
from typing import Sequence

from . import wufr_static_equilibrium_core as core
from . import wufr_road_contact as road_model


@dataclass(frozen=True)
class _CornerDerivativeBundle:
    corner_id: str
    accepted_J_row: tuple[float, float, float]
    coarse_J_row: tuple[float, float, float]
    fine_J_row: tuple[float, float, float]
    body_convergence_error: float
    accepted_contact_coefficient: float
    coarse_contact_coefficient: float
    fine_contact_coefficient: float
    contact_convergence_error: float
    accepted_wheel_center_derivative: tuple[float, float, float]
    coarse_wheel_center_derivative: tuple[float, float, float]
    fine_wheel_center_derivative: tuple[float, float, float]
    wheel_center_convergence_error: float


class _CompatibilityCache:
    """Cache the exact road roots and their implicit compatible derivatives.

    ``AUTH-VEH-0008`` defines the road root ``g(q_b,z_w)=0``.  Differentiating
    that same root gives ``dz_w/dq_b=-g_q/g_z``.  This runtime evaluates the
    derivative locally at the converged root, rather than differencing two
    independently bisected roots.  The physical model and root are unchanged;
    the formulation removes root-tolerance noise and uses the same ``g_z`` for
    contact recovery, which is required by the corrected EQ-VEH-0018 chain.
    """

    def __init__(self, provider: core.WUFRStaticEquilibriumProvider) -> None:
        self.provider = provider
        self._road: dict[tuple[float, float, float], road_model.RoadCompatibilityResult] = {}
        self._derivatives: dict[tuple[float, float, float], tuple[_CornerDerivativeBundle, ...]] = {}
        self._state: dict[tuple[float, float, float], core.CompatibilityState] = {}
        self._evaluation: dict[tuple[float, float, float], road_model.WUFRRoadContactEvaluation] = {}

    @staticmethod
    def _key(q_body: Sequence[float]) -> tuple[float, float, float]:
        q = tuple(float(value) for value in q_body)
        if len(q) != 3 or not all(math.isfinite(value) for value in q):
            raise core.WUFRStaticEquilibriumError(
                core.WUFRStaticEquilibriumFailureCode.NONFINITE_INPUT,
                "Cached compatibility requires finite [z_s,phi,theta] coordinates",
            )
        return q  # type: ignore[return-value]

    def road(self, q_body: Sequence[float]) -> road_model.RoadCompatibilityResult:
        key = self._key(q_body)
        if key not in self._road:
            pose = core._pose_from_q(self.provider, key)
            self._road[key] = core.solve_road_compatibility(self.provider.road_contact, pose)
        return self._road[key]

    @staticmethod
    def _pose_with_coordinate(
        pose: core.BodyPose,
        axis: int,
        delta: float,
    ) -> core.BodyPose:
        values = [pose.z_s_m, pose.phi_rad, pose.theta_rad]
        values[axis] += delta
        return replace(pose, z_s_m=values[0], phi_rad=values[1], theta_rad=values[2])

    def _road_state(
        self,
        pose: core.BodyPose,
        corner_id: str,
        wheel_coordinate_m: float,
    ) -> road_model.CornerRoadState:
        return road_model.evaluate_corner_road_state(
            self.provider.road_contact,
            pose,
            corner_id,
            wheel_coordinate_m,
        )

    def _body_gap_derivative(
        self,
        pose: core.BodyPose,
        corner_id: str,
        wheel_coordinate_m: float,
        axis: int,
        step: float,
    ) -> float:
        minus = self._road_state(
            self._pose_with_coordinate(pose, axis, -step),
            corner_id,
            wheel_coordinate_m,
        )
        plus = self._road_state(
            self._pose_with_coordinate(pose, axis, step),
            corner_id,
            wheel_coordinate_m,
        )
        return (plus.road_gap_m - minus.road_gap_m) / (2.0 * step)

    def _wheel_derivatives(
        self,
        pose: core.BodyPose,
        corner_id: str,
        wheel_coordinate_m: float,
        step: float,
    ) -> tuple[float, tuple[float, float, float]]:
        cfg = self.provider.road_contact.config
        if (
            wheel_coordinate_m - step < cfg.wheel_coordinate_min_m
            or wheel_coordinate_m + step > cfg.wheel_coordinate_max_m
        ):
            raise core.WUFRStaticEquilibriumError(
                core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                f"Implicit wheel derivative leaves the reviewed interval for {corner_id}",
            )
        minus = self._road_state(pose, corner_id, wheel_coordinate_m - step)
        plus = self._road_state(pose, corner_id, wheel_coordinate_m + step)
        inverse = 1.0 / (2.0 * step)
        center_derivative = tuple(
            (plus.wheel_center_road.position_m[index] - minus.wheel_center_road.position_m[index])
            * inverse
            for index in range(3)
        )
        gap_derivative = (plus.road_gap_m - minus.road_gap_m) * inverse
        return gap_derivative, center_derivative  # type: ignore[return-value]

    def derivatives(
        self,
        q_body: Sequence[float],
    ) -> tuple[_CornerDerivativeBundle, ...]:
        key = self._key(q_body)
        if key in self._derivatives:
            return self._derivatives[key]
        road = self.road(key)
        if not road.ok or road.wheel_coordinates_m is None:
            raise core.WUFRStaticEquilibriumError(
                core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                road.message or "WUFR road compatibility failed",
            )
        pose = core._pose_from_q(self.provider, key)
        cfg = self.provider.road_contact.config
        fine_body_steps = tuple(0.5 * value for value in cfg.body_fd_steps)
        coarse_wheel_step = cfg.wheel_fd_step_m
        fine_wheel_step = 0.5 * coarse_wheel_step
        bundles: list[_CornerDerivativeBundle] = []
        for root in road.roots:
            if not root.ok or root.wheel_coordinate_m is None:
                raise core.WUFRStaticEquilibriumError(
                    core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                    root.message or f"Road root unavailable for {root.corner_id}",
                )
            z = float(root.wheel_coordinate_m)
            coarse_gq = tuple(
                self._body_gap_derivative(pose, root.corner_id, z, axis, cfg.body_fd_steps[axis])
                for axis in range(3)
            )
            fine_gq = tuple(
                self._body_gap_derivative(pose, root.corner_id, z, axis, fine_body_steps[axis])
                for axis in range(3)
            )
            accepted_gq = tuple((4.0 * fine - coarse) / 3.0 for coarse, fine in zip(coarse_gq, fine_gq))
            coarse_c, coarse_center = self._wheel_derivatives(
                pose,
                root.corner_id,
                z,
                coarse_wheel_step,
            )
            fine_c, fine_center = self._wheel_derivatives(
                pose,
                root.corner_id,
                z,
                fine_wheel_step,
            )
            accepted_c = (4.0 * fine_c - coarse_c) / 3.0
            accepted_center = tuple(
                (4.0 * fine - coarse) / 3.0
                for coarse, fine in zip(coarse_center, fine_center)
            )
            if (
                not math.isfinite(accepted_c)
                or abs(accepted_c) < cfg.contact_coefficient_min_abs
            ):
                raise core.WUFRStaticEquilibriumError(
                    core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                    f"Implicit contact coefficient is invalid for {root.corner_id}",
                )
            coarse_J = tuple(-value / coarse_c for value in coarse_gq)
            fine_J = tuple(-value / fine_c for value in fine_gq)
            accepted_J = tuple(-value / accepted_c for value in accepted_gq)
            body_error = max(abs(left - right) for left, right in zip(coarse_J, fine_J))
            body_scale = max(1.0, *(abs(value) for value in accepted_J))
            body_tolerance = cfg.derivative_absolute_tolerance + cfg.derivative_relative_tolerance * body_scale
            contact_error = abs(coarse_c - fine_c)
            contact_tolerance = cfg.derivative_absolute_tolerance + cfg.derivative_relative_tolerance * max(1.0, abs(accepted_c))
            center_error = max(abs(left - right) for left, right in zip(coarse_center, fine_center))
            center_scale = max(1.0, *(abs(value) for value in accepted_center))
            center_tolerance = cfg.derivative_absolute_tolerance + cfg.derivative_relative_tolerance * center_scale
            if body_error > body_tolerance:
                raise core.WUFRStaticEquilibriumError(
                    core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                    f"Implicit J_wb h/h2 difference {body_error:.6g} exceeds AUTH-VEH-0008 tolerance {body_tolerance:.6g}",
                )
            if contact_error > contact_tolerance or center_error > center_tolerance:
                raise core.WUFRStaticEquilibriumError(
                    core.WUFRStaticEquilibriumFailureCode.COMPATIBILITY_FAILURE,
                    f"Implicit wheel derivative did not converge for {root.corner_id}",
                )
            bundles.append(
                _CornerDerivativeBundle(
                    root.corner_id,
                    accepted_J,  # type: ignore[arg-type]
                    coarse_J,  # type: ignore[arg-type]
                    fine_J,  # type: ignore[arg-type]
                    body_error,
                    accepted_c,
                    coarse_c,
                    fine_c,
                    contact_error,
                    accepted_center,  # type: ignore[arg-type]
                    coarse_center,
                    fine_center,
                    center_error,
                )
            )
        result = tuple(bundles)
        self._derivatives[key] = result
        return result

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
        try:
            bundles = self.derivatives(key)
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
        result = core.CompatibilityState(
            core.QuasiStaticStatus.SUCCESS,
            wheel_coordinates=road.wheel_coordinates_m,
            J_wb=tuple(bundle.accepted_J_row for bundle in bundles),
            wheel_coordinate_order=core.CORNER_ORDER,
            wheel_coordinate_units=core.WHEEL_UNITS,
            source_id=self.provider.road_contact.source.record_id,
            configuration_id=self.provider.source.configuration_id,
        )
        self._state[key] = result
        return result

    def evaluation(self, q_body: Sequence[float]) -> road_model.WUFRRoadContactEvaluation:
        key = self._key(q_body)
        if key in self._evaluation:
            return self._evaluation[key]
        road = self.road(key)
        state = self.state(key)
        if not road.ok or not state.ok:
            result = road_model.WUFRRoadContactEvaluation(
                road_model.WUFRRoadContactStatus.FAILURE,
                road,
                failure_code=road.failure_code,
                message=state.message or road.message,
            )
            self._evaluation[key] = result
            return result
        bundles = self.derivatives(key)
        masses = {item.corner_id: item for item in self.provider.gravity.unsprung}
        contact_results: list[road_model.ScalarProjectionResult] = []
        gravity_results: list[road_model.ScalarProjectionResult] = []
        for bundle in bundles:
            contact_results.append(
                road_model.ScalarProjectionResult(
                    road_model.WUFRRoadContactStatus.SUCCESS,
                    bundle.corner_id,
                    bundle.accepted_contact_coefficient,
                    bundle.coarse_contact_coefficient,
                    self.provider.road_contact.config.wheel_fd_step_m,
                    0.5 * self.provider.road_contact.config.wheel_fd_step_m,
                    bundle.contact_convergence_error,
                )
            )
            mass = masses.get(bundle.corner_id)
            if mass is None:
                result = road_model.WUFRRoadContactEvaluation(
                    road_model.WUFRRoadContactStatus.FAILURE,
                    road,
                    contact_coefficients=tuple(contact_results),
                    failure_code=road_model.WUFRRoadContactFailureCode.GRAVITY_SOURCE_MISMATCH,
                    message=f"Missing source unsprung mass for {bundle.corner_id}",
                )
                self._evaluation[key] = result
                return result
            force = mass.force_N(self.provider.gravity.g_mps2)
            coarse_q = sum(force[index] * bundle.coarse_wheel_center_derivative[index] for index in range(3))
            fine_q = sum(force[index] * bundle.fine_wheel_center_derivative[index] for index in range(3))
            accepted_q = sum(force[index] * bundle.accepted_wheel_center_derivative[index] for index in range(3))
            gravity_results.append(
                road_model.ScalarProjectionResult(
                    road_model.WUFRRoadContactStatus.SUCCESS,
                    bundle.corner_id,
                    accepted_q,
                    coarse_q,
                    self.provider.road_contact.config.wheel_fd_step_m,
                    0.5 * self.provider.road_contact.config.wheel_fd_step_m,
                    abs(coarse_q - fine_q),
                )
            )
        accepted_matrix = tuple(bundle.accepted_J_row for bundle in bundles)
        coarse_matrix = tuple(bundle.coarse_J_row for bundle in bundles)
        jacobian = road_model.RoadJacobianResult(
            road_model.WUFRRoadContactStatus.SUCCESS,
            jacobian=accepted_matrix,  # type: ignore[arg-type]
            coarse_jacobian=coarse_matrix,  # type: ignore[arg-type]
            coarse_steps=self.provider.road_contact.config.body_fd_steps,
            fine_steps=tuple(0.5 * value for value in self.provider.road_contact.config.body_fd_steps),
            convergence_error=max(bundle.body_convergence_error for bundle in bundles),
            message="Implicit differentiation of the AUTH-VEH-0008 road root with two-step Richardson refinement",
        )
        result = road_model.WUFRRoadContactEvaluation(
            road_model.WUFRRoadContactStatus.SUCCESS,
            road,
            jacobian,
            tuple(contact_results),
            tuple(gravity_results),
        )
        self._evaluation[key] = result
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
    effective_road_config = road_contact_config or replace(
        road_model.WUFRRoadContactSolverConfig(),
        road_gap_tolerance_m=1.0e-13,
        wheel_coordinate_tolerance_m=1.0e-13,
        root_max_iterations=160,
        physical_q_L_tolerance_rad=1.0e-14,
        physical_displacement_tolerance_m=1.0e-14,
        kinematics_root_angle_tolerance_rad=1.0e-14,
        kinematics_length_residual_tolerance_m=1.0e-14,
        kinematics_max_iterations=180,
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
        road_contact_config=effective_road_config,
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
    gravity_cache: dict[tuple[float, ...], core.WUFRUnsprungGravityReductionResult] = {}

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
            compatibility = compatibility_cache.state(key)
            road_evaluation = compatibility_cache.evaluation(key)
            road = road_evaluation.compatibility
            if not compatibility.ok or not road_evaluation.ok:
                body_cache[key] = core.BodyExternalGeneralizedForceState(
                    core.QuasiStaticStatus.FAILURE,
                    coordinate_order=core.BODY_ORDER,
                    coordinate_units=core.BODY_UNITS,
                    source_id=provider.gravity.record_id,
                    configuration_id=provider.source.configuration_id,
                    failure_code=core.QuasiStaticFailureCode.BODY_EXTERNAL_PROVIDER_FAILURE,
                    message=compatibility.message or road_evaluation.message or "Compatible state unavailable for EQ-VEH-0018",
                )
                gravity_cache[key] = core.WUFRUnsprungGravityReductionResult(
                    core.WUFRStaticEquilibriumStatus.FAILURE,
                    source_id=provider.gravity.record_id,
                    configuration_id=provider.source.configuration_id,
                    failure_code=core.WUFRStaticEquilibriumFailureCode.BODY_EXTERNAL_FAILURE,
                    message=body_cache[key].message,
                )
            else:
                body, reduction = core._body_external_state(
                    provider,
                    key,
                    road,
                    compatibility.J_wb,
                    tuple(float(item.value) for item in road_evaluation.unsprung_gravity_forces),
                )
                body_cache[key] = body
                gravity_cache[key] = reduction
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

    final_key = tuple(float(value) for value in solve.q_body)
    body_external_provider(final_key)
    gravity_reduction = gravity_cache.get(final_key)
    pose = core._pose_from_q(provider, solve.q_body)
    road_contact = compatibility_cache.evaluation(final_key)
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
            gravity_reduction=gravity_reduction,
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
            gravity_reduction=gravity_reduction,
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
            gravity_reduction=gravity_reduction,
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
            gravity_reduction=gravity_reduction,
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
            gravity_reduction=gravity_reduction,
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
        gravity_reduction=gravity_reduction,
        road_contact=road_contact,
        contact_recovery=contact,
        energy_gradient=energy,
        physical_closure=closure,
        complete_static_road_reaction=True,
        installed_as_built_authority=False,
        historical_scale_reconstruction_used=False,
        message="WUFR uncorrelated design-intent static-gravity equilibrium converged",
    )
