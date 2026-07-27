from __future__ import annotations

import math
import unittest

from pssd_suspension.linkage_statics import (
    IdealTwoForceLink,
    LinkageStaticsFailureCode,
    PrescribedExternalWrench,
    solve_linkage_statics,
)
from tests.test_suspension_linkage_statics import FRAME, TARGET_FORCE_N, build_links, prescribed_wrench_for_forces


class SuspensionLinkageStaticsFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.links = build_links()
        self.wrench = prescribed_wrench_for_forces(
            self.links,
            TARGET_FORCE_N,
            reference_point_m=(0.0, 0.0, 0.0),
        )

    def test_wrong_link_count_is_unsupported_not_approximately_solved(self) -> None:
        for links in (self.links[:5], self.links + (self.links[0],)):
            result = solve_linkage_statics(links, self.wrench)
            self.assertFalse(result.ok)
            self.assertEqual(result.failure_code, LinkageStaticsFailureCode.UNSUPPORTED_TOPOLOGY)
            self.assertEqual(result.link_forces, ())

    def test_duplicate_link_id_fails(self) -> None:
        links = list(self.links)
        links[5] = IdealTwoForceLink(
            link_id="L1",
            frame_id=FRAME,
            body_point_m=links[5].body_point_m,
            remote_point_m=links[5].remote_point_m,
        )
        result = solve_linkage_statics(tuple(links), self.wrench)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, LinkageStaticsFailureCode.DUPLICATE_LINK_ID)

    def test_zero_length_link_fails_before_matrix_assembly(self) -> None:
        links = list(self.links)
        body = links[3].body_point_m
        links[3] = IdealTwoForceLink("L4", FRAME, body, body)
        result = solve_linkage_statics(tuple(links), self.wrench)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, LinkageStaticsFailureCode.DEGENERATE_LINK)
        self.assertEqual(result.equilibrium_matrix, ())

    def test_frame_mismatch_fails(self) -> None:
        links = list(self.links)
        link = links[2]
        links[2] = IdealTwoForceLink(
            link.link_id,
            "wrong_frame",
            link.body_point_m,
            link.remote_point_m,
        )
        result = solve_linkage_statics(tuple(links), self.wrench)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, LinkageStaticsFailureCode.FRAME_MISMATCH)

    def test_nonfinite_input_fails(self) -> None:
        wrench = PrescribedExternalWrench(
            frame_id=FRAME,
            reference_point_m=(0.0, 0.0, 0.0),
            force_N=(math.nan, -260.0, -340.0),
            moment_Nm=(-40.0, -50.0, -60.0),
        )
        result = solve_linkage_statics(self.links, wrench)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, LinkageStaticsFailureCode.NONFINITE_INPUT)

    def test_singular_six_link_geometry_fails_without_force_vector(self) -> None:
        links = list(self.links)
        links[3] = IdealTwoForceLink("L4", FRAME, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        result = solve_linkage_statics(tuple(links), self.wrench)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, LinkageStaticsFailureCode.SINGULAR_EQUILIBRIUM)
        self.assertEqual(result.link_forces, ())

    def test_ill_conditioned_six_link_geometry_fails_without_regularization(self) -> None:
        links = list(self.links)
        epsilon = 1.0e-10
        links[3] = IdealTwoForceLink("L4", FRAME, (0.0, epsilon, 0.0), (0.0, epsilon, 1.0))
        result = solve_linkage_statics(tuple(links), self.wrench)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, LinkageStaticsFailureCode.ILL_CONDITIONED_EQUILIBRIUM)
        self.assertIsNotNone(result.condition_number_inf)
        assert result.condition_number_inf is not None
        self.assertGreater(result.condition_number_inf, 1.0e10)
        self.assertEqual(result.link_forces, ())


if __name__ == "__main__":
    unittest.main()
