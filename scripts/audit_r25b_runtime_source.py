#!/usr/bin/env python3
"""Audit the processed R25B Trojan against the exact live-script profile.

This command is source bounded. It validates channel structure, contiguous
operating-state sweeps, slip grids, and legacy strict-prepeak diagnostics. It
does not smooth, repair, re-fit, classify full signed branches, or authorize a
canonical/runtime provider.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from math import isfinite
from pathlib import Path
from typing import Iterable, Mapping, Sequence

EXPECTED_CHANNELS = ("ET", "FX", "FY", "FZ", "IA", "MX", "MZ", "N", "P", "SA", "SL", "V")
EXPECTED_FZ_N = (222.0, 445.0, 667.0, 890.0, 1112.0)
EXPECTED_IA_DEG = (0.0, 2.0, 4.0)
EXPECTED_P_KPA = (55.2, 68.9, 82.7, 96.5)
EXPECTED_V_KPH = (40.2,)
EXPECTED_SL = (0.0,)
EXPECTED_STATE_COUNT = 60
EXPECTED_TOTAL_ROWS = 9630
EXPECTED_ROWS_PER_STATE_HISTOGRAM = ((100, 2), (130, 13), (160, 27), (190, 18))
SOURCE_TIRE_ID = "HOOSIER_43105_18X7.5-10_R25B"
INTENDED_TIRE_ID = "HOOSIER_43104_18X7.5-10_R20"


@dataclass(frozen=True)
class R25bRuntimeSourceAudit:
    total_rows: int
    state_count: int
    normal_load_values_n: tuple[float, ...]
    inclination_values_deg: tuple[float, ...]
    pressure_values_kpa: tuple[float, ...]
    speed_values_kph: tuple[float, ...]
    slip_ratio_values: tuple[float, ...]
    rows_per_state_histogram: tuple[tuple[int, int], ...]
    all_required_channels_finite: bool
    all_state_slip_grids_strictly_increasing: bool
    all_state_slip_grids_span_minus12_to_plus12_deg: bool
    exact_generator_profile_matches_binary: bool
    historical_april_profile_matches_binary: bool
    mismatch_reasons: tuple[str, ...]
    prepeak_monotonic_state_count: int
    prepeak_rejected_state_count: int
    prepeak_rejected_states: tuple[str, ...]


def _unique(values: Sequence[float]) -> tuple[float, ...]:
    return tuple(sorted(set(float(value) for value in values)))


def _state_label(fz: float, ia: float, pressure: float) -> str:
    return f"Fz={fz:g}N;IA={ia:g}deg;P={pressure:g}kPa"


def _contiguous_states(
    fz: Sequence[float], ia: Sequence[float], pressure: Sequence[float]
) -> tuple[tuple[int, int, tuple[float, float, float]], ...]:
    keys = tuple((float(f), float(i), float(p)) for f, i, p in zip(fz, ia, pressure))
    states: list[tuple[int, int, tuple[float, float, float]]] = []
    start = 0
    for index in range(1, len(keys) + 1):
        if index == len(keys) or keys[index] != keys[start]:
            states.append((start, index, keys[start]))
            start = index
    return tuple(states)


def _strict_prepeak_pass(sa: Sequence[float], fy: Sequence[float]) -> bool:
    selected = [
        (abs(float(slip)), float(force))
        for slip, force in zip(sa, fy)
        if float(slip) < 0.0 and float(force) > 0.0
    ]
    if len(selected) < 2:
        return False
    selected.sort(key=lambda item: item[0])
    forces = [force for _, force in selected]
    peak_index = max(range(len(forces)), key=forces.__getitem__)
    prepeak = forces[: peak_index + 1]
    return len(prepeak) >= 2 and all(right > left for left, right in zip(prepeak, prepeak[1:]))


def audit_channels(channels: Mapping[str, Sequence[float]]) -> R25bRuntimeSourceAudit:
    missing = [name for name in EXPECTED_CHANNELS if name not in channels]
    if missing:
        raise ValueError(f"source is missing required channels: {', '.join(missing)}")
    lengths = {len(channels[name]) for name in EXPECTED_CHANNELS}
    if len(lengths) != 1:
        raise ValueError("required source channels do not share one row count")
    total_rows = lengths.pop()
    if total_rows == 0:
        raise ValueError("source contains no rows")

    all_finite = all(
        isfinite(float(value))
        for name in EXPECTED_CHANNELS
        for value in channels[name]
    )
    if not all_finite:
        raise ValueError("source contains nonfinite required-channel values")

    fz_values = _unique(channels["FZ"])
    ia_values = _unique(channels["IA"])
    pressure_values = _unique(channels["P"])
    speed_values = _unique(channels["V"])
    slip_ratio_values = _unique(channels["SL"])
    states = _contiguous_states(channels["FZ"], channels["IA"], channels["P"])
    histogram = tuple(sorted(Counter(end - start for start, end, _ in states).items()))

    all_increasing = True
    all_span = True
    rejected: list[str] = []
    for start, end, (fz, ia, pressure) in states:
        slip = tuple(float(value) for value in channels["SA"][start:end])
        force = tuple(float(value) for value in channels["FY"][start:end])
        if any(right <= left for left, right in zip(slip, slip[1:])):
            all_increasing = False
        if not slip or abs(slip[0] + 12.0) > 1.0e-12 or abs(slip[-1] - 12.0) > 1.0e-12:
            all_span = False
        if not _strict_prepeak_pass(slip, force):
            rejected.append(_state_label(fz, ia, pressure))

    mismatch: list[str] = []
    checks = (
        (total_rows == EXPECTED_TOTAL_ROWS, f"row count is {total_rows}, expected {EXPECTED_TOTAL_ROWS}"),
        (len(states) == EXPECTED_STATE_COUNT, f"state count is {len(states)}, expected {EXPECTED_STATE_COUNT}"),
        (fz_values == EXPECTED_FZ_N, f"FZ lattice is {fz_values}, expected {EXPECTED_FZ_N}"),
        (ia_values == EXPECTED_IA_DEG, f"IA lattice is {ia_values}, expected {EXPECTED_IA_DEG}"),
        (
            pressure_values == EXPECTED_P_KPA,
            f"pressure lattice is {pressure_values}, expected {EXPECTED_P_KPA}",
        ),
        (speed_values == EXPECTED_V_KPH, f"speed lattice is {speed_values}, expected {EXPECTED_V_KPH}"),
        (
            slip_ratio_values == EXPECTED_SL,
            f"slip-ratio lattice is {slip_ratio_values}, expected {EXPECTED_SL}",
        ),
        (
            histogram == EXPECTED_ROWS_PER_STATE_HISTOGRAM,
            f"rows/state histogram is {histogram}, expected {EXPECTED_ROWS_PER_STATE_HISTOGRAM}",
        ),
        (all_increasing, "at least one state slip grid is not strictly increasing"),
        (all_span, "at least one state does not span exactly -12 to +12 degrees"),
    )
    mismatch.extend(message for passed, message in checks if not passed)

    exact_match = not mismatch
    return R25bRuntimeSourceAudit(
        total_rows=total_rows,
        state_count=len(states),
        normal_load_values_n=fz_values,
        inclination_values_deg=ia_values,
        pressure_values_kpa=pressure_values,
        speed_values_kph=speed_values,
        slip_ratio_values=slip_ratio_values,
        rows_per_state_histogram=histogram,
        all_required_channels_finite=all_finite,
        all_state_slip_grids_strictly_increasing=all_increasing,
        all_state_slip_grids_span_minus12_to_plus12_deg=all_span,
        exact_generator_profile_matches_binary=exact_match,
        historical_april_profile_matches_binary=(
            total_rows == 3600
            and len(states) == 36
            and fz_values == (222.0, 445.0, 667.0, 1112.0)
            and pressure_values == (68.9, 82.7, 96.5)
            and histogram == ((100, 36),)
        ),
        mismatch_reasons=tuple(mismatch),
        prepeak_monotonic_state_count=len(states) - len(rejected),
        prepeak_rejected_state_count=len(rejected),
        prepeak_rejected_states=tuple(rejected),
    )


def load_mat_channels(path: Path) -> dict[str, tuple[float, ...]]:
    try:
        import numpy
        from scipy.io import loadmat
    except ImportError as exc:
        raise SystemExit("NumPy and SciPy are required to audit the binary MAT source") from exc
    source = loadmat(path, squeeze_me=True)
    result: dict[str, tuple[float, ...]] = {}
    for name in EXPECTED_CHANNELS:
        if name not in source:
            raise SystemExit(f"MAT source is missing required channel {name}")
        values = numpy.asarray(source[name], dtype=float).reshape(-1)
        result[name] = tuple(float(value) for value in values)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    audit = audit_channels(load_mat_channels(args.source))
    rendered = json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n"
    if args.json_output is not None:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not audit.exact_generator_profile_matches_binary:
        print("Processed R25B binary does not match the exact TTC Spline Fitter profile.")
        return 3
    print("Processed R25B binary matches the exact 9,630-row TTC Spline Fitter profile.")
    print("Canonical adapter review and source-specific runtime authorization remain separate gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
