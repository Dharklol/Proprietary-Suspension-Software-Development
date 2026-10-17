"""Explicit development-only negative-inclination extension of R25B data.

ASM-VEH-0009 is an owner-accepted engineering symmetry assumption, not measured
negative-IA data. The reviewed source table and its canonical adapter are intact.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
import json

from pssd_tire.r25b_runtime import (
    R25B_CANONICAL_SOURCE_CONVENTION_ID, load_r25b_steady_state_lateral_table,
)
from pssd_tire.r25b_source_native import EXPECTED_SOURCE_TIRE_ID, EXPECTED_INTENDED_TIRE_ID
from pssd_tire.r25b_named_runtime import load_r25b_classified_lateral_table
from pssd_tire.steady_state_lateral import (
    SteadyStateLateralFailure, SteadyStateLateralOperatingState,
    SteadyStateLateralResponse, SteadyStateLateralTable, evaluate_table,
)

SYMMETRY_ASSUMPTION_ID = "ASM-VEH-0009"
SYMMETRY_POLICY = "development_negative_IA_reflect_slip_inclination_and_force"
SYMMETRY_LABEL = "uncorrelated_R25B_to_R20_proxy_with_assumed_negative_IA_symmetry"


@dataclass(frozen=True)
class DevelopmentTireResponse:
    requested_state: SteadyStateLateralOperatingState
    source_response: SteadyStateLateralResponse
    reflected: bool
    assumption_id: str = SYMMETRY_ASSUMPTION_ID
    policy: str = SYMMETRY_POLICY
    fidelity_label: str = SYMMETRY_LABEL

    @property
    def lateral_force_N(self) -> float:
        return (-1 if self.reflected else 1) * self.source_response.lateral_force_N

    @property
    def left_segment_slope_N_per_rad(self) -> float:
        return (self.source_response.right_segment_slope_N_per_rad if self.reflected
                else self.source_response.left_segment_slope_N_per_rad)

    @property
    def right_segment_slope_N_per_rad(self) -> float:
        return (self.source_response.left_segment_slope_N_per_rad if self.reflected
                else self.source_response.right_segment_slope_N_per_rad)


def evaluate_development_r25b(query: SteadyStateLateralOperatingState, *,
                              accepted_assumption_id: str, policy: str,
                              table: SteadyStateLateralTable | None = None) -> DevelopmentTireResponse:
    """For gamma<0 evaluate -Fy(-alpha,Fz,-gamma,P); otherwise source directly.

    No load/pressure/slip/inclination clipping, smoothing or symmetry completion
    of the zero-IA source curve. A source bias at zero IA can leave a discontinuity
    between the reflected and direct limits; callers must retain that boundary.
    Source query, curve IDs, segments, weights and interpolation fractions remain
    available in source_response in their actual lookup coordinates.
    """
    if accepted_assumption_id != SYMMETRY_ASSUMPTION_ID or policy != SYMMETRY_POLICY:
        raise SteadyStateLateralFailure("symmetry_not_authorized", "Explicit ASM-VEH-0009 policy required")
    if query.source_id != EXPECTED_SOURCE_TIRE_ID or query.source_convention_id != R25B_CANONICAL_SOURCE_CONVENTION_ID:
        raise SteadyStateLateralFailure("source_adapter_mismatch", "Reviewed R25B source/convention required")
    reflected = query.inclination_rad < 0
    lookup = (replace(query, slip_angle_rad=-query.slip_angle_rad,
                      inclination_rad=-query.inclination_rad) if reflected else query)
    result = evaluate_table(table or load_r25b_steady_state_lateral_table(), lookup)
    return DevelopmentTireResponse(query, result, reflected)


class R25BDevelopmentCorneringTireProvider:
    """Forward-only coupled-kernel bridge with exact lookup provenance.

    The branch signature is a continuation guard, not a named inverse selector.
    Monotone positive/negative pre-peak and central-transition segments form the
    connected central region; exact original signed labels remain in provenance.
    Indeterminate approaches and post-peak labels remain distinct. Crossing the
    direct/reflected IA boundary is blocked by a changed signature.
    """

    def __init__(self, *, accepted_assumption_id: str, policy: str):
        if accepted_assumption_id != SYMMETRY_ASSUMPTION_ID or policy != SYMMETRY_POLICY:
            raise SteadyStateLateralFailure("symmetry_not_authorized", "Explicit ASM-VEH-0009 policy required")
        self.accepted_assumption_id, self.policy = accepted_assumption_id, policy
        self.table = load_r25b_classified_lateral_table()
        self._curves = {curve.curve_id: curve for curve in self.table.curves}
        self.tire_revision = hashlib.sha256(json.dumps(
            {'table': asdict(self.table), 'assumption': accepted_assumption_id, 'policy': policy},
            sort_keys=True, allow_nan=False).encode()).hexdigest()

    def __call__(self, query):
        from .steady_cornering import CorneringFailure, CorneringTireResponse
        if (query.source_tire_id != EXPECTED_SOURCE_TIRE_ID
                or query.intended_tire_id != EXPECTED_INTENDED_TIRE_ID
                or query.convention_id != R25B_CANONICAL_SOURCE_CONVENTION_ID
                or query.tire_revision != self.tire_revision):
            raise CorneringFailure("tire_source_mismatch", "Bound source/proxy/convention/revision required")
        requested = SteadyStateLateralOperatingState(query.slip_angle_rad, query.normal_load_n,
            query.inclination_rad, query.pressure_pa, query.state_id,
            query.source_tire_id, query.convention_id)
        try:
            result = evaluate_development_r25b(requested, table=self.table,
                accepted_assumption_id=self.accepted_assumption_id, policy=self.policy)
        except SteadyStateLateralFailure as error:
            raise CorneringFailure(error.failure_code, error.message) from error
        original_labels, regions = [], set()
        for segment in result.source_response.slip_segment_ids:
            curve_id, _, index = segment.rpartition(':segment:')
            curve = self._curves[curve_id]
            slot = int(index)
            label = curve.segment_branch_ids[slot]
            slope = (curve.lateral_force_N[slot+1]-curve.lateral_force_N[slot])/(curve.slip_angle_rad[slot+1]-curve.slip_angle_rad[slot])
            original_labels.append((segment, label))
            if label in ('positive_slip_pre_peak', 'negative_slip_pre_peak', 'central_transition') and slope > 0:
                regions.add('connected_monotone_central')
            else:
                regions.add(label)
        boundary = 'reflected_negative_IA' if result.reflected else 'direct_nonnegative_IA'
        branch = boundary+':'+','.join(sorted(regions))
        provenance = (*result.source_response.source_and_adapter_provenance,
            SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY, SYMMETRY_LABEL,
            'requested_query:'+json.dumps(asdict(requested), sort_keys=True),
            'source_response:'+json.dumps(asdict(result.source_response), sort_keys=True),
            'source_segment_labels:'+json.dumps(original_labels))
        return CorneringTireResponse(query, result.lateral_force_N, tuple(provenance), branch)
