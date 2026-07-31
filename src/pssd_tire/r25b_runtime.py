"""Reviewed source-specific runtime adapter for the frozen R25B exchange.

The source-native exchange remains immutable and explicitly noncanonical. This
module applies AUTH-TIRE-0002 as a separate adapter layer. The TTC P channel is
interpreted as gauge pressure by reviewer decision; that basis is not presented
as a source-stated TTC or Calspan fact.
"""

from __future__ import annotations

from math import radians
from pathlib import Path
import tomllib
from typing import Final

from .r25b_source_native import (
    EXPECTED_EXCHANGE_ID,
    EXPECTED_GENERATOR_SHA1,
    EXPECTED_INTENDED_TIRE_ID,
    EXPECTED_SOURCE_SHA1,
    EXPECTED_SOURCE_TIRE_ID,
    R25bSourceNativeExchange,
    load_r25b_source_native_exchange,
)
from .steady_state_lateral import (
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    SteadyStateLateralOperatingState,
    SteadyStateLateralResponse,
    SteadyStateLateralTable,
    evaluate_table,
    invert_lateral_force,
)

SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED: Final[bool] = True
R25B_RUNTIME_AUTHORIZATION_ID: Final[str] = "AUTH-TIRE-0002"
R25B_RUNTIME_ADAPTER_ID: Final[str] = (
    "ADAPTER-TIRE-R25B-SAE-J670-TO-CANONICAL-GAUGE-V1"
)
R25B_CANONICAL_SOURCE_CONVENTION_ID: Final[str] = (
    "SAE_J670_TTC_R6_TO_CANONICAL_TIRE_CONTACT_ISO_LEFT_UP_GAUGE_V1"
)
R25B_RUNTIME_TABLE_ID: Final[str] = "R25B_CANONICAL_COMPLETE_SIGNED_RUNTIME_V1"
R25B_PRESSURE_BASIS: Final[str] = "gauge"
R25B_FIDELITY_LABEL: Final[str] = (
    "exact_processed_ttc_r25b_engineering_proxy_for_r20"
)
_EXPECTED_PAYLOAD_SHA256: Final[str] = (
    "3084bce3d519e088a3e3aa32f30ec8d45cf4f365e5d33028b8da45ca3f2fc438"
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_R25B_SOURCE_NATIVE_MANIFEST: Final[Path] = _REPOSITORY_ROOT / (
    "benchmarks/tires/"
    "WUFR26_H43105_R25B_COMPLETE_SIGNED_SOURCE_NATIVE_V0/manifest.toml"
)
DEFAULT_R25B_RUNTIME_AUTHORIZATION: Final[Path] = (
    _REPOSITORY_ROOT / "authorizations/tire/AUTH-TIRE-0002.toml"
)


def _load_authorization(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            f"R25B runtime authorization is unavailable: {path}",
        )
    with path.open("rb") as stream:
        record = tomllib.load(stream)
    required_top_level = {
        "authorization_id": R25B_RUNTIME_AUTHORIZATION_ID,
        "status": "reviewed",
        "implementation_authorized": True,
    }
    for key, expected in required_top_level.items():
        if record.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_specific_activation_blocked",
                f"R25B authorization field {key!r} does not match the reviewed value",
            )
    scope = record.get("scope")
    decision = record.get("review_decision")
    identity = record.get("source_identity")
    adapter = record.get("canonical_adapter")
    if not all(isinstance(value, dict) for value in (scope, decision, identity, adapter)):
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            "R25B authorization is structurally incomplete",
        )
    assert isinstance(scope, dict)
    assert isinstance(decision, dict)
    assert isinstance(identity, dict)
    assert isinstance(adapter, dict)
    if scope.get("source_specific_r25b_runtime_activation_authorized") is not True:
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            "R25B source-specific runtime activation is not authorized",
        )
    if decision.get("pressure_basis") != R25B_PRESSURE_BASIS:
        raise SteadyStateLateralFailure(
            "source_adapter_mismatch", "reviewed R25B pressure basis is not gauge"
        )
    if decision.get("pressure_basis_source_type") != (
        "reviewer_authorized_engineering_interpretation"
    ):
        raise SteadyStateLateralFailure(
            "source_adapter_mismatch",
            "R25B gauge basis is not marked as an engineering interpretation",
        )
    if decision.get("pressure_basis_is_source_stated_fact") is not False:
        raise SteadyStateLateralFailure(
            "source_adapter_mismatch",
            "R25B authorization incorrectly promotes the pressure basis to source fact",
        )
    expected_identity = {
        "source_tire_id": EXPECTED_SOURCE_TIRE_ID,
        "intended_tire_id": EXPECTED_INTENDED_TIRE_ID,
        "source_binary_sha1": EXPECTED_SOURCE_SHA1,
        "generator_sha1": EXPECTED_GENERATOR_SHA1,
        "source_exchange_id": EXPECTED_EXCHANGE_ID,
        "source_exchange_payload_sha256": _EXPECTED_PAYLOAD_SHA256,
        "curve_count": 60,
        "sample_count": 9630,
    }
    for key, expected in expected_identity.items():
        if identity.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_identity_mismatch",
                f"R25B authorization identity field {key!r} does not match",
            )
    expected_adapter = {
        "adapter_id": R25B_RUNTIME_ADAPTER_ID,
        "canonical_convention_id": "CANONICAL_TIRE_CONTACT_ISO_LEFT_UP",
        "pressure_basis": R25B_PRESSURE_BASIS,
        "slip_angle_rule": "alpha_rad = deg_to_rad(source_SA_deg)",
        "lateral_force_rule": "Fy_canonical_N = -source_FY_N",
        "inclination_rule": "inclination_rad = deg_to_rad(source_IA_deg)",
        "pressure_rule": "pressure_Pa = 1000 * source_P_kPa",
    }
    for key, expected in expected_adapter.items():
        if adapter.get(key) != expected:
            raise SteadyStateLateralFailure(
                "source_adapter_mismatch",
                f"R25B adapter field {key!r} does not match the reviewed transform",
            )
    return record


def require_r25b_runtime_activation(
    authorization_path: Path = DEFAULT_R25B_RUNTIME_AUTHORIZATION,
) -> None:
    """Validate the reviewed source-specific authorization and return normally."""

    if not SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED:
        raise SteadyStateLateralFailure(
            "source_specific_activation_blocked",
            "R25B runtime activation constant is disabled",
        )
    _load_authorization(authorization_path)


def _adapt_curve(
    exchange: R25bSourceNativeExchange,
    source_curve,
) -> SteadyStateLateralCurve:
    if abs(source_curve.slip_ratio) > 1.0e-12:
        raise SteadyStateLateralFailure(
            "source_curve_invalid", "R25B source curve is not pure lateral"
        )
    canonical_slip = tuple(radians(value) for value in source_curve.source_slip_angle_deg)
    canonical_force = tuple(-value for value in source_curve.source_lateral_force_n)
    return SteadyStateLateralCurve(
        curve_id=f"{source_curve.curve_id}:CANONICAL_GAUGE_V1",
        normal_load_N=source_curve.normal_load_n,
        inclination_rad=radians(source_curve.inclination_deg),
        pressure_Pa=1000.0 * source_curve.pressure_kpa,
        slip_angle_rad=canonical_slip,
        lateral_force_N=canonical_force,
        source_tire_id=exchange.source_tire_id,
        intended_tire_id=exchange.intended_tire_id,
        source_path=exchange.manifest_path,
        source_hash=(
            f"source_sha1:{exchange.source_binary_sha1};"
            f"payload_sha256:{exchange.payload_sha256}"
        ),
        source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        adapter_id=R25B_RUNTIME_ADAPTER_ID,
        fidelity_label=R25B_FIDELITY_LABEL,
        domain_and_censor_metadata=(
            "source_slip_domain_deg=[-12,12]",
            f"source_speed_kph={source_curve.speed_kph:.1f}",
            "source_slip_ratio=0",
            "pressure_basis=gauge_reviewer_authorized_engineering_interpretation",
            "pressure_basis_is_not_source_stated_fact",
            "source_tire=Hoosier_43105_R25B",
            "intended_tire=Hoosier_43104_R20_engineering_proxy",
            "source_peak_postpeak_and_nonmonotonicity_retained",
            "named_branch_selection_not_authorized",
        ),
        source_preprocessing=(
            "exact_hashed_processed_trojan_samples",
            "source_MATLAB_smoothingspline_p=0.5",
            "no_runtime_smoothing_refit_repair_symmetry_or_track_scale",
        ),
        source_branch_role="complete_signed_unclassified_source_curve",
        segment_branch_ids=(),
    )


def _small_slip_slope(curve: SteadyStateLateralCurve) -> float:
    for left_index, (left, right) in enumerate(
        zip(curve.slip_angle_rad, curve.slip_angle_rad[1:])
    ):
        if left <= 0.0 <= right:
            return (
                curve.lateral_force_N[left_index + 1]
                - curve.lateral_force_N[left_index]
            ) / (right - left)
    raise SteadyStateLateralFailure(
        "source_curve_invalid", "R25B curve does not contain zero slip"
    )


def load_r25b_steady_state_lateral_table(
    manifest_path: Path = DEFAULT_R25B_SOURCE_NATIVE_MANIFEST,
    authorization_path: Path = DEFAULT_R25B_RUNTIME_AUTHORIZATION,
) -> SteadyStateLateralTable:
    """Load the exact exchange and apply the reviewed canonical adapter."""

    require_r25b_runtime_activation(authorization_path)
    exchange = load_r25b_source_native_exchange(manifest_path)
    if exchange.payload_sha256 != _EXPECTED_PAYLOAD_SHA256:
        raise SteadyStateLateralFailure(
            "source_identity_mismatch", "R25B exchange payload identity mismatch"
        )
    curves = tuple(_adapt_curve(exchange, curve) for curve in exchange.curves)
    if len(curves) != 60 or sum(len(curve.slip_angle_rad) for curve in curves) != 9630:
        raise SteadyStateLateralFailure(
            "source_curve_invalid", "R25B canonical exchange coverage is incomplete"
        )
    if any(_small_slip_slope(curve) <= 0.0 for curve in curves):
        raise SteadyStateLateralFailure(
            "source_adapter_mismatch",
            "reviewed R25B adapter does not produce positive local canonical slope",
        )
    return SteadyStateLateralTable(table_id=R25B_RUNTIME_TABLE_ID, curves=curves)


def evaluate_r25b_steady_state_lateral(
    operating_state: SteadyStateLateralOperatingState,
    *,
    table: SteadyStateLateralTable | None = None,
) -> SteadyStateLateralResponse:
    """Evaluate the reviewed R25B canonical table without extrapolation."""

    selected_table = table or load_r25b_steady_state_lateral_table()
    return evaluate_table(selected_table, operating_state)


def invert_r25b_lateral_force(
    *,
    normal_load_N: float,
    inclination_rad: float,
    pressure_Pa: float,
    requested_lateral_force_N: float,
    state_id: str = "r25b_inverse_query",
    table: SteadyStateLateralTable | None = None,
):
    """Return every R25B signed-slip root; named branch selection is not exposed."""

    selected_table = table or load_r25b_steady_state_lateral_table()
    return invert_lateral_force(
        selected_table,
        normal_load_N=normal_load_N,
        inclination_rad=inclination_rad,
        pressure_Pa=pressure_Pa,
        requested_lateral_force_N=requested_lateral_force_N,
        source_id=EXPECTED_SOURCE_TIRE_ID,
        source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        state_id=state_id,
        branch_selector=None,
    )
