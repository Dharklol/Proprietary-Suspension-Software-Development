#!/usr/bin/env python3
"""Independently reproduce the processed R25B Trojan from Round 6 run files.

This is an offline provenance oracle, not a runtime provider. It follows the
exact selection, normalization, target-load scaling, operating-state order,
point-count rule, and slip grids extracted from TTC_Spline_Fitter.mlx. SciPy's
smoothing spline is used as an independent numerical implementation of the
MATLAB p=0.5 smoothing-spline objective. The command reports differences
against the frozen processed Trojan and never overwrites source files.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

EXPECTED = {
    "generator": (
        "TTC_Spline_Fitter.mlx",
        286_864,
        "c78a66751be956b60ff0f879cd0f733638a71ce3",
    ),
    "trojan": (
        "Hoosier 43105 R25B Cornering Trojan.mat",
        333_286,
        "475338b18b6cba21b967c7e75bdd12d9a0e3437a",
    ),
    "run21": ("Round6_Run21.mat", 10_864_944, "fca6c5b5116ae7fb16e2036b757ff294e0f790f6"),
    "run22": ("Round6_Run22.mat", 9_510_184, "a995a2a89290dc32c5372b22e7bb5f469b6cf949"),
}
CHANNELS = ("SA", "SL", "FZ", "IA", "P", "FX", "FY", "MX", "MZ", "N", "V")
RESPONSE_CHANNELS = ("FX", "FY", "MX", "MZ")
FZ_TARGETS = (222.0, 445.0, 667.0, 890.0, 1112.0)
P_TARGETS = (96.5, 82.7, 68.9, 55.2)
IA_TARGETS = (0.0, 2.0, 4.0)


@dataclass(frozen=True)
class ChannelError:
    max_abs: float
    rms: float
    mean_abs: float


@dataclass(frozen=True)
class R25bRawReproduction:
    generator_sha1: str
    trojan_sha1: str
    run21_sha1: str
    run22_sha1: str
    concatenated_raw_rows: int
    speed_filtered_raw_rows: int
    state_count: int
    reproduced_rows: int
    exact_structural_channels: tuple[str, ...]
    channel_errors: dict[str, ChannelError]
    matlab_smoothing_parameter: float
    scipy_lambda: float
    duplicate_slip_rule: str
    profile_reproduced: bool


def _sha1(path: Path) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify(path: Path, identity: tuple[str, int, str]) -> str:
    name, size, expected_sha1 = identity
    if not path.is_file():
        raise SystemExit(f"source file not found: {path}")
    if path.name != name:
        raise SystemExit(f"unexpected filename: expected {name!r}, received {path.name!r}")
    if path.stat().st_size != size:
        raise SystemExit(f"source size mismatch for {name}")
    actual = _sha1(path)
    if actual != expected_sha1:
        raise SystemExit(f"source SHA-1 mismatch for {name}: {actual}")
    return actual


def _load(path: Path) -> dict[str, "numpy.ndarray"]:
    try:
        import numpy
        from scipy.io import loadmat
    except ImportError as exc:
        raise SystemExit("NumPy and SciPy are required for the offline reproduction oracle") from exc
    source = loadmat(path, squeeze_me=True)
    result: dict[str, numpy.ndarray] = {}
    for channel in CHANNELS:
        if channel not in source:
            raise SystemExit(f"{path.name} is missing channel {channel}")
        values = numpy.asarray(source[channel], dtype=float).reshape(-1)
        if not numpy.all(numpy.isfinite(values)):
            raise SystemExit(f"{path.name} channel {channel} contains nonfinite values")
        result[channel] = values
    lengths = {len(values) for values in result.values()}
    if len(lengths) != 1:
        raise SystemExit(f"{path.name} channels do not share one row count")
    return result


def _point_count(fz: float, pressure: float, inclination: float) -> int:
    count = 100
    if fz >= 667.0:
        count += 30
    if pressure >= 68.9:
        count += 30
    if inclination <= 2.0:
        count += 30
    return count


def _independent_smoothing_spline(
    slip: "numpy.ndarray",
    response: "numpy.ndarray",
    evaluation_slip: "numpy.ndarray",
) -> "numpy.ndarray":
    import numpy
    from scipy.interpolate import make_smoothing_spline

    order = numpy.argsort(slip, kind="stable")
    ordered_slip = slip[order]
    ordered_response = response[order]
    unique_slip, first_indices, counts = numpy.unique(
        ordered_slip, return_index=True, return_counts=True
    )
    sums = numpy.add.reduceat(ordered_response, first_indices)
    means = sums / counts
    # MATLAB csaps/smoothingspline p=0.5 has lambda=(1-p)/p=1.
    spline = make_smoothing_spline(
        unique_slip,
        means,
        w=counts.astype(float),
        lam=1.0,
    )
    return numpy.asarray(spline(evaluation_slip), dtype=float)


def reproduce(
    *,
    generator: Path,
    trojan: Path,
    run21: Path,
    run22: Path,
) -> R25bRawReproduction:
    import numpy

    hashes = {
        key: _verify(path, EXPECTED[key])
        for key, path in (
            ("generator", generator),
            ("trojan", trojan),
            ("run21", run21),
            ("run22", run22),
        )
    }
    run_a = _load(run21)
    run_b = _load(run22)
    concatenated = {
        channel: numpy.concatenate((run_a[channel], run_b[channel]))
        for channel in CHANNELS
    }
    concatenated_rows = len(concatenated["SA"])
    speed_mask = numpy.abs(concatenated["V"] - 40.0) < 10.0
    raw = {channel: values[speed_mask] for channel, values in concatenated.items()}
    processed = _load(trojan)

    predicted: dict[str, list[float]] = {
        channel: [] for channel in ("SA", "FZ", "IA", "P", *RESPONSE_CHANNELS)
    }
    state_count = 0
    for fz in FZ_TARGETS:
        for pressure in P_TARGETS:
            for inclination in IA_TARGETS:
                mask = (
                    (numpy.abs(raw["FZ"] + fz) < 100.0)
                    & (numpy.abs(raw["P"] - pressure) < 5.0)
                    & (numpy.abs(raw["IA"] - inclination) < 1.0)
                    & (raw["SL"] == 0.0)
                )
                if not numpy.any(mask):
                    raise SystemExit(
                        f"no raw rows selected for FZ={fz}, P={pressure}, IA={inclination}"
                    )
                count = _point_count(fz, pressure, inclination)
                sim_sa = numpy.linspace(-12.0, 12.0, count)
                predicted["SA"].extend(sim_sa)
                predicted["FZ"].extend((fz,) * count)
                predicted["IA"].extend((inclination,) * count)
                predicted["P"].extend((pressure,) * count)
                for channel in RESPONSE_CHANNELS:
                    scaled = raw[channel][mask] / raw["FZ"][mask] * (-fz)
                    fitted = _independent_smoothing_spline(
                        raw["SA"][mask], scaled, sim_sa
                    )
                    predicted[channel].extend(fitted)
                state_count += 1

    arrays = {channel: numpy.asarray(values, dtype=float) for channel, values in predicted.items()}
    errors: dict[str, ChannelError] = {}
    for channel, values in arrays.items():
        difference = values - processed[channel]
        errors[channel] = ChannelError(
            max_abs=float(numpy.max(numpy.abs(difference))),
            rms=float(numpy.sqrt(numpy.mean(difference * difference))),
            mean_abs=float(numpy.mean(numpy.abs(difference))),
        )

    exact_structural = tuple(
        channel
        for channel in ("FZ", "IA", "P")
        if numpy.array_equal(arrays[channel], processed[channel])
    )
    profile_reproduced = (
        state_count == 60
        and len(arrays["SA"]) == 9630
        and exact_structural == ("FZ", "IA", "P")
        and errors["SA"].max_abs < 1.0e-12
        and errors["FX"].max_abs < 2.0e-6
        and errors["FY"].max_abs < 1.0e-4
        and errors["MX"].max_abs < 2.0e-6
        and errors["MZ"].max_abs < 2.0e-6
    )
    return R25bRawReproduction(
        generator_sha1=hashes["generator"],
        trojan_sha1=hashes["trojan"],
        run21_sha1=hashes["run21"],
        run22_sha1=hashes["run22"],
        concatenated_raw_rows=concatenated_rows,
        speed_filtered_raw_rows=len(raw["SA"]),
        state_count=state_count,
        reproduced_rows=len(arrays["SA"]),
        exact_structural_channels=exact_structural,
        channel_errors=errors,
        matlab_smoothing_parameter=0.5,
        scipy_lambda=1.0,
        duplicate_slip_rule="stable sort; identical SA samples replaced by count-weighted mean",
        profile_reproduced=profile_reproduced,
    )


def _json_default(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(type(value).__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", required=True, type=Path)
    parser.add_argument("--trojan", required=True, type=Path)
    parser.add_argument("--run21", required=True, type=Path)
    parser.add_argument("--run22", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = reproduce(
        generator=args.generator,
        trojan=args.trojan,
        run21=args.run21,
        run22=args.run22,
    )
    rendered = json.dumps(asdict(result), indent=2, sort_keys=True) + "\n"
    if args.json_output is not None:
        args.json_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if not result.profile_reproduced:
        print("Independent R25B raw-input reproduction failed closed.")
        return 3
    print("Independent raw-input reproduction matches the processed Trojan within frozen bounds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
