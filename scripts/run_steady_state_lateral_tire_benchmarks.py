from __future__ import annotations

import argparse
from pathlib import Path

from pssd_tire.steady_state_lateral_benchmarks import (
    build_benchmark_result,
    format_benchmark_result_json,
    write_benchmark_results,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MOD-TIRE-0001 synthetic benchmarks")
    parser.add_argument("--write", action="store_true", help="write frozen JSON and TOML records")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if args.write:
        json_path, toml_path = write_benchmark_results(root)
        print(json_path.relative_to(root))
        print(toml_path.relative_to(root))
    else:
        print(format_benchmark_result_json(build_benchmark_result()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
