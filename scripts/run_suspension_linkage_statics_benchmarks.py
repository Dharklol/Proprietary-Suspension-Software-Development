#!/usr/bin/env python3
"""Generate BENCH-SUSP-0018/0019/0020 linkage-statics diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from pssd_suspension.linkage_statics import (
    IdealTwoForceLink,
    LinkageStaticsFailureCode,
    PrescribedExternalWrench,
    solve_linkage_statics,
)


FRAME = "synthetic_body_frame"
BODY_POINTS = (
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
)
UNIT_AXES = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
)
TARGET_FORCE_N = (100.0, 200.0, 300.0, 40.0, 50.0, 60.0)


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(s: float, a: tuple[float, float, float]) -> tuple[float, float, float]:
    return (s * a[0], s * a[1], s * a[2])


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _links(translation: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[IdealTwoForceLink, ...]:
    rows = []
    for index, (body, axis) in enumerate(zip(BODY_POINTS, UNIT_AXES), start=1):
        body_t = _add(body, translation)
        rows.append(
            IdealTwoForceLink(
                link_id=f"L{index}",
                frame_id=FRAME,
                body_point_m=body_t,
                remote_point_m=_add(_add(body, axis), translation),
                source_id="BENCH-SUSP-0018",
                configuration_id="ANALYTICAL_SIX_LINK_V0",
            )
        )
    return tuple(rows)


def _wrench_for_target(
    links: tuple[IdealTwoForceLink, ...],
    reference: tuple[float, float, float],
) -> PrescribedExternalWrench:
    force = (0.0, 0.0, 0.0)
    moment = (0.0, 0.0, 0.0)
    for link, axial in zip(links, TARGET_FORCE_N):
        direction = _sub(link.remote_point_m, link.body_point_m)
        length = math.sqrt(sum(value * value for value in direction))
        unit = _scale(1.0 / length, direction)
        body_force = _scale(axial, unit)
        force = _add(force, body_force)
        moment = _add(moment, _cross(_sub(link.body_point_m, reference), body_force))
    return PrescribedExternalWrench(
        frame_id=FRAME,
        reference_point_m=reference,
        force_N=_scale(-1.0, force),
        moment_Nm=_scale(-1.0, moment),
        load_case_id="BENCH-SUSP-0018",
        source_id="analytical_fixture",
    )


def analytical_benchmark() -> dict:
    links = _links()
    wrench = _wrench_for_target(links, (0.0, 0.0, 0.0))
    result = solve_linkage_statics(links, wrench)
    force_error = max(abs(actual - target) for actual, target in zip(result.axial_force_N, TARGET_FORCE_N)) if result.ok else math.inf
    passed = (
        result.ok
        and force_error <= 1.0e-9
        and (result.force_residual_inf_norm_N or math.inf) <= 1.0e-9
        and (result.moment_residual_inf_norm_Nm or math.inf) <= 1.0e-9
        and result.condition_number_inf is not None
        and result.condition_number_inf <= 1.0e10
    )
    return {
        "pass": passed,
        "frame_id": FRAME,
        "reference_point_m": list(result.reference_point_m),
        "link_order": list(result.link_order),
        "target_axial_force_N": list(TARGET_FORCE_N),
        "solved_axial_force_N": list(result.axial_force_N),
        "external_force_N": list(wrench.force_N),
        "external_moment_Nm": list(wrench.moment_Nm),
        "maximum_axial_force_error_N": force_error,
        "characteristic_length_m": result.characteristic_length_m,
        "condition_number_inf": result.condition_number_inf,
        "minimum_relative_pivot": result.minimum_relative_pivot,
        "force_residual_inf_norm_N": result.force_residual_inf_norm_N,
        "moment_residual_inf_norm_Nm": result.moment_residual_inf_norm_Nm,
        "positive_force_is_tension": True,
    }


def invariance_benchmark() -> dict:
    origin = (0.0, 0.0, 0.0)
    links = _links()
    wrench = _wrench_for_target(links, origin)
    baseline = solve_linkage_statics(links, wrench)

    reference_2 = (0.31, -0.17, 0.23)
    translated_moment = _add(wrench.moment_Nm, _cross(_sub(origin, reference_2), wrench.force_N))
    reference_result = solve_linkage_statics(
        links,
        PrescribedExternalWrench(
            frame_id=FRAME,
            reference_point_m=reference_2,
            force_N=wrench.force_N,
            moment_Nm=translated_moment,
            load_case_id="BENCH-SUSP-0019-reference",
        ),
    )

    translation = (1.2, -0.8, 0.45)
    translated_result = solve_linkage_statics(
        _links(translation),
        PrescribedExternalWrench(
            frame_id=FRAME,
            reference_point_m=translation,
            force_N=wrench.force_N,
            moment_Nm=wrench.moment_Nm,
            load_case_id="BENCH-SUSP-0019-translation",
        ),
    )
    reference_error = max(abs(a - b) for a, b in zip(reference_result.axial_force_N, baseline.axial_force_N)) if baseline.ok and reference_result.ok else math.inf
    translation_error = max(abs(a - b) for a, b in zip(translated_result.axial_force_N, baseline.axial_force_N)) if baseline.ok and translated_result.ok else math.inf
    passed = (
        baseline.ok
        and reference_result.ok
        and translated_result.ok
        and reference_error <= 1.0e-9
        and translation_error <= 1.0e-9
        and (reference_result.force_residual_inf_norm_N or math.inf) <= 1.0e-9
        and (reference_result.moment_residual_inf_norm_Nm or math.inf) <= 1.0e-9
        and (translated_result.force_residual_inf_norm_N or math.inf) <= 1.0e-9
        and (translated_result.moment_residual_inf_norm_Nm or math.inf) <= 1.0e-9
    )
    return {
        "pass": passed,
        "reference_point_2_m": list(reference_2),
        "reference_point_translated_external_moment_Nm": list(translated_moment),
        "reference_point_max_force_difference_N": reference_error,
        "rigid_translation_m": list(translation),
        "rigid_translation_max_force_difference_N": translation_error,
        "reference_point_condition_number_inf": reference_result.condition_number_inf,
        "translated_geometry_condition_number_inf": translated_result.condition_number_inf,
        "maximum_force_residual_inf_norm_N": max(
            float(reference_result.force_residual_inf_norm_N or 0.0),
            float(translated_result.force_residual_inf_norm_N or 0.0),
        ),
        "maximum_moment_residual_inf_norm_Nm": max(
            float(reference_result.moment_residual_inf_norm_Nm or 0.0),
            float(translated_result.moment_residual_inf_norm_Nm or 0.0),
        ),
    }


def failure_benchmark() -> dict:
    links = list(_links())
    wrench = _wrench_for_target(tuple(links), (0.0, 0.0, 0.0))

    body = links[3].body_point_m
    degenerate = list(links)
    degenerate[3] = IdealTwoForceLink("L4", FRAME, body, body)
    degenerate_result = solve_linkage_statics(tuple(degenerate), wrench)

    five_result = solve_linkage_statics(tuple(links[:5]), wrench)
    seven_result = solve_linkage_statics(tuple(links + [links[0]]), wrench)

    singular = list(links)
    singular[3] = IdealTwoForceLink("L4", FRAME, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    singular_result = solve_linkage_statics(tuple(singular), wrench)

    near = list(links)
    epsilon = 1.0e-10
    near[3] = IdealTwoForceLink("L4", FRAME, (0.0, epsilon, 0.0), (0.0, epsilon, 1.0))
    near_result = solve_linkage_statics(tuple(near), wrench)

    nonfinite_wrench = PrescribedExternalWrench(
        frame_id=FRAME,
        reference_point_m=(0.0, 0.0, 0.0),
        force_N=(math.nan, -260.0, -340.0),
        moment_Nm=(-40.0, -50.0, -60.0),
    )
    nonfinite_result = solve_linkage_statics(tuple(links), nonfinite_wrench)

    expected = {
        "degenerate_link": (degenerate_result, LinkageStaticsFailureCode.DEGENERATE_LINK),
        "five_link": (five_result, LinkageStaticsFailureCode.UNSUPPORTED_TOPOLOGY),
        "seven_link": (seven_result, LinkageStaticsFailureCode.UNSUPPORTED_TOPOLOGY),
        "singular": (singular_result, LinkageStaticsFailureCode.SINGULAR_EQUILIBRIUM),
        "ill_conditioned": (near_result, LinkageStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM),
        "nonfinite": (nonfinite_result, LinkageStaticsFailureCode.NONFINITE_INPUT),
    }
    passed = all((not result.ok) and result.failure_code is code for result, code in expected.values())
    passed = passed and near_result.condition_number_inf is not None and near_result.condition_number_inf > 1.0e10
    return {
        "pass": passed,
        "failure_codes": {
            name: result.failure_code.value if result.failure_code else None
            for name, (result, _code) in expected.items()
        },
        "ill_conditioned_epsilon_m": epsilon,
        "ill_conditioned_condition_number_inf": near_result.condition_number_inf,
        "condition_limit": 1.0e10,
        "five_link_force_vector_available": bool(five_result.link_forces),
        "seven_link_force_vector_available": bool(seven_result.link_forces),
        "singular_force_vector_available": bool(singular_result.link_forces),
        "ill_conditioned_force_vector_available": bool(near_result.link_forces),
    }


def build_report() -> dict:
    b18 = analytical_benchmark()
    b19 = invariance_benchmark()
    b20 = failure_benchmark()
    if not b18["pass"] or not b19["pass"] or not b20["pass"]:
        raise RuntimeError("Suspension linkage-statics benchmark acceptance failed")
    return {
        "model_id": "MOD-SUSP-0006",
        "authorization_id": "AUTH-SUSP-0010",
        "assumption_id": "ASM-SUSP-0004",
        "authority": "provider-neutral ideal six-link rigid-body statics only; no WUFR load-case or structural-release authority",
        "BENCH-SUSP-0018": b18,
        "BENCH-SUSP-0019": b19,
        "BENCH-SUSP-0020": b20,
        "authority_boundary": {
            "wufr_corner_adapter_authorized": False,
            "wufr_load_case_generation_authorized": False,
            "beam_stress_authorized": False,
            "structural_release_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("suspension_linkage_statics_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b18 = report["BENCH-SUSP-0018"]
        b20 = report["BENCH-SUSP-0020"]
        print(
            "MOD-SUSP-0006: "
            f"N={b18['solved_axial_force_N']}, "
            f"cond_inf={b18['condition_number_inf']}, "
            f"failure_gate={b20['pass']}, "
            "WUFR_adapter_authorized=False"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
