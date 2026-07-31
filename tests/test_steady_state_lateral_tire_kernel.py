from __future__ import annotations

import pytest

from pssd_tire.steady_state_lateral import (
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    evaluate_curve,
)


def _curve() -> SteadyStateLateralCurve:
    return SteadyStateLateralCurve(
        curve_id="SYNTHETIC_SIGNED_NONLINEAR_V0",
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        slip_angle_rad=(-0.2, -0.1, 0.0, 0.1, 0.2),
        lateral_force_N=(-700.0, -900.0, 0.0, 1000.0, 800.0),
        source_tire_id="SYNTHETIC_TIRE",
        intended_tire_id="SYNTHETIC_TIRE",
        source_path="tests/fixtures/synthetic_signed_curve",
        source_hash="synthetic",
        source_convention_id="CANONICAL_TIRE_CONTACT_ISO_LEFT_UP",
        adapter_id="IDENTITY_ADAPTER",
        fidelity_label="synthetic_software_verification",
    )


def test_exact_knot_preserves_stored_value_and_reports_one_sided_slopes() -> None:
    response = evaluate_curve(_curve(), 0.1)

    assert response.lateral_force_N == 1000.0
    assert response.exact_knot is True
    assert response.left_segment_slope_N_per_rad == pytest.approx(10_000.0)
    assert response.right_segment_slope_N_per_rad == pytest.approx(-2_000.0)
    assert response.derivative_unique is False
    assert len(response.segment_ids) == 2


def test_open_segment_is_affine_and_has_unique_slope() -> None:
    response = evaluate_curve(_curve(), 0.05)

    assert response.lateral_force_N == pytest.approx(500.0)
    assert response.interpolation_fraction == pytest.approx(0.5)
    assert response.left_segment_slope_N_per_rad == pytest.approx(10_000.0)
    assert response.right_segment_slope_N_per_rad == pytest.approx(10_000.0)
    assert response.derivative_unique is True


def test_out_of_domain_fails_without_clipping() -> None:
    with pytest.raises(SteadyStateLateralFailure) as exc_info:
        evaluate_curve(_curve(), 0.25)

    assert exc_info.value.failure_code == "slip_out_of_domain"


def test_malformed_source_curve_is_rejected() -> None:
    with pytest.raises(SteadyStateLateralFailure) as exc_info:
        SteadyStateLateralCurve(
            curve_id="BAD",
            normal_load_N=1000.0,
            inclination_rad=0.0,
            pressure_Pa=82_737.1,
            slip_angle_rad=(0.0, 0.0),
            lateral_force_N=(0.0, 1.0),
            source_tire_id="SYNTHETIC_TIRE",
            intended_tire_id="SYNTHETIC_TIRE",
            source_path="synthetic",
            source_hash="synthetic",
            source_convention_id="CANONICAL_TIRE_CONTACT_ISO_LEFT_UP",
            adapter_id="IDENTITY_ADAPTER",
            fidelity_label="synthetic_software_verification",
        )

    assert exc_info.value.failure_code == "source_curve_invalid"
