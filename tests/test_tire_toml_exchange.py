from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from pssd_tire import (
    LateralForceBranch,
    LateralForceCurveSample,
    TireLateralForceBranchSet,
    TireOperatingPoint,
    format_lateral_force_branch_set_toml,
    load_lateral_force_branch_set,
)


class TireTomlExchangeTests(unittest.TestCase):
    def test_roundtrip_preserves_branch_identity_operating_point_and_samples(self) -> None:
        branch_set = TireLateralForceBranchSet(
            branch_set_id="roundtrip-set",
            version="0.1.0",
            source_tire_id="SOURCE",
            intended_tire_id="INTENDED",
            authority="test authority",
            source_path="source.mat",
            provenance=(("exporter", "unit-test"), ("note", 'quote " and slash \\')),
            branches=(
                LateralForceBranch(
                    branch_id="state-a",
                    operating_point=TireOperatingPoint(445.0, 2.0, 82.7),
                    samples=(
                        LateralForceCurveSample(0.5, 100.0),
                        LateralForceCurveSample(2.0, 500.0),
                        LateralForceCurveSample(5.0, 900.0),
                    ),
                    authority="test branch",
                    source_branch_description="negative-SA positive-FY pre-peak branch",
                    provenance=(("source_sign", "SA<0,FY>0"),),
                ),
            ),
        )

        rendered = format_lateral_force_branch_set_toml(branch_set)
        self.assertIn('source_type = "explicit_lateral_force_branches"', rendered)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "branches.toml"
            path.write_text(rendered, encoding="utf-8")
            loaded = load_lateral_force_branch_set(path)

        self.assertEqual(loaded.branch_set_id, branch_set.branch_set_id)
        self.assertEqual(loaded.source_tire_id, "SOURCE")
        self.assertEqual(loaded.intended_tire_id, "INTENDED")
        self.assertEqual(loaded.branches[0].operating_point.pressure_kpa, 82.7)
        self.assertEqual(
            [sample.lateral_force_magnitude_n for sample in loaded.branches[0].samples],
            [100.0, 500.0, 900.0],
        )
        self.assertEqual(dict(loaded.branches[0].provenance)["source_sign"], "SA<0,FY>0")


if __name__ == "__main__":
    unittest.main()
