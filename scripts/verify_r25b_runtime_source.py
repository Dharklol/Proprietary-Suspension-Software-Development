from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_NAME = "Hoosier 43105 R25B Cornering Trojan.mat"
EXPECTED_SIZE_BYTES = 333_286
EXPECTED_SHA1 = "475338b18b6cba21b967c7e75bdd12d9a0e3437a"


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_source(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"source file not found: {path}")
    if path.name != EXPECTED_NAME:
        raise SystemExit(f"unexpected source filename: {path.name!r}")
    size = path.stat().st_size
    if size != EXPECTED_SIZE_BYTES:
        raise SystemExit(
            f"source size mismatch: expected {EXPECTED_SIZE_BYTES}, received {size}"
        )
    actual_sha1 = sha1_file(path)
    if actual_sha1 != EXPECTED_SHA1:
        raise SystemExit(
            f"source SHA-1 mismatch: expected {EXPECTED_SHA1}, received {actual_sha1}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail-closed preflight for the frozen R25B processed Trojan source."
    )
    parser.add_argument("source", type=Path)
    arguments = parser.parse_args()
    verify_source(arguments.source)
    print("R25B source identity verified.")
    print(
        "Next: execute scripts/export_r25b_cornering_force_branches.py using the "
        "frozen export profile; this verifier does not authorize runtime activation."
    )


if __name__ == "__main__":
    main()
