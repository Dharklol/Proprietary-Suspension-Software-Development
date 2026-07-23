"""Target-provider contracts for nominal steering inverse-design development.

Target providers define what response is requested. They never replace the rigid
mechanism evaluator. Historical fits remain evidence-only target sources, while
synthetic targets are generated through ``MOD-STEER-0001`` for software recovery
benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import tomllib
from typing import Iterable

from ..core import GeometryError, SteeringGeometry, solve_sweep
from ..legacy_fits import load_wheel_angle_fits
from ..projection import projected_wheel_heading, reference_from_static_alignment
from .geometry import generate_candidate_geometry
from .roles import RequirementSet, resolve_candidate


class TargetDefinitionError(ValueError):
    """Raised when a target contract is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class SteeringTarget:
    """A unit-explicit left/right incremental wheel-heading target."""

    target_id: str
    version: str
    source_type: str
    authority: str
    input_quantity_id: str
    input_unit: str
    output_quantity_id: str
    output_unit: str
    inputs: tuple[float, ...]
    rack_displacements: tuple[float, ...]
    left_outputs: tuple[float, ...]
    right_outputs: tuple[float, ...]
    weights: tuple[float, ...]
    canonical_to_target_output_sign: float
    static_toe_out_deg: float
    static_camber_deg: float
    normalization_scale_deg: float
    objective_weight: float
    require_monotonic_response: bool
    monotonic_tolerance_deg: float
    source_path: str
    provenance: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.target_id:
            raise TargetDefinitionError("target_id is required")
        count = len(self.inputs)
        if count < 3:
            raise TargetDefinitionError("A steering target requires at least three samples")
        series = (
            self.rack_displacements,
            self.left_outputs,
            self.right_outputs,
            self.weights,
        )
        if any(len(values) != count for values in series):
            raise TargetDefinitionError("All target series must have equal length")
        if not all(math.isfinite(value) for values in (self.inputs,) + series for value in values):
            raise TargetDefinitionError("Target series must contain only finite values")
        if not all(upper > lower for lower, upper in zip(self.inputs, self.inputs[1:])):
            raise TargetDefinitionError("Target inputs must be strictly increasing")
        if 0.0 not in self.inputs:
            raise TargetDefinitionError("Target inputs must include the centered 0 state")
        if not all(weight > 0.0 for weight in self.weights):
            raise TargetDefinitionError("Target weights must be positive")
        if self.canonical_to_target_output_sign not in {-1.0, 1.0}:
            raise TargetDefinitionError("canonical_to_target_output_sign must be +1 or -1")
        if not math.isfinite(self.normalization_scale_deg) or self.normalization_scale_deg <= 0.0:
            raise TargetDefinitionError("normalization_scale_deg must be finite and positive")
        if not math.isfinite(self.objective_weight) or self.objective_weight <= 0.0:
            raise TargetDefinitionError("objective_weight must be finite and positive")
        if not math.isfinite(self.monotonic_tolerance_deg) or self.monotonic_tolerance_deg < 0.0:
            raise TargetDefinitionError("monotonic_tolerance_deg must be finite and nonnegative")

    @property
    def left_monotonic_sign(self) -> float:
        delta = self.left_outputs[-1] - self.left_outputs[0]
        return 1.0 if delta >= 0.0 else -1.0

    @property
    def right_monotonic_sign(self) -> float:
        delta = self.right_outputs[-1] - self.right_outputs[0]
        return 1.0 if delta >= 0.0 else -1.0


@dataclass(frozen=True)
class SyntheticRecoveryFixture:
    """Analyzer-generated target plus the source candidate and recovery contract."""

    target: SteeringTarget
    source_candidate_values: tuple[tuple[str, float], ...]
    active_variable_ids: tuple[str, ...]
    recovery_tolerance: float
    objective_tolerance_deg_rms: float
    seed: int
    source_path: str


def _float_tuple(values: Iterable[object], *, name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result:
        raise TargetDefinitionError(f"{name} cannot be empty")
    if not all(math.isfinite(value) for value in result):
        raise TargetDefinitionError(f"{name} must contain finite values")
    return result


def load_historical_fit_target(path: str | Path) -> SteeringTarget:
    """Load the frozen WUFR-26/27 polynomial-fit regression target."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type")) != "historical_polynomial_fit":
        raise TargetDefinitionError("Target source_type is not historical_polynomial_fit")

    root = source_path.resolve().parents[2]
    source = document["source"]
    fit_path = root / str(source["fit_path"])
    fit_id = str(source["fit_id"])
    fits = load_wheel_angle_fits(fit_path)
    if fit_id not in fits:
        raise TargetDefinitionError(f"Historical fit {fit_id!r} is unavailable")
    fit = fits[fit_id]

    signals = document["signals"]
    adapter = document["adapter"]
    sampling = document["sampling"]
    objective = document["objective"]
    constraints = document["constraints"]
    inputs = _float_tuple(sampling["inputs_deg"], name="inputs_deg")
    weights = _float_tuple(sampling["weights"], name="weights")
    input_sign = float(adapter["input_sign"])
    if input_sign not in {-1.0, 1.0}:
        raise TargetDefinitionError("Historical target input_sign must be +1 or -1")
    rack_gain = float(adapter["rack_metres_per_input_degree"])
    if not math.isfinite(rack_gain) or rack_gain <= 0.0:
        raise TargetDefinitionError("rack_metres_per_input_degree must be positive")

    return SteeringTarget(
        target_id=str(document["target_id"]),
        version=str(document.get("version", "0")),
        source_type="historical_polynomial_fit",
        authority=str(document.get("authority", "")),
        input_quantity_id=str(signals["input_quantity_id"]),
        input_unit=str(signals["input_unit"]),
        output_quantity_id=str(signals["output_quantity_id"]),
        output_unit=str(signals["output_unit"]),
        inputs=inputs,
        rack_displacements=tuple(input_sign * value * rack_gain for value in inputs),
        left_outputs=tuple(fit.left_incremental_deg(value) for value in inputs),
        right_outputs=tuple(fit.right_incremental_deg(value) for value in inputs),
        weights=weights,
        canonical_to_target_output_sign=float(adapter["canonical_to_target_output_sign"]),
        static_toe_out_deg=float(adapter["static_toe_out_deg"]),
        static_camber_deg=float(adapter["static_camber_deg"]),
        normalization_scale_deg=float(objective["normalization_scale_deg"]),
        objective_weight=float(objective["weight"]),
        require_monotonic_response=bool(constraints["require_monotonic_response"]),
        monotonic_tolerance_deg=float(constraints["monotonic_tolerance_deg"]),
        source_path=str(source_path),
        provenance=(
            ("fit_id", fit_id),
            ("fit_path", str(fit_path)),
            ("fit_source_id", str(source.get("fit_source_id", ""))),
            ("level_e_contract", str(source.get("level_e_contract", ""))),
        ),
    )


def build_analyzer_incremental_target(
    geometry: SteeringGeometry,
    *,
    target_id: str,
    version: str,
    source_type: str,
    authority: str,
    inputs_deg: tuple[float, ...],
    rack_metres_per_input_degree: float,
    weights: tuple[float, ...] | None = None,
    canonical_to_target_output_sign: float = 1.0,
    static_toe_out_deg: float = -1.0,
    static_camber_deg: float = -2.25,
    normalization_scale_deg: float = 1.0,
    objective_weight: float = 1.0,
    require_monotonic_response: bool = True,
    monotonic_tolerance_deg: float = 1.0e-9,
    source_path: str = "",
    provenance: tuple[tuple[str, str], ...] = (),
) -> SteeringTarget:
    """Generate a synthetic target through the authoritative rigid analyzer."""

    if canonical_to_target_output_sign not in {-1.0, 1.0}:
        raise TargetDefinitionError("canonical_to_target_output_sign must be +1 or -1")
    rack_displacements = tuple(
        float(value) * float(rack_metres_per_input_degree) for value in inputs_deg
    )
    solved = solve_sweep(geometry, rack_displacements)
    outputs: dict[str, tuple[float, ...]] = {}
    for side in ("left", "right"):
        corner = geometry.left if side == "left" else geometry.right
        reference = reference_from_static_alignment(
            side,
            toe_out=math.radians(static_toe_out_deg),
            camber=math.radians(static_camber_deg),
            source_role=f"{target_id} synthetic reference alignment",
        )
        values: list[float] = []
        for state in solved[side]:
            if not state.ok or state.upright_rotation is None:
                raise GeometryError(
                    f"Synthetic target source geometry failed on {side} at "
                    f"{state.rack_displacement:.17g} m: {state.message}"
                )
            _, incremental = projected_wheel_heading(
                corner, reference, state.upright_rotation
            )
            values.append(canonical_to_target_output_sign * math.degrees(incremental))
        outputs[side] = tuple(values)

    return SteeringTarget(
        target_id=target_id,
        version=version,
        source_type=source_type,
        authority=authority,
        input_quantity_id="steering_or_pinion_input_angle_design_study",
        input_unit="deg",
        output_quantity_id="centered_projected_road_wheel_heading",
        output_unit="deg",
        inputs=tuple(float(value) for value in inputs_deg),
        rack_displacements=rack_displacements,
        left_outputs=outputs["left"],
        right_outputs=outputs["right"],
        weights=(weights if weights is not None else tuple(1.0 for _ in inputs_deg)),
        canonical_to_target_output_sign=canonical_to_target_output_sign,
        static_toe_out_deg=static_toe_out_deg,
        static_camber_deg=static_camber_deg,
        normalization_scale_deg=normalization_scale_deg,
        objective_weight=objective_weight,
        require_monotonic_response=require_monotonic_response,
        monotonic_tolerance_deg=monotonic_tolerance_deg,
        source_path=source_path,
        provenance=provenance,
    )


def load_synthetic_recovery_fixture(
    path: str | Path,
    baseline: SteeringGeometry,
    requirement_set: RequirementSet,
) -> SyntheticRecoveryFixture:
    """Load and generate the frozen Level A synthetic recovery target."""

    source_path = Path(path)
    with source_path.open("rb") as stream:
        document = tomllib.load(stream)
    if str(document.get("source_type")) != "analyzer_generated_synthetic":
        raise TargetDefinitionError("Synthetic fixture source_type is invalid")
    if str(document.get("baseline_configuration_id")) != baseline.geometry_id:
        raise TargetDefinitionError("Synthetic fixture baseline identity does not match")
    if str(document.get("requirement_set_id")) != requirement_set.id:
        raise TargetDefinitionError("Synthetic fixture requirement-set identity does not match")

    candidate_values = {
        key: float(value) for key, value in document["source_candidate"].items()
    }
    candidate = resolve_candidate(
        requirement_set,
        candidate_values,
        candidate_id=f"{document['target_id']}:SOURCE",
    )
    generated = generate_candidate_geometry(baseline, requirement_set, candidate)
    signals = document["signals"]
    inputs = _float_tuple(signals["inputs_deg"], name="synthetic inputs_deg")
    weights = _float_tuple(signals["weights"], name="synthetic weights")
    target = build_analyzer_incremental_target(
        generated.geometry,
        target_id=str(document["target_id"]),
        version=str(document.get("version", "0")),
        source_type="analyzer_generated_synthetic",
        authority=str(document.get("authority", "")),
        inputs_deg=inputs,
        rack_metres_per_input_degree=float(signals["rack_metres_per_input_degree"]),
        weights=weights,
        canonical_to_target_output_sign=float(
            signals["canonical_to_target_output_sign"]
        ),
        static_toe_out_deg=float(signals["static_toe_out_deg"]),
        static_camber_deg=float(signals["static_camber_deg"]),
        source_path=str(source_path),
        provenance=(
            ("source_candidate_id", candidate.candidate_id),
            ("baseline_geometry_id", baseline.geometry_id),
            ("requirement_set_id", requirement_set.id),
            ("evaluator_model_id", "MOD-STEER-0001"),
        ),
    )
    problem = document["search_problem"]
    method = document["method"]
    return SyntheticRecoveryFixture(
        target=target,
        source_candidate_values=tuple(sorted(candidate_values.items())),
        active_variable_ids=tuple(str(value) for value in problem["active_variable_ids"]),
        recovery_tolerance=float(problem["recovery_tolerance"]),
        objective_tolerance_deg_rms=float(problem["objective_tolerance_deg_rms"]),
        seed=int(method["seed"]),
        source_path=str(source_path),
    )
