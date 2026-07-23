"""Evaluate steering candidates over provider-supplied suspension poses.

No suspension kinematics are solved here. Each pose is applied to the generated
candidate and every rack state is solved through MOD-STEER-0001.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ..core import PositionResult, SteeringGeometry, solve_sweep
from ..projection import projected_wheel_heading, reference_from_static_alignment
from .geometry import GeneratedSteeringGeometry, generate_candidate_geometry
from .poses import PosedSteeringGeometry, SuspensionPoseSet, apply_pose_state, transform_wheel_plane
from .roles import RequirementSet, ResolvedCandidate
from .targets import SteeringTarget


@dataclass(frozen=True)
class PoseStateEvaluation:
    state_id: str
    feasible: bool
    geometry: SteeringGeometry
    analyzer_results: tuple[tuple[str, tuple[PositionResult, ...]], ...]
    left_total_heading_deg: tuple[float, ...]
    right_total_heading_deg: tuple[float, ...]
    left_incremental_from_pose_deg: tuple[float, ...]
    right_incremental_from_pose_deg: tuple[float, ...]
    center_left_total_heading_deg: float | None
    center_right_total_heading_deg: float | None
    center_left_global_heading_change_deg: float | None
    center_right_global_heading_change_deg: float | None
    center_left_side_local_toe_out_change_deg: float | None
    center_right_side_local_toe_out_change_deg: float | None
    minimum_singularity_ratio: float | None
    failure_code: str | None
    failure_message: str
    provenance: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MultiStateSteeringEvaluation:
    candidate_id: str
    requirement_set_id: str
    pose_set_id: str
    nominal_state_id: str
    target_id: str
    generated_nominal: GeneratedSteeringGeometry
    states: tuple[PoseStateEvaluation, ...]
    provenance: tuple[tuple[str, str], ...]

    @property
    def feasible(self) -> bool:
        return all(item.feasible for item in self.states)

    @property
    def state_map(self) -> dict[str, PoseStateEvaluation]:
        return {item.state_id: item for item in self.states}


def _wrapped_difference_deg(value: float, reference: float) -> float:
    difference = math.radians(value - reference)
    return math.degrees(math.atan2(math.sin(difference), math.cos(difference)))


def _state_failure(
    posed: PosedSteeringGeometry,
    solved: dict[str, list[PositionResult]],
    *,
    code: str,
    message: str,
) -> PoseStateEvaluation:
    return PoseStateEvaluation(
        state_id=posed.state.state_id,
        feasible=False,
        geometry=posed.geometry,
        analyzer_results=tuple((side, tuple(solved.get(side, []))) for side in ("left", "right")),
        left_total_heading_deg=(),
        right_total_heading_deg=(),
        left_incremental_from_pose_deg=(),
        right_incremental_from_pose_deg=(),
        center_left_total_heading_deg=None,
        center_right_total_heading_deg=None,
        center_left_global_heading_change_deg=None,
        center_right_global_heading_change_deg=None,
        center_left_side_local_toe_out_change_deg=None,
        center_right_side_local_toe_out_change_deg=None,
        minimum_singularity_ratio=None,
        failure_code=code,
        failure_message=message,
        provenance=(("evaluator_model_id", "MOD-STEER-0001"), ("pose_state_id", posed.state.state_id)),
    )


def evaluate_candidate_over_pose_set(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    candidate: ResolvedCandidate,
    target: SteeringTarget,
    pose_set: SuspensionPoseSet,
) -> MultiStateSteeringEvaluation:
    """Evaluate one candidate across all named zero-steer suspension poses.

    The target supplies the rack sweep and nominal alignment basis only. Target
    values are not imposed as objectives at non-nominal poses in this release.
    """

    generated = generate_candidate_geometry(baseline, requirement_set, candidate)
    nominal_references = {
        side: reference_from_static_alignment(
            side,
            toe_out=math.radians(target.static_toe_out_deg),
            camber=math.radians(target.static_camber_deg),
            source_role=f"{target.target_id} nominal alignment for pose evaluation",
        )
        for side in ("left", "right")
    }
    try:
        center_index = target.rack_displacements.index(0.0)
    except ValueError as exc:
        raise ValueError("Pose-state evaluation requires an exact rack-center sample") from exc

    state_results: list[PoseStateEvaluation] = []
    for state in pose_set.states:
        posed = apply_pose_state(generated, state)
        solved = solve_sweep(posed.geometry, target.rack_displacements)
        failures = [result for side in ("left", "right") for result in solved[side] if not result.ok]
        if failures:
            first = failures[0]
            code = first.failure_code.value if first.failure_code is not None else "unknown"
            state_results.append(
                _state_failure(
                    posed,
                    solved,
                    code=code,
                    message=f"{first.side}@{first.rack_displacement:.17g} m: {first.message}",
                )
            )
            continue

        outputs: dict[str, list[float]] = {"left": [], "right": []}
        incremental: dict[str, list[float]] = {"left": [], "right": []}
        try:
            for side in ("left", "right"):
                transform = state.left_transform if side == "left" else state.right_transform
                reference = transform_wheel_plane(nominal_references[side], transform)
                corner = posed.geometry.left if side == "left" else posed.geometry.right
                for result in solved[side]:
                    if result.upright_rotation is None:
                        raise ValueError("Successful analyzer state is missing upright rotation")
                    total, delta = projected_wheel_heading(corner, reference, result.upright_rotation)
                    outputs[side].append(math.degrees(total))
                    incremental[side].append(math.degrees(delta))
        except (ValueError, ArithmeticError) as exc:
            state_results.append(_state_failure(posed, solved, code="wheel_plane_projection", message=str(exc)))
            continue

        singularity_values = [
            result.singularity_ratio_to_reference
            for side in ("left", "right")
            for result in solved[side]
            if result.singularity_ratio_to_reference is not None
        ]
        state_results.append(
            PoseStateEvaluation(
                state_id=state.state_id,
                feasible=True,
                geometry=posed.geometry,
                analyzer_results=tuple((side, tuple(solved[side])) for side in ("left", "right")),
                left_total_heading_deg=tuple(outputs["left"]),
                right_total_heading_deg=tuple(outputs["right"]),
                left_incremental_from_pose_deg=tuple(incremental["left"]),
                right_incremental_from_pose_deg=tuple(incremental["right"]),
                center_left_total_heading_deg=outputs["left"][center_index],
                center_right_total_heading_deg=outputs["right"][center_index],
                center_left_global_heading_change_deg=None,
                center_right_global_heading_change_deg=None,
                center_left_side_local_toe_out_change_deg=None,
                center_right_side_local_toe_out_change_deg=None,
                minimum_singularity_ratio=min(singularity_values) if singularity_values else None,
                failure_code=None,
                failure_message="",
                provenance=(
                    ("evaluator_model_id", "MOD-STEER-0001"),
                    ("pose_state_id", state.state_id),
                    ("pose_source_type", state.source_type),
                    ("pose_source_path", state.source_path),
                    ("pose_authority", state.authority),
                    ("target_id_for_rack_domain_and_alignment", target.target_id),
                ),
            )
        )

    state_map = {item.state_id: item for item in state_results}
    nominal = state_map[pose_set.nominal_state_id]
    if not nominal.feasible:
        raise ValueError("The declared nominal suspension pose must evaluate successfully")
    if nominal.center_left_total_heading_deg is None or nominal.center_right_total_heading_deg is None:
        raise ValueError("Nominal pose is missing centered heading outputs")

    completed: list[PoseStateEvaluation] = []
    for item in state_results:
        if not item.feasible:
            completed.append(item)
            continue
        if item.center_left_total_heading_deg is None or item.center_right_total_heading_deg is None:
            raise ValueError(f"Pose {item.state_id!r} is missing centered heading outputs")
        left_delta = _wrapped_difference_deg(item.center_left_total_heading_deg, nominal.center_left_total_heading_deg)
        right_delta = _wrapped_difference_deg(item.center_right_total_heading_deg, nominal.center_right_total_heading_deg)
        completed.append(
            replace(
                item,
                center_left_global_heading_change_deg=left_delta,
                center_right_global_heading_change_deg=right_delta,
                center_left_side_local_toe_out_change_deg=left_delta,
                center_right_side_local_toe_out_change_deg=-right_delta,
            )
        )

    return MultiStateSteeringEvaluation(
        candidate_id=candidate.candidate_id,
        requirement_set_id=requirement_set.id,
        pose_set_id=pose_set.pose_set_id,
        nominal_state_id=pose_set.nominal_state_id,
        target_id=target.target_id,
        generated_nominal=generated,
        states=tuple(completed),
        provenance=(
            ("evaluator_model_id", "MOD-STEER-0001"),
            ("optimizer_model_id", "MOD-STEER-0002"),
            ("pose_set_id", pose_set.pose_set_id),
            ("pose_set_source_path", pose_set.source_path),
            ("pose_set_authority", pose_set.authority),
            ("provider_scope", "nonphysical_pose_input_only"),
        ),
    )
