#!/usr/bin/env python3
"""Audit the exact R25B Cornering Trojan before any runtime activation.

The audit is intentionally source-native. It verifies channel integrity, enumerates the
stored operating-state lattice, checks each slip sweep, and compares the binary structure
with the frozen description of ``April_Interpolator.m``. It does not repair, resample,
smooth, sign-convert, or authorize tire behavior.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
from math import isclose, isfinite
from pathlib import Path
from typing import Mapping, Sequence

from scripts.verify_r25b_runtime_source import verify_source

REQUIRED_CHANNELS = (
    "ET",
    "FX",
    "FY",
    "FZ",
    "IA",
    "MX",
    "MZ",
    "N",
    "P",
    "SA",
    "SL",
    "V",
)
EXPECTED_FZ_N = (222.0, 445.0, 667.0, 1112.0)
EXPECTED_IA_DEG = (0.0, 2.0, 4.0)
EXPECTED_P_KPA = (68.9, 82.7, 96.5)
EXPECTED_ROWS_PER_STATE = 100
EXPECTED_TOTAL_ROWS = 3600
STATE_TOLERANCE = 1.0e-9
MONOTONIC_FORCE_TOLERANCE_N = 1.0e-6


@dataclass(frozen=True)
class R25bSourceStructureAudit:
    total_rows: int
    state_count: int
    normal_load_values_n: tuple[float, ...]
    inclination_values_deg: tuple[float, ...]
    pressure_values_kpa: tuple[float, ...]
    speed_values_kph: tuple[float, ...]
    slip_ratio_values: tuple[float, ...]
    rows_per_state_histogram: tuple[tuple[int, int], ...]
    all_channels_finite: bool
    all_state_slip_grids_strictly_increasing: bool
    all_state_slip_grids_span_minus12_to_plus12_deg: bool
    frozen_generator_description_matches_binary: bool
    mismatch_reasons: tuple[str, ...]
    prepeak_monotonic_state_count: int
    prepeak_rejected_state_count: int
    prepeak_rejected_states: tuple[str, ...]


def _normalized_channels(
    channels: Mapping[str, Sequence[float]],
) -> tuple[dict[str, tuple[float, ...]], int]:
    missing = [name for name in REQUIRED_CHANNELS if name not in channels]
    if missing:
        raise ValueError(f"missing required channels: {missing}")

    normalized: dict[str, tuple[float, ...]] = {}
    lengths: set[int] = set()
    for name in REQUIRED_CHANNELS:
        values = tuple(float(value) for value in channels[name])
        if not values:
            raise ValueError(f"channel {name} is empty")
        if not all(isfinite(value) for value in values):
            raise ValueError(f"channel {name} contains nonfinite values")
        normalized[name] = values
        lengths.add(len(values))
    if len(lengths) != 1:
        raise ValueError("required channels do not share one row count")
    return normalized, lengths.pop()


def _state_id(state: tuple[float, float, float, float, float]) -> str:
    fz, ia, pressure, speed, slip_ratio = state
    return f"Fz={fz:g}N;IA={ia:g}deg;P={pressure:g}kPa;V={speed:g}kph;SL={slip_ratio:g}"


def _prepeak_is_monotonic(
    rows: tuple[dict[str, float], ...],
    *,
    force_tolerance_n: float = MONOTONIC_FORCE_TOLERANCE_N,
) -> bool:
    quadrant = sorted(
        (
            (abs(row["SA"]), abs(row["FY"]))
            for row in rows
            if row["SA"] <= STATE_TOLERANCE and row["FY"] >= -force_tolerance_n
        ),
        key=lambda item: item[0],
    )
    if len(quadrant) < 2:
        return False
    if any(
        upper[0] <= lower[0] + STATE_TOLERANCE
        for lower, upper in zip(quadrant, quadrant[1:])
    ):
        return False
    peak_index = max(range(len(quadrant)), key=lambda index: quadrant[index][1])
    prepeak = quadrant[: peak_index + 1]
    if len(prepeak) < 2:
        return False
    return all(
        upper[1] > lower[1] + force_tolerance_n
        for lower, upper in zip(prepeak, prepeak[1:])
    )


def audit_channels(channels: Mapping[str, Sequence[float]]) -> R25bSourceStructureAudit:
    rows, total_rows = _normalized_channels(channels)
    grouped: dict[tuple[float, float, float, float, float], list[dict[str, float]]] = defaultdict(list)
    for index in range(total_rows):
        state = (
            rows["FZ"][index],
            rows["IA"][index],
            rows["P"][index],
            rows["V"][index],
            rows["SL"][index],
        )
        grouped[state].append({name: rows[name][index] for name in REQUIRED_CHANNELS})

    fz_values = tuple(sorted({state[0] for state in grouped}))
    ia_values = tuple(sorted({state[1] for state in grouped}))
    pressure_values = tuple(sorted({state[2] for state in grouped}))
    speed_values = tuple(sorted({state[3] for state in grouped}))
    slip_ratio_values = tuple(sorted({state[4] for state in grouped}))
    histogram = tuple(sorted(Counter(len(state_rows) for state_rows in grouped.values()).items()))

    strictly_increasing = True
    complete_span = True
    rejected: list[str] = []
    for state, state_rows_list in sorted(grouped.items()):
        state_rows = tuple(state_rows_list)
        slip = tuple(row["SA"] for row in state_rows)
        if any(right <= left for left, right in zip(slip, slip[1:])):
            strictly_increasing = False
        if not (
            isclose(slip[0], -12.0, rel_tol=0.0, abs_tol=STATE_TOLERANCE)
            and isclose(slip[-1], 12.0, rel_tol=0.0, abs_tol=STATE_TOLERANCE)
        ):
            complete_span = False
        if not _prepeak_is_monotonic(state_rows):
            rejected.append(_state_id(state))

    mismatch_reasons: list[str] = []
    if total_rows != EXPECTED_TOTAL_ROWS:
        mismatch_reasons.append(
            f"binary has {total_rows} rows; frozen generator description implies {EXPECTED_TOTAL_ROWS}"
        )
    if fz_values != EXPECTED_FZ_N:
        mismatch_reasons.append(
            f"binary FZ lattice is {fz_values}; frozen description is {EXPECTED_FZ_N}"
        )
    if ia_values != EXPECTED_IA_DEG:
        mismatch_reasons.append(
            f"binary IA lattice is {ia_values}; frozen description is {EXPECTED_IA_DEG}"
        )
    if pressure_values != EXPECTED_P_KPA:
        mismatch_reasons.append(
            f"binary pressure lattice is {pressure_values}; frozen description is {EXPECTED_P_KPA}"
        )
    if histogram != ((EXPECTED_ROWS_PER_STATE, len(grouped)),):
        mismatch_reasons.append(
            f"binary rows/state histogram is {histogram}; frozen description requires 100 rows/state"
        )

    return R25bSourceStructureAudit(
        total_rows=total_rows,
        state_count=len(grouped),
        normal_load_values_n=fz_values,
        inclination_values_deg=ia_values,
        pressure_values_kpa=pressure_values,
        speed_values_kph=speed_values,
        slip_ratio_values=slip_ratio_values,
        rows_per_state_histogram=histogram,
        all_channels_finite=True,
        all_state_slip_grids_strictly_increasing=strictly_increasing,
        all_state_slip_grids_span_minus12_to_plus12_deg=complete_span,
        frozen_generator_description_matches_binary=not mismatch_reasons,
        mismatch_reasons=tuple(mismatch_reasons),
        prepeak_monotonic_state_count=len(grouped) - len(rejected),
        prepeak_rejected_state_count=len(rejected),
        prepeak_rejected_states=tuple(rejected),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    verify_source(args.source)
    from pssd_tire.io import load_mat_ttc_channels

    channels = load_mat_ttc_channels(args.source, channels=REQUIRED_CHANNELS)
    audit = audit_channels(channels)
    rendered = json.dumps(asdict(audit), indent=2, sort_keys=True) + "\n"
    if args.json_output is not None:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not audit.frozen_generator_description_matches_binary:
        print(
            "R25B activation remains blocked: the exact binary does not match the frozen "
            "generator-structure description.",
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
