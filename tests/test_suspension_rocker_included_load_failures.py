from __future__ import annotations

import math
import unittest

from pssd_suspension.rocker_included_load import (
    RockerIncludedLoadFailureCode,
    RockerPointLoad,
    evaluate_rocker_included_load,
)


FRAME = "TEST_FRAME"
CONFIG = "TEST_CONFIG"
CASE = "TEST_CASE"


def _load(
    load_id: str = "load",
    *,
    point=(1.0, 0.0, 0.0),
    force=(0.0, 1.0, 0.0),
    source_id="SOURCE",
    frame_id=FRAME,
    configuration_id=CONFIG,
    load_case_id=CASE,
) -> RockerPointLoad:
    return RockerPointLoad(
        load_id=load_id,
        application_point_m=point,
        force_N=force,
        source_id=source_id,
        frame_id=frame_id,
        configuration_id=configuration_id,
        load_case_id=load_case_id,
    )


def _solve(*, loads=(_load(),), missing=("missing",), axis=(0.0, 0.0, 1.0)):
    return evaluate_rocker_included_load(
        rocker_pivot_m=(0.0, 0.0, 0.0),
        rocker_axis=axis,
        loads=loads,
        missing_load_ids=missing,
        frame_id=FRAME,
        configuration_id=CONFIG,
        load_case_id=CASE,
    )


class RockerIncludedLoadFailureTests(unittest.TestCase):
    def test_empty_load_set_fails(self) -> None:
        result = _solve(loads=())
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, RockerIncludedLoadFailureCode.EMPTY_INCLUDED_SET)

    def test_degenerate_axis_fails(self) -> None:
        result = _solve(axis=(0.0, 0.0, 0.0))
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, RockerIncludedLoadFailureCode.DEGENERATE_ROCKER_AXIS)

    def test_nonfinite_point_or_force_fails(self) -> None:
        for load in (
            _load(point=(math.nan, 0.0, 0.0)),
            _load(force=(0.0, math.inf, 0.0)),
        ):
            with self.subTest(load=load):
                result = _solve(loads=(load,))
                self.assertFalse(result.ok)
                self.assertEqual(result.failure_code, RockerIncludedLoadFailureCode.NONFINITE_INPUT)

    def test_missing_and_duplicate_identities_fail(self) -> None:
        missing_id = _solve(loads=(_load(load_id=""),))
        self.assertEqual(missing_id.failure_code, RockerIncludedLoadFailureCode.MISSING_LOAD_IDENTITY)
        missing_source = _solve(loads=(_load(source_id=""),))
        self.assertEqual(missing_source.failure_code, RockerIncludedLoadFailureCode.MISSING_LOAD_IDENTITY)
        duplicate = _solve(loads=(_load("same"), _load("same", point=(0.0, 1.0, 0.0))))
        self.assertEqual(duplicate.failure_code, RockerIncludedLoadFailureCode.DUPLICATE_LOAD_IDENTITY)
        duplicate_missing = _solve(missing=("same", "same"))
        self.assertEqual(duplicate_missing.failure_code, RockerIncludedLoadFailureCode.DUPLICATE_LOAD_IDENTITY)
        overlap = _solve(loads=(_load("same"),), missing=("same",))
        self.assertEqual(overlap.failure_code, RockerIncludedLoadFailureCode.LOAD_SET_IDENTITY_CONFLICT)

    def test_frame_configuration_and_load_case_mismatch_fail(self) -> None:
        cases = (
            (_load(frame_id="OTHER"), RockerIncludedLoadFailureCode.FRAME_MISMATCH),
            (_load(configuration_id="OTHER"), RockerIncludedLoadFailureCode.CONFIGURATION_MISMATCH),
            (_load(load_case_id="OTHER"), RockerIncludedLoadFailureCode.LOAD_CASE_MISMATCH),
        )
        for load, expected in cases:
            with self.subTest(expected=expected):
                result = _solve(loads=(load,))
                self.assertFalse(result.ok)
                self.assertEqual(result.failure_code, expected)

    def test_nonzero_axis_residual_is_not_repaired_or_failed(self) -> None:
        result = _solve(loads=(_load(point=(1.0, 0.0, 0.0), force=(0.0, 10.0, 0.0)),))
        self.assertTrue(result.ok, result.message)
        self.assertAlmostEqual(result.free_axis_moment_residual_Nm, 10.0)
        self.assertEqual(result.pivot_moment_contribution_Nm, (0.0, 0.0, 0.0))
        self.assertEqual(result.final_moment_residual_Nm, (0.0, 0.0, 10.0))
        self.assertFalse(result.complete_hardware_reaction)


if __name__ == "__main__":
    unittest.main()
