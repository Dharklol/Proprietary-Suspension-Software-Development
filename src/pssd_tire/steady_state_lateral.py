"""Provider-neutral steady-state pure-lateral tire response kernel.

The implementation is intentionally source bounded.  It evaluates immutable
signed ``Fy(alpha)`` tables, performs complete-cell interpolation in normal
load, inclination, and pressure, and inverts the resulting piecewise-linear
response without smoothing, extrapolation, hidden symmetry, or arbitrary
branch selection.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from math import isfinite
from typing import Final, Iterable

_KNOT_TOLERANCE_RAD: Final[float] = 1.0e-12
_STATE_TOLERANCE: Final[float] = 1.0e-12
_SLOPE_TOLERANCE: Final[float] = 1.0e-12
_FORCE_TOLERANCE_N: Final[float] = 1.0e-9

R25B_SOURCE_TIRE_ID: Final[str] = "HOOSIER_43105_18X7.5-10_R25B"
SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED: Final[bool] = False


class SteadyStateLateralFailure(ValueError):
    """Structured fail-closed outcome from the bounded kernel."""

    def __init__(self, failure_code: str, message: str) -> None:
        super().__init__(message)
        self.failure_code = failure_code
        self.message = message


@dataclass(frozen=True, slots=True)
class SteadyStateLateralOperatingState:
    """Canonical query state for a steady-state pure-lateral response."""

    slip_angle_rad: float
    normal_load_N: float
    inclination_rad: float
    pressure_Pa: float
    state_id: str
    source_id: str
    source_convention_id: str

    def __post_init__(self) -> None:
        if not isfinite(self.slip_angle_rad):
            raise SteadyStateLateralFailure("nonfinite_input", "slip_angle_rad must be finite")
        if not isfinite(self.normal_load_N) or self.normal_load_N <= 0.0:
            raise SteadyStateLateralFailure(
                "invalid_normal_load", "normal_load_N must be finite and positive"
            )
        if not isfinite(self.inclination_rad):
            raise SteadyStateLateralFailure(
                "nonfinite_input", "inclination_rad must be finite"
            )
        if not isfinite(self.pressure_Pa) or self.pressure_Pa <= 0.0:
            raise SteadyStateLateralFailure(
                "invalid_pressure", "pressure_Pa must be finite and positive"
            )
        if not self.state_id:
            raise SteadyStateLateralFailure("nonfinite_input", "state_id is required")
        if not self.source_id:
            raise SteadyStateLateralFailure("nonfinite_input", "source_id is required")
        if not self.source_convention_id:
            raise SteadyStateLateralFailure(
                "nonfinite_input", "source_convention_id is required"
            )


@dataclass(frozen=True, slots=True)
class SteadyStateLateralCurve:
    """Immutable signed ``Fy(alpha)`` source curve at one operating state."""

    curve_id: str
    normal_load_N: float
    inclination_rad: float
    pressure_Pa: float
    slip_angle_rad: tuple[float, ...]
    lateral_force_N: tuple[float, ...]
    source_tire_id: str
    intended_tire_id: str
    source_path: str
    source_hash: str
    source_convention_id: str
    adapter_id: str
    fidelity_label: str
    domain_and_censor_metadata: tuple[str, ...] = ()
    source_preprocessing: tuple[str, ...] = ()
    source_branch_role: str = "complete_signed_curve"
    segment_branch_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required_strings = {
            "curve_id": self.curve_id,
            "source_tire_id": self.source_tire_id,
            "intended_tire_id": self.intended_tire_id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "source_convention_id": self.source_convention_id,
            "adapter_id": self.adapter_id,
            "fidelity_label": self.fidelity_label,
            "source_branch_role": self.source_branch_role,
        }
        missing = [name for name, value in required_strings.items() if not value]
        if missing:
            raise SteadyStateLateralFailure(
                "source_curve_invalid", f"required curve fields are empty: {', '.join(missing)}"
            )
        if not isfinite(self.normal_load_N) or self.normal_load_N <= 0.0:
            raise SteadyStateLateralFailure(
                "invalid_normal_load", "normal_load_N must be finite and positive"
            )
        if not isfinite(self.inclination_rad):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "inclination_rad must be finite"
            )
        if not isfinite(self.pressure_Pa) or self.pressure_Pa <= 0.0:
            raise SteadyStateLateralFailure(
                "invalid_pressure", "pressure_Pa must be finite and positive"
            )
        if len(self.slip_angle_rad) < 2:
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "at least two slip samples are required"
            )
        if len(self.slip_angle_rad) != len(self.lateral_force_N):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "slip and force arrays must have equal length"
            )
        if not all(isfinite(value) for value in self.slip_angle_rad):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "all slip samples must be finite"
            )
        if not all(isfinite(value) for value in self.lateral_force_N):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "all force samples must be finite"
            )
        if any(
            right <= left
            for left, right in zip(self.slip_angle_rad, self.slip_angle_rad[1:])
        ):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "slip samples must be strictly increasing"
            )
        if self.segment_branch_ids and len(self.segment_branch_ids) != len(self.slip_angle_rad) - 1:
            raise SteadyStateLateralFailure(
                "source_curve_invalid",
                "segment_branch_ids must be empty or contain one ID per source segment",
            )
        if any(not branch_id for branch_id in self.segment_branch_ids):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "segment branch IDs cannot be empty"
            )

    @property
    def state_key(self) -> tuple[float, float, float]:
        return (self.normal_load_N, self.inclination_rad, self.pressure_Pa)


@dataclass(frozen=True, slots=True)
class SteadyStateLateralTable:
    """Complete or partially complete collection of source curves."""

    table_id: str
    curves: tuple[SteadyStateLateralCurve, ...]

    def __post_init__(self) -> None:
        if not self.table_id:
            raise SteadyStateLateralFailure("source_curve_invalid", "table_id is required")
        if not self.curves:
            raise SteadyStateLateralFailure(
                "source_curve_unavailable", "at least one source curve is required"
            )
        curve_ids = [curve.curve_id for curve in self.curves]
        if len(set(curve_ids)) != len(curve_ids):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "duplicate curve IDs are not permitted"
            )
        state_keys = [curve.state_key for curve in self.curves]
        if len(set(state_keys)) != len(state_keys):
            raise SteadyStateLateralFailure(
                "source_curve_invalid", "duplicate operating-state curves are not permitted"
            )


@dataclass(frozen=True, slots=True)
class SteadyStateLateralResponse:
    """Successful forward-evaluation result."""

    ok: bool
    status: str
    failure_code: str | None
    message: str
    operating_state: SteadyStateLateralOperatingState
    lateral_force_N: float
    left_segment_slope_N_per_rad: float
    right_segment_slope_N_per_rad: float
    derivative_unique: bool
    participating_curve_ids: tuple[str, ...]
    slip_segment_ids: tuple[str, ...]
    state_interpolation_weights: tuple[tuple[str, float], ...]
    source_and_adapter_provenance: tuple[str, ...]
    domain_and_censor_metadata: tuple[str, ...]
    fidelity_label: str
    exact_knot: bool
    slip_interpolation_fractions: tuple[tuple[str, float], ...]

    @property
    def curve_id(self) -> str:
        """Backward-compatible singular identity for one-curve queries."""

        if len(self.participating_curve_ids) == 1:
            return self.participating_curve_ids[0]
        return "state_interpolated"

    @property
    def segment_ids(self) -> tuple[str, ...]:
        """Backward-compatible alias retained for the first implementation slice."""

        return self.slip_segment_ids

    @property
    def interpolation_fraction(self) -> float:
        """Return the single-curve fraction when it is unambiguous."""

        if len(self.slip_interpolation_fractions) != 1:
            return 0.0
        return self.slip_interpolation_fractions[0][1]


@dataclass(frozen=True, slots=True)
class SteadyStateLateralInverseCandidate:
    """One signed-slip root of a requested signed lateral-force demand."""

    slip_angle_rad: float
    segment_id: str
    branch_id: str
    interpolation_fraction: float
    source_curve_ids: tuple[str, ...]
    source_and_adapter_provenance: tuple[str, ...]
    contributing_segment_ids: tuple[str, ...]
    contributing_branch_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SteadyStateLateralInverseResult:
    """Successful multi-root inverse result."""

    ok: bool
    status: str
    failure_code: str | None
    message: str
    requested_lateral_force_N: float
    candidates: tuple[SteadyStateLateralInverseCandidate, ...]
    branch_selection_applied: bool
    selected_candidate: SteadyStateLateralInverseCandidate | None
    out_of_domain: bool


@dataclass(frozen=True, slots=True)
class _CellCurve:
    curve: SteadyStateLateralCurve
    weight: float


def _segment_slope(curve: SteadyStateLateralCurve, index: int) -> float:
    return (
        curve.lateral_force_N[index + 1] - curve.lateral_force_N[index]
    ) / (curve.slip_angle_rad[index + 1] - curve.slip_angle_rad[index])


def _segment_branch_id(curve: SteadyStateLateralCurve, index: int) -> str:
    if curve.segment_branch_ids:
        return curve.segment_branch_ids[index]
    return "unclassified"


def _curve_response(
    curve: SteadyStateLateralCurve,
    operating_state: SteadyStateLateralOperatingState,
    *,
    knot_tolerance_rad: float,
) -> tuple[float, float, float, bool, tuple[str, ...], bool, float]:
    slip_angle_rad = operating_state.slip_angle_rad
    minimum = curve.slip_angle_rad[0]
    maximum = curve.slip_angle_rad[-1]
    if (
        slip_angle_rad < minimum - knot_tolerance_rad
        or slip_angle_rad > maximum + knot_tolerance_rad
    ):
        raise SteadyStateLateralFailure(
            "slip_out_of_domain",
            f"slip_angle_rad={slip_angle_rad!r} is outside [{minimum!r}, {maximum!r}]",
        )

    for knot_index, knot in enumerate(curve.slip_angle_rad):
        if abs(slip_angle_rad - knot) <= knot_tolerance_rad:
            if knot_index == 0:
                slope = _segment_slope(curve, 0)
                left_slope = right_slope = slope
                segment_ids = (f"{curve.curve_id}:segment:0",)
            elif knot_index == len(curve.slip_angle_rad) - 1:
                slope = _segment_slope(curve, knot_index - 1)
                left_slope = right_slope = slope
                segment_ids = (f"{curve.curve_id}:segment:{knot_index - 1}",)
            else:
                left_slope = _segment_slope(curve, knot_index - 1)
                right_slope = _segment_slope(curve, knot_index)
                segment_ids = (
                    f"{curve.curve_id}:segment:{knot_index - 1}",
                    f"{curve.curve_id}:segment:{knot_index}",
                )
            return (
                curve.lateral_force_N[knot_index],
                left_slope,
                right_slope,
                abs(left_slope - right_slope) <= _SLOPE_TOLERANCE,
                segment_ids,
                True,
                0.0,
            )

    for index, (left_alpha, right_alpha) in enumerate(
        zip(curve.slip_angle_rad, curve.slip_angle_rad[1:])
    ):
        if left_alpha < slip_angle_rad < right_alpha:
            fraction = (slip_angle_rad - left_alpha) / (right_alpha - left_alpha)
            left_force = curve.lateral_force_N[index]
            right_force = curve.lateral_force_N[index + 1]
            force = left_force + fraction * (right_force - left_force)
            slope = _segment_slope(curve, index)
            return (
                force,
                slope,
                slope,
                True,
                (f"{curve.curve_id}:segment:{index}",),
                False,
                fraction,
            )

    raise SteadyStateLateralFailure(
        "slip_out_of_domain", "no source segment contains the requested slip angle"
    )


def evaluate_curve(
    curve: SteadyStateLateralCurve,
    slip_angle_rad: float,
    *,
    knot_tolerance_rad: float = _KNOT_TOLERANCE_RAD,
) -> SteadyStateLateralResponse:
    """Evaluate one validated source curve without clipping or extrapolation."""

    if not isfinite(knot_tolerance_rad) or knot_tolerance_rad < 0.0:
        raise ValueError("knot_tolerance_rad must be finite and non-negative")
    state = SteadyStateLateralOperatingState(
        slip_angle_rad=slip_angle_rad,
        normal_load_N=curve.normal_load_N,
        inclination_rad=curve.inclination_rad,
        pressure_Pa=curve.pressure_Pa,
        state_id=f"{curve.curve_id}:query",
        source_id=curve.source_tire_id,
        source_convention_id=curve.source_convention_id,
    )
    force, left_slope, right_slope, derivative_unique, segment_ids, exact_knot, fraction = (
        _curve_response(curve, state, knot_tolerance_rad=knot_tolerance_rad)
    )
    return SteadyStateLateralResponse(
        ok=True,
        status="ok",
        failure_code=None,
        message="exact source curve evaluation",
        operating_state=state,
        lateral_force_N=force,
        left_segment_slope_N_per_rad=left_slope,
        right_segment_slope_N_per_rad=right_slope,
        derivative_unique=derivative_unique,
        participating_curve_ids=(curve.curve_id,),
        slip_segment_ids=segment_ids,
        state_interpolation_weights=((curve.curve_id, 1.0),),
        source_and_adapter_provenance=(
            f"{curve.curve_id}|{curve.source_path}|{curve.source_hash}|{curve.adapter_id}",
        ),
        domain_and_censor_metadata=curve.domain_and_censor_metadata,
        fidelity_label=curve.fidelity_label,
        exact_knot=exact_knot,
        slip_interpolation_fractions=((curve.curve_id, fraction),),
    )


def _axis_weights(
    values: Iterable[float],
    query: float,
    *,
    failure_code: str,
    axis_name: str,
    tolerance: float = _STATE_TOLERANCE,
) -> tuple[tuple[float, float], ...]:
    axis = tuple(sorted(set(values)))
    for value in axis:
        if abs(query - value) <= tolerance:
            return ((value, 1.0),)
    if query < axis[0] - tolerance or query > axis[-1] + tolerance:
        raise SteadyStateLateralFailure(
            failure_code, f"{axis_name}={query!r} is outside [{axis[0]!r}, {axis[-1]!r}]"
        )
    for left, right in zip(axis, axis[1:]):
        if left < query < right:
            fraction = (query - left) / (right - left)
            return ((left, 1.0 - fraction), (right, fraction))
    raise SteadyStateLateralFailure(
        failure_code, f"no interpolation bracket contains {axis_name}={query!r}"
    )


def _identity_signature(curve: SteadyStateLateralCurve) -> tuple[str, ...]:
    return (
        curve.source_tire_id,
        curve.intended_tire_id,
        curve.source_convention_id,
        curve.adapter_id,
        curve.fidelity_label,
        curve.source_branch_role,
    )


def _select_cell(
    table: SteadyStateLateralTable,
    operating_state: SteadyStateLateralOperatingState,
) -> tuple[_CellCurve, ...]:
    load_weights = _axis_weights(
        (curve.normal_load_N for curve in table.curves),
        operating_state.normal_load_N,
        failure_code="operating_state_out_of_domain",
        axis_name="normal_load_N",
    )
    inclination_weights = _axis_weights(
        (curve.inclination_rad for curve in table.curves),
        operating_state.inclination_rad,
        failure_code="operating_state_out_of_domain",
        axis_name="inclination_rad",
    )
    pressure_weights = _axis_weights(
        (curve.pressure_Pa for curve in table.curves),
        operating_state.pressure_Pa,
        failure_code="operating_state_out_of_domain",
        axis_name="pressure_Pa",
    )

    selected: list[_CellCurve] = []
    state_corners = product(load_weights, inclination_weights, pressure_weights)
    for (load, load_weight), (inclination, inclination_weight), (
        pressure,
        pressure_weight,
    ) in state_corners:
        matches = [
            curve
            for curve in table.curves
            if abs(curve.normal_load_N - load) <= _STATE_TOLERANCE
            and abs(curve.inclination_rad - inclination) <= _STATE_TOLERANCE
            and abs(curve.pressure_Pa - pressure) <= _STATE_TOLERANCE
        ]
        if len(matches) != 1:
            raise SteadyStateLateralFailure(
                "interpolation_cell_incomplete",
                "every nonzero-weight operating-state corner must exist exactly once",
            )
        selected.append(
            _CellCurve(
                curve=matches[0],
                weight=load_weight * inclination_weight * pressure_weight,
            )
        )

    signatures = {_identity_signature(item.curve) for item in selected}
    if len(signatures) != 1:
        raise SteadyStateLateralFailure(
            "interpolation_identity_mismatch",
            "participating curves do not share compatible source, adapter, and fidelity identities",
        )
    first = selected[0].curve
    if operating_state.source_id != first.source_tire_id:
        raise SteadyStateLateralFailure(
            "source_identity_mismatch",
            "query source_id does not match the selected source tire identity",
        )
    if operating_state.source_convention_id != first.source_convention_id:
        raise SteadyStateLateralFailure(
            "source_adapter_mismatch",
            "query source convention does not match the selected canonical adapter family",
        )
    total_weight = sum(item.weight for item in selected)
    if abs(total_weight - 1.0) > 1.0e-12:
        raise SteadyStateLateralFailure(
            "interpolation_cell_incomplete", "state interpolation weights do not sum to one"
        )
    return tuple(selected)


def evaluate_table(
    table: SteadyStateLateralTable,
    operating_state: SteadyStateLateralOperatingState,
    *,
    knot_tolerance_rad: float = _KNOT_TOLERANCE_RAD,
) -> SteadyStateLateralResponse:
    """Evaluate a complete compatible operating-state interpolation cell."""

    if not isfinite(knot_tolerance_rad) or knot_tolerance_rad < 0.0:
        raise ValueError("knot_tolerance_rad must be finite and non-negative")
    cell = _select_cell(table, operating_state)

    force = 0.0
    left_slope = 0.0
    right_slope = 0.0
    segment_ids: list[str] = []
    exact_knot = True
    source_metadata: list[str] = []
    domain_metadata: list[str] = []
    fractions: list[tuple[str, float]] = []
    for item in cell:
        (
            curve_force,
            curve_left_slope,
            curve_right_slope,
            _,
            curve_segment_ids,
            curve_exact_knot,
            curve_fraction,
        ) = _curve_response(item.curve, operating_state, knot_tolerance_rad=knot_tolerance_rad)
        force += item.weight * curve_force
        left_slope += item.weight * curve_left_slope
        right_slope += item.weight * curve_right_slope
        segment_ids.extend(curve_segment_ids)
        exact_knot = exact_knot and curve_exact_knot
        source_metadata.append(
            "|".join(
                (
                    item.curve.curve_id,
                    item.curve.source_path,
                    item.curve.source_hash,
                    item.curve.adapter_id,
                )
            )
        )
        domain_metadata.extend(item.curve.domain_and_censor_metadata)
        fractions.append((item.curve.curve_id, curve_fraction))

    first = cell[0].curve
    return SteadyStateLateralResponse(
        ok=True,
        status="ok",
        failure_code=None,
        message="complete-cell multilinear operating-state interpolation",
        operating_state=operating_state,
        lateral_force_N=force,
        left_segment_slope_N_per_rad=left_slope,
        right_segment_slope_N_per_rad=right_slope,
        derivative_unique=abs(left_slope - right_slope) <= _SLOPE_TOLERANCE,
        participating_curve_ids=tuple(item.curve.curve_id for item in cell),
        slip_segment_ids=tuple(segment_ids),
        state_interpolation_weights=tuple(
            (item.curve.curve_id, item.weight) for item in cell
        ),
        source_and_adapter_provenance=tuple(source_metadata),
        domain_and_censor_metadata=tuple(dict.fromkeys(domain_metadata)),
        fidelity_label=first.fidelity_label,
        exact_knot=exact_knot,
        slip_interpolation_fractions=tuple(fractions),
    )


def _deduplicate_sorted(values: Iterable[float], tolerance: float) -> tuple[float, ...]:
    result: list[float] = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return tuple(result)


def _segment_details_at_midpoint(
    cell: tuple[_CellCurve, ...], midpoint: float
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    segment_ids: list[str] = []
    branch_ids: list[str] = []
    for item in cell:
        curve = item.curve
        segments = zip(curve.slip_angle_rad, curve.slip_angle_rad[1:])
        for index, (left, right) in enumerate(segments):
            if left < midpoint < right or abs(midpoint - left) <= _KNOT_TOLERANCE_RAD:
                segment_ids.append(f"{curve.curve_id}:segment:{index}")
                branch_ids.append(_segment_branch_id(curve, index))
                break
        else:
            raise SteadyStateLateralFailure(
                "slip_out_of_domain", "composite segment midpoint is not supported"
            )
    return tuple(segment_ids), tuple(dict.fromkeys(branch_ids))


def _merge_candidate(
    existing: SteadyStateLateralInverseCandidate,
    new: SteadyStateLateralInverseCandidate,
) -> SteadyStateLateralInverseCandidate:
    segments = tuple(
        dict.fromkeys(existing.contributing_segment_ids + new.contributing_segment_ids)
    )
    branches = tuple(
        dict.fromkeys(existing.contributing_branch_ids + new.contributing_branch_ids)
    )
    branch_id = branches[0] if len(branches) == 1 else "shared_branch_boundary"
    return replace(
        existing,
        segment_id="|".join(segments),
        branch_id=branch_id,
        contributing_segment_ids=segments,
        contributing_branch_ids=branches,
    )


def invert_lateral_force(
    table: SteadyStateLateralTable,
    *,
    normal_load_N: float,
    inclination_rad: float,
    pressure_Pa: float,
    requested_lateral_force_N: float,
    source_id: str,
    source_convention_id: str,
    state_id: str = "inverse_query",
    branch_selector: str | None = None,
    root_tolerance_rad: float = _KNOT_TOLERANCE_RAD,
    force_tolerance_N: float = _FORCE_TOLERANCE_N,
) -> SteadyStateLateralInverseResult:
    """Return every signed slip root of a signed force demand.

    The combined response is exactly piecewise linear on the union of all
    participating source-curve knots over their common supported slip domain.
    """

    if not isfinite(requested_lateral_force_N):
        raise SteadyStateLateralFailure(
            "nonfinite_input", "requested_lateral_force_N must be finite"
        )
    if not isfinite(root_tolerance_rad) or root_tolerance_rad < 0.0:
        raise ValueError("root_tolerance_rad must be finite and non-negative")
    if not isfinite(force_tolerance_N) or force_tolerance_N < 0.0:
        raise ValueError("force_tolerance_N must be finite and non-negative")

    seed_state = SteadyStateLateralOperatingState(
        slip_angle_rad=0.0,
        normal_load_N=normal_load_N,
        inclination_rad=inclination_rad,
        pressure_Pa=pressure_Pa,
        state_id=state_id,
        source_id=source_id,
        source_convention_id=source_convention_id,
    )
    cell = _select_cell(table, seed_state)
    common_minimum = max(item.curve.slip_angle_rad[0] for item in cell)
    common_maximum = min(item.curve.slip_angle_rad[-1] for item in cell)
    if common_minimum >= common_maximum:
        raise SteadyStateLateralFailure(
            "slip_out_of_domain", "participating curves have no common supported slip interval"
        )
    breakpoints = _deduplicate_sorted(
        (
            knot
            for item in cell
            for knot in item.curve.slip_angle_rad
            if common_minimum - root_tolerance_rad <= knot <= common_maximum + root_tolerance_rad
        ),
        root_tolerance_rad,
    )
    if breakpoints[0] > common_minimum + root_tolerance_rad:
        breakpoints = (common_minimum,) + breakpoints
    if breakpoints[-1] < common_maximum - root_tolerance_rad:
        breakpoints = breakpoints + (common_maximum,)

    evaluated: list[tuple[float, float]] = []
    for alpha in breakpoints:
        response = evaluate_table(
            table,
            replace(seed_state, slip_angle_rad=alpha),
            knot_tolerance_rad=root_tolerance_rad,
        )
        evaluated.append((alpha, response.lateral_force_N))

    candidates: list[SteadyStateLateralInverseCandidate] = []
    provenance = tuple(
        "|".join(
            (
                item.curve.curve_id,
                item.curve.source_path,
                item.curve.source_hash,
                item.curve.adapter_id,
            )
        )
        for item in cell
    )
    source_curve_ids = tuple(item.curve.curve_id for item in cell)

    for index, ((left_alpha, left_force), (right_alpha, right_force)) in enumerate(
        zip(evaluated, evaluated[1:])
    ):
        force_span = right_force - left_force
        midpoint = 0.5 * (left_alpha + right_alpha)
        segment_ids, branch_ids = _segment_details_at_midpoint(cell, midpoint)
        if abs(force_span) <= force_tolerance_N:
            if abs(requested_lateral_force_N - left_force) <= force_tolerance_N:
                raise SteadyStateLateralFailure(
                    "inverse_branch_ambiguous",
                    "a horizontal response interval coincides with the requested force",
                )
            continue
        minimum_force = min(left_force, right_force) - force_tolerance_N
        maximum_force = max(left_force, right_force) + force_tolerance_N
        if not (minimum_force <= requested_lateral_force_N <= maximum_force):
            continue
        fraction = (requested_lateral_force_N - left_force) / force_span
        if fraction < -1.0e-12 or fraction > 1.0 + 1.0e-12:
            continue
        fraction = min(1.0, max(0.0, fraction))
        alpha = left_alpha + fraction * (right_alpha - left_alpha)
        branch_id = branch_ids[0] if len(branch_ids) == 1 else "mixed_branch_segment"
        candidate = SteadyStateLateralInverseCandidate(
            slip_angle_rad=alpha,
            segment_id=f"{table.table_id}:composite_segment:{index}",
            branch_id=branch_id,
            interpolation_fraction=fraction,
            source_curve_ids=source_curve_ids,
            source_and_adapter_provenance=provenance,
            contributing_segment_ids=segment_ids,
            contributing_branch_ids=branch_ids,
        )
        for candidate_index, existing in enumerate(candidates):
            if abs(existing.slip_angle_rad - alpha) <= root_tolerance_rad:
                candidates[candidate_index] = _merge_candidate(existing, candidate)
                break
        else:
            candidates.append(candidate)

    if not candidates:
        raise SteadyStateLateralFailure(
            "force_demand_out_of_domain",
            "the requested signed lateral force has no root in the supported slip domain",
        )

    candidates_tuple = tuple(sorted(candidates, key=lambda candidate: candidate.slip_angle_rad))
    selected: SteadyStateLateralInverseCandidate | None = None
    if branch_selector is not None:
        selector_map = {
            "named_pre_peak_branch": "pre_peak",
            "named_post_peak_branch": "post_peak",
        }
        if branch_selector not in selector_map:
            raise SteadyStateLateralFailure(
                "inverse_branch_ambiguous", f"unrecognized branch selector: {branch_selector}"
            )
        requested_branch = selector_map[branch_selector]
        matches = [
            candidate
            for candidate in candidates_tuple
            if requested_branch in candidate.contributing_branch_ids
        ]
        if len(matches) != 1:
            raise SteadyStateLateralFailure(
                "inverse_branch_ambiguous",
                "the named branch selector does not identify exactly one source-declared root",
            )
        selected = matches[0]

    return SteadyStateLateralInverseResult(
        ok=True,
        status="multiple_roots" if len(candidates_tuple) > 1 else "ok",
        failure_code=None,
        message="all distinct signed slip roots retained",
        requested_lateral_force_N=requested_lateral_force_N,
        candidates=candidates_tuple,
        branch_selection_applied=branch_selector is not None,
        selected_candidate=selected,
        out_of_domain=False,
    )


def require_r25b_runtime_activation() -> None:
    """Fail explicitly until a reviewed real-source curve exchange is authorized."""

    if not SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED:
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            "real R25B runtime activation remains blocked by AUTH-TIRE-0001",
        )
