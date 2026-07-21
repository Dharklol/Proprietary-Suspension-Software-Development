#!/usr/bin/env python3
"""Compute immutable source-file SHA-256 values for catalog freeze.

This script hashes raw bytes only. It never opens or rewrites the source through an
application-specific library, which prevents spreadsheet/CAD conversion from
changing the bytes being identified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit a JSON object keyed by path")
    args = parser.parse_args()

    results: dict[str, dict[str, object]] = {}
    failed = False
    for candidate in args.files:
        path = candidate.resolve()
        try:
            stat = path.stat()
            if not path.is_file():
                raise OSError("not a regular file")
            results[str(candidate)] = {
                "size_bytes": stat.st_size,
                "sha256": sha256_file(path),
            }
        except OSError as exc:
            failed = True
            results[str(candidate)] = {"error": str(exc)}

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for name, result in results.items():
            if "error" in result:
                print(f"ERROR  {name}: {result['error']}", file=sys.stderr)
            else:
                print(f"{result['sha256']}  {result['size_bytes']:>10}  {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
