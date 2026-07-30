from __future__ import annotations

from dataclasses import replace
import unittest

from scripts.run_wufr_static_level1_interface_load_benchmarks import provider
from pssd_suspension.wufr_interface_statics import InterfaceStaticsSolverConfig
from pssd_suspension.wufr_static_level1_interface_loads import (
    WUFRStaticLevel1Config,
    WUFRStaticLevel1Error,
    WUFRStaticLevel1FailureCode,
    evaluate_wufr_static_level1_interface_loads,
)
from pssd_vehicle.wufr_static_carrier_wrench import (
    WUFRStaticCarrierWrenchStatus,
    evaluate_wufr_static_carrier_wrenches,
)


class WufrStaticLevel1InterfaceLoadsFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = provider()
        cls.carrier = evaluate_wufr_static_carrier_wrenches(cls.provider.carrier_provider)
        assert cls.carrier.ok

    def test_reordered_collection_fails_without_partial_publication(self) -> None:
        reordered = replace(
            self.carrier,
            corners=(self.carrier.corners[1], self.carrier.corners[0], *self.carrier.corners[2:]),
        )
        result = evaluate_wufr_static_level1_interface_loads(self.provider, carrier_result=reordered)
        self.assertEqual(result.failure_code, WUFRStaticLevel1FailureCode.CORNER_COUNT_OR_ORDER_MISMATCH)
        self.assertEqual(result.corners, ())

    def test_unsuccessful_upstream_carrier_fails_closed(self) -> None:
        failed = replace(self.carrier, status=WUFRStaticCarrierWrenchStatus.FAILURE, message="injected")
        result = evaluate_wufr_static_level1_interface_loads(self.provider, carrier_result=failed)
        self.assertEqual(result.failure_code, WUFRStaticLevel1FailureCode.UPSTREAM_CARRIER_RESULT_FAILURE)
        self.assertEqual(result.corners, ())

    def test_frame_and_reference_mismatch_fail_before_solve(self) -> None:
        first = self.carrier.corners[0]
        assert first.level1_wrench
        bad_frame = replace(first, level1_wrench=replace(first.level1_wrench, frame_id="wrong"))
        result = evaluate_wufr_static_level1_interface_loads(
            self.provider,
            carrier_result=replace(self.carrier, corners=(bad_frame, *self.carrier.corners[1:])),
        )
        self.assertEqual(result.failure_code, WUFRStaticLevel1FailureCode.FRAME_OR_REFERENCE_MISMATCH)
        shifted = list(first.level1_wrench.reference_point_m)
        shifted[0] += 1.0e-6
        bad_ref = replace(first, level1_wrench=replace(first.level1_wrench, reference_point_m=tuple(shifted)))
        result = evaluate_wufr_static_level1_interface_loads(
            self.provider,
            carrier_result=replace(self.carrier, corners=(bad_ref, *self.carrier.corners[1:])),
        )
        self.assertEqual(result.failure_code, WUFRStaticLevel1FailureCode.FRAME_OR_REFERENCE_MISMATCH)
        self.assertEqual(result.corners, ())

    def test_front_steering_unavailable_fails_closed(self) -> None:
        def failed(*args, **kwargs):
            raise WUFRStaticLevel1Error(
                WUFRStaticLevel1FailureCode.FRONT_STEERING_STATE_UNAVAILABLE,
                "injected",
            )
        result = evaluate_wufr_static_level1_interface_loads(
            self.provider,
            carrier_result=self.carrier,
            front_steering_builder=failed,
        )
        self.assertEqual(result.failure_code, WUFRStaticLevel1FailureCode.FRONT_STEERING_STATE_UNAVAILABLE)
        self.assertEqual(result.failed_corner_id, "front_left")
        self.assertEqual(result.corners, ())

    def test_corner_solver_condition_failure_fails_complete_collection(self) -> None:
        p = provider(config=WUFRStaticLevel1Config(solver_config=InterfaceStaticsSolverConfig(condition_limit=1.0)))
        result = evaluate_wufr_static_level1_interface_loads(p, carrier_result=self.carrier)
        self.assertEqual(result.failure_code, WUFRStaticLevel1FailureCode.CORNER_SOLVE_FAILURE)
        self.assertEqual(result.failed_corner_id, "front_left")
        self.assertEqual(result.corners, ())


if __name__ == "__main__":
    unittest.main()
