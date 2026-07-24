#!/usr/bin/env python3
"""Export reviewed R25B Cornering Trojan states to PR #30 force-demand TOML.

This is an offline source-export command.  It requires SciPy only when invoked because the
project runtime deliberately does not depend on SciPy.  The command validates the source
file hash by default, applies the named WUFR-26 processed-Trojan profile, and writes the
exact generic branch-set schema consumed by ``pssd_tire.force_demand``.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from pssd_tire import TireDataError, TireOperatingPoint, write_lateral_force_branch_set_toml
from pssd_tire.ttc_cornering import (
    WUFR26_APRIL_CORNERING_TROJAN_V0,
    build_branch_set,
    export_cornering_trojan_mat_branch,
)

EXPECTED_CORNERING_TROJAN_SHA1 = "475338b18b6cba21b967c7e75bdd12d9a0e3437a"
SOURCE_TIRE_ID = "HOOSIER_43105_18X7.5-10_R25B"
INTENDED_TIRE_ID = "HOOSIER_43104_18X7.5-10_R20"


def _sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _state(value: str) -> tuple[str, TireOperatingPoint]:
    try:
        state_id, fz, ia, pressure = value.split(":", 3)
        point = TireOperatingPoint(float(fz), float(ia), float(pressure))
    except (ValueError, TireDataError) as exc:
        raise argparse.ArgumentTypeError(
            "state must be ID:FZ_N:IA_DEG:P_KPA, for example outside:1112:2:82.7"
        ) from exc
    if not state_id:
        raise argparse.ArgumentTypeError("state ID cannot be empty")
    return state_id, point


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mat", type=Path, help="Hoosier 43105 R25B Cornering Trojan.mat")
    parser.add_argument("output", type=Path, help="Output explicit_lateral_force_branches TOML")
    parser.add_argument(
        "--state",
        action="append",
        type=_state,
        required=True,
        help="Exact exported state ID:FZ_N:IA_DEG:P_KPA; repeat for multiple branches",
    )
    parser.add_argument(
        "--expected-sha1",
        default=EXPECTED_CORNERING_TROJAN_SHA1,
        help="Expected source SHA-1; defaults to the frozen Box source hash",
    )
    parser.add_argument(
        "--branch-set-id",
        default="WUFR26_H43105_R25B_FORCE_BRANCHES_V0",
        help="Branch-set identity written to the exchange file",
    )
    parser.add_argument(
        "--authority",
        default=(
            "WUFR-26 processed Cornering Trojan source export; R25B is the project-authorized "
            "engineering-equivalent steering-development source for intended R20"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = args.mat.resolve()
    if not source.is_file():
        print(f"source MAT file does not exist: {source}", file=sys.stderr)
        return 2

    actual_sha1 = _sha1(source)
    if args.expected_sha1 and actual_sha1.lower() != args.expected_sha1.lower():
        print(
            f"source SHA-1 mismatch: expected {args.expected_sha1}, got {actual_sha1}",
            file=sys.stderr,
        )
        return 2

    exports = []
    try:
        for state_id, point in args.state:
            exports.append(
                export_cornering_trojan_mat_branch(
                    source,
                    point,
                    branch_id=state_id,
                    authority=args.authority,
                    source_branch_description=(
                        "WUFR-26 processed R25B Cornering Trojan, negative-SA/positive-FY "
                        "into-turn branch, bounded through the source pre-peak maximum"
                    ),
                    profile=WUFR26_APRIL_CORNERING_TROJAN_V0,
                    provenance=(
                        ("source_box_file_id", "1890914118742"),
                        ("source_sha1", actual_sha1),
                        ("source_kind", "processed_cornering_trojan"),
                        ("track_scale", "none"),
                    ),
                )
            )
        branch_set = build_branch_set(
            tuple(exports),
            branch_set_id=args.branch_set_id,
            version="0.1.0",
            source_tire_id=SOURCE_TIRE_ID,
            intended_tire_id=INTENDED_TIRE_ID,
            authority=args.authority,
            source_path=str(source),
            provenance=(
                ("source_box_file_id", "1890914118742"),
                ("source_sha1", actual_sha1),
                ("profile_id", WUFR26_APRIL_CORNERING_TROJAN_V0.profile_id),
                ("historical_two_thirds_track_scale_applied", "false"),
            ),
        )
        write_lateral_force_branch_set_toml(args.output, branch_set)
    except TireDataError as exc:
        print(f"export rejected: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {len(exports)} branch(es) to {args.output}")
    for item in exports:
        audit = item.audit
        print(
            f"  {item.branch.branch_id}: {audit.prepeak_rows} pre-peak points, "
            f"|alpha|max={audit.maximum_exported_slip_angle_deg:.6g} deg, "
            f"|Fy|max={audit.maximum_exported_lateral_force_n:.6g} N"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
