"""Deterministic synthetic benchmarks for MOD-TIRE-0001."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from .steady_state_lateral import (
    SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED,
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    SteadyStateLateralOperatingState,
    SteadyStateLateralTable,
    evaluate_curve,
    evaluate_table,
    invert_lateral_force,
    require_r25b_runtime_activation,
)

CANONICAL_CONVENTION = "CANONICAL_TIRE_CONTACT_ISO_LEFT_UP"
SYNTHETIC_SOURCE = "SYNTHETIC_TIRE"
SYNTHETIC_FIDELITY = "synthetic_software_verification"


def signed_nonlinear_curve() -> SteadyStateLateralCurve:
    return SteadyStateLateralCurve(
        curve_id="SYNTHETIC_SIGNED_NONLINEAR_V0",
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        slip_angle_rad=(-0.2, -0.1, 0.0, 0.1, 0.2),
        lateral_force_N=(-700.0, -900.0, 0.0, 1000.0, 800.0),
        source_tire_id=SYNTHETIC_SOURCE,
        intended_tire_id=SYNTHETIC_SOURCE,
        source_path="synthetic://BENCH-TIRE-0001/signed_nonlinear",
        source_hash="sha256:synthetic-bench-tire-0001",
        source_convention_id=CANONICAL_CONVENTION,
        adapter_id="IDENTITY_ADAPTER",
        fidelity_label=SYNTHETIC_FIDELITY,
        domain_and_censor_metadata=("complete_signed_domain", "not_censored"),
        source_preprocessing=("none",),
        segment_branch_ids=("negative_post_peak", "negative_pre_peak", "pre_peak", "post_peak"),
    )


def _affine_force(alpha: float, load: float, inclination: float, pressure: float) -> float:
    return 5000.0 * alpha + 0.2 * load + 1000.0 * inclination + 0.001 * pressure - 500.0


def affine_state_cell() -> SteadyStateLateralTable:
    curves: list[SteadyStateLateralCurve] = []
    for load_index, load in enumerate((1000.0, 2000.0)):
        for inclination_index, inclination in enumerate((0.0, 0.02)):
            for pressure_index, pressure in enumerate((80_000.0, 100_000.0)):
                parity = (load_index + inclination_index + pressure_index) % 2
                slips = (-0.2, -0.05, 0.2) if parity == 0 else (-0.2, 0.07, 0.2)
                curve_id = f"AFFINE_L{load_index}_G{inclination_index}_P{pressure_index}"
                curves.append(
                    SteadyStateLateralCurve(
                        curve_id=curve_id,
                        normal_load_N=load,
                        inclination_rad=inclination,
                        pressure_Pa=pressure,
                        slip_angle_rad=slips,
                        lateral_force_N=tuple(
                            _affine_force(alpha, load, inclination, pressure)
                            for alpha in slips
                        ),
                        source_tire_id=SYNTHETIC_SOURCE,
                        intended_tire_id=SYNTHETIC_SOURCE,
                        source_path=f"synthetic://BENCH-TIRE-0002/{curve_id}",
                        source_hash=f"sha256:synthetic-{curve_id.lower()}",
                        source_convention_id=CANONICAL_CONVENTION,
                        adapter_id="IDENTITY_ADAPTER",
                        fidelity_label=SYNTHETIC_FIDELITY,
                        domain_and_censor_metadata=("common_supported_interval:-0.2:0.2",),
                        source_preprocessing=("none",),
                        segment_branch_ids=("unclassified", "unclassified"),
                    )
                )
    return SteadyStateLateralTable(table_id="SYNTHETIC_AFFINE_2X2X2", curves=tuple(curves))


def peak_post_peak_table() -> SteadyStateLateralTable:
    curve = SteadyStateLateralCurve(
        curve_id="SYNTHETIC_SIGNED_PEAK_POSTPEAK_V0",
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        slip_angle_rad=(-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3),
        lateral_force_N=(-500.0, -1000.0, -600.0, 0.0, 600.0, 1000.0, 500.0),
        source_tire_id=SYNTHETIC_SOURCE,
        intended_tire_id=SYNTHETIC_SOURCE,
        source_path="synthetic://BENCH-TIRE-0003/peak_postpeak",
        source_hash="sha256:synthetic-bench-tire-0003",
        source_convention_id=CANONICAL_CONVENTION,
        adapter_id="IDENTITY_ADAPTER",
        fidelity_label=SYNTHETIC_FIDELITY,
        domain_and_censor_metadata=("complete_signed_domain", "pre_and_post_peak"),
        source_preprocessing=("none",),
        segment_branch_ids=(
            "negative_post_peak",
            "negative_pre_peak",
            "negative_pre_peak",
            "pre_peak",
            "pre_peak",
            "post_peak",
        ),
    )
    return SteadyStateLateralTable(table_id="SYNTHETIC_PEAK_POSTPEAK", curves=(curve,))


def _failure_code(callable_object: Any) -> str:
    try:
        callable_object()
    except SteadyStateLateralFailure as exc:
        return exc.failure_code
    raise AssertionError("benchmark expected a structured failure")


def build_benchmark_result() -> dict[str, Any]:
    curve = signed_nonlinear_curve()
    exact = evaluate_curve(curve, 0.1)
    interior = evaluate_curve(curve, 0.05)

    cell = affine_state_cell()
    query = SteadyStateLateralOperatingState(
        slip_angle_rad=0.03,
        normal_load_N=1500.0,
        inclination_rad=0.01,
        pressure_Pa=90_000.0,
        state_id="BENCH-TIRE-0002:interior",
        source_id=SYNTHETIC_SOURCE,
        source_convention_id=CANONICAL_CONVENTION,
    )
    interpolated = evaluate_table(cell, query)
    expected_force = _affine_force(
        query.slip_angle_rad,
        query.normal_load_N,
        query.inclination_rad,
        query.pressure_Pa,
    )

    peak_table = peak_post_peak_table()
    inverse_all = invert_lateral_force(
        peak_table,
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        requested_lateral_force_N=700.0,
        source_id=SYNTHETIC_SOURCE,
        source_convention_id=CANONICAL_CONVENTION,
    )
    inverse_pre = invert_lateral_force(
        peak_table,
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        requested_lateral_force_N=700.0,
        source_id=SYNTHETIC_SOURCE,
        source_convention_id=CANONICAL_CONVENTION,
        branch_selector="named_pre_peak_branch",
    )
    inverse_post = invert_lateral_force(
        peak_table,
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        requested_lateral_force_N=700.0,
        source_id=SYNTHETIC_SOURCE,
        source_convention_id=CANONICAL_CONVENTION,
        branch_selector="named_post_peak_branch",
    )
    shared_peak = invert_lateral_force(
        peak_table,
        normal_load_N=1000.0,
        inclination_rad=0.0,
        pressure_Pa=82_737.1,
        requested_lateral_force_N=1000.0,
        source_id=SYNTHETIC_SOURCE,
        source_convention_id=CANONICAL_CONVENTION,
    )

    missing_cell = SteadyStateLateralTable(
        table_id="MISSING_CORNER",
        curves=cell.curves[:-1],
    )
    identity_mismatch_curves = list(cell.curves)
    identity_mismatch_curves[-1] = replace(
        identity_mismatch_curves[-1], intended_tire_id="OTHER_SYNTHETIC_TIRE"
    )
    identity_mismatch = SteadyStateLateralTable(
        table_id="IDENTITY_MISMATCH", curves=tuple(identity_mismatch_curves)
    )
    horizontal = SteadyStateLateralTable(
        table_id="HORIZONTAL_INTERVAL",
        curves=(
            replace(
                curve,
                curve_id="HORIZONTAL",
                slip_angle_rad=(0.0, 0.1, 0.2, 0.3),
                lateral_force_N=(0.0, 100.0, 100.0, 0.0),
                segment_branch_ids=("pre_peak", "plateau", "post_peak"),
            ),
        ),
    )

    failure_codes = {
        "malformed_source": _failure_code(
            lambda: replace(
                curve,
                curve_id="BAD",
                slip_angle_rad=(0.0, 0.0),
                lateral_force_N=(0.0, 1.0),
            )
        ),
        "slip_out_of_domain": _failure_code(lambda: evaluate_curve(curve, 0.25)),
        "missing_cell": _failure_code(lambda: evaluate_table(missing_cell, query)),
        "identity_mismatch": _failure_code(lambda: evaluate_table(identity_mismatch, query)),
        "force_out_of_domain": _failure_code(
            lambda: invert_lateral_force(
                peak_table,
                normal_load_N=1000.0,
                inclination_rad=0.0,
                pressure_Pa=82_737.1,
                requested_lateral_force_N=1200.0,
                source_id=SYNTHETIC_SOURCE,
                source_convention_id=CANONICAL_CONVENTION,
            )
        ),
        "horizontal_interval": _failure_code(
            lambda: invert_lateral_force(
                horizontal,
                normal_load_N=1000.0,
                inclination_rad=0.0,
                pressure_Pa=82_737.1,
                requested_lateral_force_N=100.0,
                source_id=SYNTHETIC_SOURCE,
                source_convention_id=CANONICAL_CONVENTION,
            )
        ),
        "r25b_activation": _failure_code(require_r25b_runtime_activation),
    }

    expected_roots = (0.125, 0.26)
    actual_roots = tuple(candidate.slip_angle_rad for candidate in inverse_all.candidates)
    return {
        "record_id": "STEADY_STATE_LATERAL_TIRE_RESULT_V0.1.0",
        "authorization_id": "AUTH-TIRE-0001",
        "model_id": "MOD-TIRE-0001",
        "canonical_convention_id": CANONICAL_CONVENTION,
        "source_fixture_hashes": {
            "BENCH-TIRE-0001": curve.source_hash,
            "BENCH-TIRE-0002": "sha256:synthetic-affine-2x2x2-v0",
            "BENCH-TIRE-0003": peak_table.curves[0].source_hash,
        },
        "benchmarks": {
            "BENCH-TIRE-0001": {
                "exact_force_N": exact.lateral_force_N,
                "exact_left_slope_N_per_rad": exact.left_segment_slope_N_per_rad,
                "exact_right_slope_N_per_rad": exact.right_segment_slope_N_per_rad,
                "exact_derivative_unique": exact.derivative_unique,
                "interior_force_N": interior.lateral_force_N,
                "interior_fraction": interior.interpolation_fraction,
                "interior_slope_N_per_rad": interior.left_segment_slope_N_per_rad,
                "maximum_force_error_N": max(
                    abs(exact.lateral_force_N - 1000.0),
                    abs(interior.lateral_force_N - 500.0),
                ),
                "maximum_slope_error_N_per_rad": max(
                    abs(exact.left_segment_slope_N_per_rad - 10_000.0),
                    abs(exact.right_segment_slope_N_per_rad + 2000.0),
                    abs(interior.left_segment_slope_N_per_rad - 10_000.0),
                ),
            },
            "BENCH-TIRE-0002": {
                "interpolated_force_N": interpolated.lateral_force_N,
                "expected_force_N": expected_force,
                "interpolated_slope_N_per_rad": interpolated.left_segment_slope_N_per_rad,
                "curve_count": len(interpolated.participating_curve_ids),
                "weights": [weight for _, weight in interpolated.state_interpolation_weights],
                "maximum_force_error_N": abs(interpolated.lateral_force_N - expected_force),
                "maximum_slope_error_N_per_rad": abs(
                    interpolated.left_segment_slope_N_per_rad - 5000.0
                ),
                "maximum_weight_error": max(
                    abs(weight - 0.125)
                    for _, weight in interpolated.state_interpolation_weights
                ),
            },
            "BENCH-TIRE-0003": {
                "requested_force_N": 700.0,
                "all_roots_rad": list(actual_roots),
                "pre_peak_selected_rad": (
                    inverse_pre.selected_candidate.slip_angle_rad
                    if inverse_pre.selected_candidate
                    else None
                ),
                "post_peak_selected_rad": (
                    inverse_post.selected_candidate.slip_angle_rad
                    if inverse_post.selected_candidate
                    else None
                ),
                "shared_peak_root_count": len(shared_peak.candidates),
                "shared_peak_branches": list(shared_peak.candidates[0].contributing_branch_ids),
                "maximum_root_error_rad": max(
                    abs(actual - expected)
                    for actual, expected in zip(actual_roots, expected_roots)
                ),
            },
        },
        "failure_code_coverage": failure_codes,
        "fidelity": {
            "synthetic_software_verification_only": True,
            "source_specific_r25b_runtime_activation_authorized": (
                SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED
            ),
            "real_hoosier_curve_exchange_frozen": False,
            "magic_formula_or_fitted_reconstruction_used": False,
            "slip_or_state_extrapolation_used": False,
            "hidden_symmetry_used": False,
        },
    }


def format_benchmark_result_json(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: list[Any]) -> str:
    rendered: list[str] = []
    for value in values:
        if isinstance(value, str):
            rendered.append(_toml_string(value))
        elif isinstance(value, bool):
            rendered.append("true" if value else "false")
        elif value is None:
            rendered.append(_toml_string("unavailable"))
        else:
            rendered.append(repr(value))
    return "[" + ", ".join(rendered) + "]"


def format_benchmark_result_toml(result: dict[str, Any]) -> str:
    lines = [
        f"record_id = {_toml_string(result['record_id'])}",
        f"authorization_id = {_toml_string(result['authorization_id'])}",
        f"model_id = {_toml_string(result['model_id'])}",
        f"canonical_convention_id = {_toml_string(result['canonical_convention_id'])}",
        "",
        "[source_fixture_hashes]",
    ]
    for key, value in result["source_fixture_hashes"].items():
        lines.append(f"{_toml_string(key)} = {_toml_string(value)}")
    for benchmark_id, benchmark in result["benchmarks"].items():
        lines.extend(("", f"[benchmarks.{_toml_string(benchmark_id)}]"))
        for key, value in benchmark.items():
            if isinstance(value, list):
                lines.append(f"{key} = {_toml_array(value)}")
            elif isinstance(value, bool):
                lines.append(f"{key} = {'true' if value else 'false'}")
            elif value is None:
                lines.append(f"{key} = {_toml_string('unavailable')}")
            else:
                lines.append(f"{key} = {repr(value)}")
    lines.extend(("", "[failure_code_coverage]"))
    for key, value in result["failure_code_coverage"].items():
        lines.append(f"{key} = {_toml_string(value)}")
    lines.extend(("", "[fidelity]"))
    for key, value in result["fidelity"].items():
        lines.append(f"{key} = {'true' if value else 'false'}")
    return "\n".join(lines) + "\n"


def write_benchmark_results(repository_root: Path) -> tuple[Path, Path]:
    result = build_benchmark_result()
    output_dir = repository_root / "benchmarks" / "tires"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "steady_state_lateral_tire_result_v0.1.0.json"
    toml_path = output_dir / "steady_state_lateral_tire_result_v0.1.0.toml"
    json_path.write_text(format_benchmark_result_json(result), encoding="utf-8")
    toml_path.write_text(format_benchmark_result_toml(result), encoding="utf-8")
    return json_path, toml_path
