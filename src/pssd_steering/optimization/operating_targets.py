"""Operating-state target contracts for multi-state steering optimization.

This module assigns explicit target curves and weights to provider-supplied
suspension states.  It does not generate tire physics or suspension kinematics.
Every target remains a request evaluated through the existing pose layer and
``MOD-STEER-0001`` mechanism solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import tomllib
from typing import Iterable, Mapping

from ..core import SteeringGeometry
from .multistate import evaluate_candidate_over_pose_set
from .poses import SuspensionPoseSet
from .roles import RequirementSet, resolve_candidate
from .targets import SteeringTarget, TargetDefinitionError


class OperatingTargetRole(str, Enum):
    OBJECTIVE = "objective"
    REPORT_ONLY = "report_only"


@dataclass(frozen=True)
class OperatingStateTarget:
    """One explicit objective or report-only disposition for a suspension state."""

    state_id: str
    role: OperatingTargetRole
    objective_id: str
    output_quantity_id: str
    output_unit: str
    left_outputs: tuple[float, ...] = ()
    right_outputs: tuple[float, ...] = ()
    sample_weights: tuple[float, ...] = ()
    normalization_scale_deg: float = 1.0
    objective_weight: float = 0.0
    canonical_to_target_output_sign: float = 1.0
    require_monotonic_response: bool = False
    monotonic_tolerance_deg: float = 0.0
    source_type: str = ""
    authority: str = ""
    source_path: str = ""
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id:
            raise TargetDefinitionError("Operating-state target requires state_id")
        if not self.objective_id:
            raise TargetDefinitionError("Operating-state target requires objective_id")
        if self.output_unit != "deg":
            raise TargetDefinitionError("The first operating-state heading target requires deg output")
        if self.canonical_to_target_output_sign not in {-1.0, 1.0}:
            raise TargetDefinitionError("canonical_to_target_output_sign must be +1 or -1")
        if not math.isfinite(self.monotonic_tolerance_deg) or self.monotonic_tolerance_deg < 0.0:
            raise TargetDefinitionError("monotonic_tolerance_deg must be finite and nonnegative")

        if self.role is OperatingTargetRole.REPORT_ONLY:
            if self.left_outputs or self.right_outputs or self.sample_weights:
                raise TargetDefinitionError(
                    f"Report-only state {self.state_id!r} cannot silently carry target arrays"
                )
            if self.objective_weight != 0.0:
                raise TargetDefinitionError(
                    f"Report-only state {self.state_id!r} must have zero objective weight"
                )
            return

        count = len(self.left_outputs)
        if count < 3 or len(self.right_outputs) != count or len(self.sample_weights) != count:
            raise TargetDefinitionError(
                f"Objective state {self.state_id!r} requires equal left/right/weight arrays with at least three samples"
            )
        if not all(
            math.isfinite(value)
            for values in (self.left_outputs, self.right_outputs, self.sample_weights)
            for value in values
        ):
            raise TargetDefinitionError(f"Objective state {self.state_id!r} contains nonfinite values")
        if not all(weight > 0.0 for weight in self.sample_weights):
            raise TargetDefinitionError(f"Objective state {self.state_id!r} sample weights must be positive")
        if not math.isfinite(self.normalization_scale_deg) or self.normalization_scale_deg <= 0.0:
            raise TargetDefinitionError("normalization_scale_deg must be finite and positive")
        if not math.isfinite(self.objective_weight) or self.objective_weight <= 0.0:
            raise TargetDefinitionError("Objective-state weight must be finite and positive")

    @property
    def left_monotonic_sign(self) -> float:
        if self.role is not OperatingTargetRole.OBJECTIVE:
            raise TargetDefinitionError("Report-only state has no monotonic target direction")
        return 1.0 if self.left_outputs[-1] - self.left_outputs[0] >= 0.0 else -1.0

    @property
    def right_monotonic_sign(self) -> float:
        if self.role is not OperatingTargetRole.OBJECTIVE:
            raise TargetDefinitionError("Report-only state has no monotonic target direction")
        return 1.0 if self.right_outputs[-1] - self.right_outputs[0] >= 0.0 else -1.0


@dataclass(frozen=True)
class OperatingStateTargetSet:
    """State-aware steering target set sharing one explicit rack sampling contract."""

    target_set_id: str
    version: str
    pose_set_id: str
    sampling_target: SteeringTarget
    state_targets: tuple[OperatingStateTarget, ...]
    aggregation_method: str
    unlisted_state_role: OperatingTargetRole
    authority: str
    source_path: str
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.target_set_id:
            raise TargetDefinitionError("target_set_id is required")
        if not self.pose_set_id:
            raise TargetDefinitionError("pose_set_id is required")
        if self.aggregation_method != "sum_weighted_normalized_state_rms":
            raise TargetDefinitionError("Unsupported operating-state aggregation method")
        if self.unlisted_state_role is not OperatingTargetRole.REPORT_ONLY:
            raise TargetDefinitionError(
                "The first operating-state contract requires unlisted states to be explicitly report_only"
            )
        ids = [item.state_id for item in self.state_targets]
        if len(ids) != len(set(ids)):
            raise TargetDefinitionError("Operating-state target set contains duplicate state IDs")
        if not any(item.role is OperatingTargetRole.OBJECTIVE for item in self.state_targets):
            raise TargetDefinitionError("At least one suspension state must carry an objective")
        for item in self.state_targets:
            if item.role is OperatingTargetRole.OBJECTIVE:
                count = len(self.sampling_target.rack_displacements)
                if len(item.left_outputs) != count:
                    raise TargetDefinitionError(
                        f"State {item.state_id!r} target length does not match the shared rack sampling contract"
                    )

    @property
    def state_map(self) -> dict[str, OperatingStateTarget]:
        return {item.state_id: item for item in self.state_targets}

    @property
    def objective_states(self) -> tuple[OperatingStateTarget, ...]:
        return tuple(item for item in self.state_targets if item.role is OperatingTargetRole.OBJECTIVE)

    def state_target(self, state_id: str) -> OperatingStateTarget:
        return self.state_map.get(
            state_id,
            OperatingStateTarget(
                state_id=state_id,
                role=self.unlisted_state_role,
                objective_id=f"report_only:{state_id}",
                output_quantity_id="incremental_projected_road_wheel_heading_from_pose",
                output_unit="deg",
                objective_weight=0.0,
                source_type="unlisted_state_policy",
                authority=self.authority,
                source_path=self.source_path,
            ),
        )


@dataclass(frozen=True)
class SyntheticOperatingTargetFixture:
    """Analyzer-generated multi-state target plus a deterministic recovery contract."""

    target_set: OperatingStateTargetSet
    source_candidate_values: tuple[tuple[str, float], ...]
    active_variable_ids: tuple[str, ...]
    recovery_tolerance: float
    objective_tolerance: float
    seed: int
    source_path: str


def _float_tuple(values: Iterable[object], *, name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or not all(math.isfinite(value) for value in result):
        raise TargetDefinitionError(f"{name} must contain finite values")
    return result


def _validate_pose_coverage(target_set: OperatingStateTargetSet, pose_set: SuspensionPoseSet) -> None:
    if target_set.pose_set_id != pose_set.pose_set_id:
        raise TargetDefinitionError("Operating target pose_set_id does not match the loaded pose set")
    available = set(pose_set.state_map)
    unknown = sorted(set(target_set.state_map) - available)
    if unknown:
        raise TargetDefinitionError(f"Operating targets reference unknown pose states: {unknown}")


def build_analyzer_operating_state_target_set(
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    source_candidate_values: Mapping[str, float],
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
    *,
    target_set_id: str,
    version: str,
    objective_state_weights: Mapping[str, float],
    normalization_scales_deg: Mapping[str, float] | None = None,
    canonical_to_target_output_sign: float = 1.0,
    authority: str = "software_verification_only",
    source_path: str = "",
) -> OperatingStateTargetSet:
    """Generate state targets through the existing multi-state analyzer composition."""

    unknown = sorted(set(objective_state_weights) - set(pose_set.state_map))
    if unknown:
        raise TargetDefinitionError(f"Synthetic operating target references unknown states: {unknown}")
    if not objective_state_weights:
        raise TargetDefinitionError("Synthetic operating target requires at least one objective state")
    candidate = resolve_candidate(
        requirement_set,
        {key: float(value) for key, value in source_candidate_values.items()},
        candidate_id=f"{target_set_id}:SOURCE",
    )
    evaluated = evaluate_candidate_over_pose_set(
        baseline, requirement_set, candidate, sampling_target, pose_set
    )
    if not evaluated.feasible:
        failed = [state.state_id for state in evaluated.states if not state.feasible]
        raise TargetDefinitionError(
            f"Synthetic operating-target source candidate is infeasible at states {failed}"
        )

    scales = dict(normalization_scales_deg or {})
    state_targets: list[OperatingStateTarget] = []
    for state in evaluated.states:
        if state.state_id not in objective_state_weights:
            continue
        weight = float(objective_state_weights[state.state_id])
        scale = float(scales.get(state.state_id, sampling_target.normalization_scale_deg))
        state_targets.append(
            OperatingStateTarget(
                state_id=state.state_id,
                role=OperatingTargetRole.OBJECTIVE,
                objective_id=f"wheel_heading_target_error:{state.state_id}",
                output_quantity_id="incremental_projected_road_wheel_heading_from_pose",
                output_unit="deg",
                left_outputs=tuple(
                    canonical_to_target_output_sign * value
                    for value in state.left_incremental_from_pose_deg
                ),
                right_outputs=tuple(
                    canonical_to_target_output_sign * value
                    for value in state.right_incremental_from_pose_deg
                ),
                sample_weights=sampling_target.weights,
                normalization_scale_deg=scale,
                objective_weight=weight,
                canonical_to_target_output_sign=canonical_to_target_output_sign,
                require_monotonic_response=sampling_target.require_monotonic_response,
                monotonic_tolerance_deg=sampling_target.monotonic_tolerance_deg,
                source_type="analyzer_generated_multistate_synthetic",
                authority=authority,
                source_path=source_path,
                provenance=(
                    ("source_candidate_id", candidate.candidate_id),
                    ("pose_state_id", state.state_id),
                    ("evaluator_model_id", "MOD-STEER-0001"),
                ),
            )
        )

    target_set = OperatingStateTargetSet(
        target_set_id=target_set_id,
        version=version,
        pose_set_id=pose_set.pose_set_id,
        sampling_target=sampling_target,
        state_targets=tuple(state_targets),
        aggregation_method="sum_weighted_normalized_state_rms",
        unlisted_state_role=OperatingTargetRole.REPORT_ONLY,
        authority=authority,
        source_path=source_path,
        provenance=(
            ("source_candidate_id", candidate.candidate_id),
            ("sampling_target_id", sampling_target.target_id),
            ("pose_set_id", pose_set.pose_set_id),
            ("evaluator_model_id", "MOD-STEER-0001"),
        ),
    )
    _validate_pose_coverage(target_set, pose_set)
    return target_set


def load_explicit_operating_state_target_set(
    path: str | Path,
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
) -> OperatingStateTargetSet:
    """Load explicit state targets from a provider-neutral TOML table."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type")) != "explicit_operating_state_targets":
        raise TargetDefinitionError("Operating target source_type is not explicit_operating_state_targets")
    if str(document.get("pose_set_id")) != pose_set.pose_set_id:
        raise TargetDefinitionError("Explicit operating target pose_set_id does not match")
    if str(document.get("sampling_target_id")) != sampling_target.target_id:
        raise TargetDefinitionError("Explicit operating target sampling_target_id does not match")

    unlisted_role = OperatingTargetRole(str(document.get("unlisted_state_role", "")))
    targets: list[OperatingStateTarget] = []
    for table in document.get("states", []):
        role = OperatingTargetRole(str(table.get("role", "")))
        if role is OperatingTargetRole.REPORT_ONLY:
            targets.append(
                OperatingStateTarget(
                    state_id=str(table.get("id", "")),
                    role=role,
                    objective_id=str(table.get("objective_id", f"report_only:{table.get('id', '')}")),
                    output_quantity_id=str(
                        table.get(
                            "output_quantity_id",
                            "incremental_projected_road_wheel_heading_from_pose",
                        )
                    ),
                    output_unit="deg",
                    objective_weight=0.0,
                    source_type=str(document.get("source_type")),
                    authority=str(table.get("authority", document.get("authority", ""))),
                    source_path=str(source_path),
                )
            )
            continue
        targets.append(
            OperatingStateTarget(
                state_id=str(table.get("id", "")),
                role=role,
                objective_id=str(table.get("objective_id", "wheel_heading_target_error")),
                output_quantity_id=str(
                    table.get(
                        "output_quantity_id",
                        "incremental_projected_road_wheel_heading_from_pose",
                    )
                ),
                output_unit=str(table.get("output_unit", "deg")),
                left_outputs=_float_tuple(table.get("left_outputs_deg", []), name="left_outputs_deg"),
                right_outputs=_float_tuple(table.get("right_outputs_deg", []), name="right_outputs_deg"),
                sample_weights=(
                    _float_tuple(table["sample_weights"], name="sample_weights")
                    if "sample_weights" in table
                    else sampling_target.weights
                ),
                normalization_scale_deg=float(table.get("normalization_scale_deg", 1.0)),
                objective_weight=float(table.get("objective_weight", 1.0)),
                canonical_to_target_output_sign=float(
                    table.get("canonical_to_target_output_sign", 1.0)
                ),
                require_monotonic_response=bool(table.get("require_monotonic_response", False)),
                monotonic_tolerance_deg=float(table.get("monotonic_tolerance_deg", 0.0)),
                source_type=str(document.get("source_type")),
                authority=str(table.get("authority", document.get("authority", ""))),
                source_path=str(source_path),
            )
        )

    target_set = OperatingStateTargetSet(
        target_set_id=str(document.get("target_set_id", "")),
        version=str(document.get("version", "0")),
        pose_set_id=pose_set.pose_set_id,
        sampling_target=sampling_target,
        state_targets=tuple(targets),
        aggregation_method=str(document.get("aggregation_method", "")),
        unlisted_state_role=unlisted_role,
        authority=str(document.get("authority", "")),
        source_path=str(source_path),
    )
    _validate_pose_coverage(target_set, pose_set)
    return target_set


def load_synthetic_operating_target_fixture(
    path: str | Path,
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
    sampling_target: SteeringTarget,
    pose_set: SuspensionPoseSet,
) -> SyntheticOperatingTargetFixture:
    """Load and generate the frozen analyzer-based multi-state recovery problem."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type")) != "analyzer_generated_multistate_synthetic":
        raise TargetDefinitionError("Synthetic operating-target fixture source_type is invalid")
    if str(document.get("baseline_configuration_id")) != baseline.geometry_id:
        raise TargetDefinitionError("Synthetic operating-target baseline identity does not match")
    if str(document.get("requirement_set_id")) != requirement_set.id:
        raise TargetDefinitionError("Synthetic operating-target requirement-set identity does not match")
    if str(document.get("pose_set_id")) != pose_set.pose_set_id:
        raise TargetDefinitionError("Synthetic operating-target pose-set identity does not match")
    if str(document.get("sampling_target_id")) != sampling_target.target_id:
        raise TargetDefinitionError("Synthetic operating-target sampling identity does not match")

    source_values = {key: float(value) for key, value in document["source_candidate"].items()}
    weights = {
        str(item["state_id"]): float(item["objective_weight"])
        for item in document.get("objective_states", [])
    }
    scales = {
        str(item["state_id"]): float(item.get("normalization_scale_deg", sampling_target.normalization_scale_deg))
        for item in document.get("objective_states", [])
    }
    target_set = build_analyzer_operating_state_target_set(
        baseline,
        requirement_set,
        source_values,
        sampling_target,
        pose_set,
        target_set_id=str(document.get("target_set_id", "")),
        version=str(document.get("version", "0")),
        objective_state_weights=weights,
        normalization_scales_deg=scales,
        canonical_to_target_output_sign=float(document.get("canonical_to_target_output_sign", 1.0)),
        authority=str(document.get("authority", "")),
        source_path=str(source_path),
    )
    problem = document["search_problem"]
    method = document["method"]
    return SyntheticOperatingTargetFixture(
        target_set=target_set,
        source_candidate_values=tuple(sorted(source_values.items())),
        active_variable_ids=tuple(str(value) for value in problem["active_variable_ids"]),
        recovery_tolerance=float(problem["recovery_tolerance"]),
        objective_tolerance=float(problem["objective_tolerance"]),
        seed=int(method["seed"]),
        source_path=str(source_path),
    )
