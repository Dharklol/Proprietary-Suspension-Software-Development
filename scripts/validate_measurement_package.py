from __future__ import annotations

import argparse
from pathlib import Path

from pssd_measurements import validate_measurement_package


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one physical-measurement package against the repository contract."
    )
    parser.add_argument("package", type=Path, help="Directory containing the session package")
    parser.add_argument(
        "--contract",
        type=Path,
        default=None,
        help="Optional measurement_data_contract.toml path",
    )
    args = parser.parse_args()
    issues = validate_measurement_package(args.package, contract_path=args.contract)
    for issue in issues:
        print(issue)
    if issues:
        print(f"Measurement package failed with {len(issues)} issue(s).")
        return 1
    print("Measurement package is structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
