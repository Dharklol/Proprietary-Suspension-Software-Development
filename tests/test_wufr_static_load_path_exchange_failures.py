from __future__ import annotations

from copy import deepcopy
import math
import unittest

from pssd_suspension.wufr_static_load_path_exchange import (
    ROOT,
    WUFRStaticLoadPathExchangeFailureCode,
    evaluate_wufr_static_load_path_exchange,
    load_wufr_static_load_path_source_documents,
)


class WufrStaticLoadPathExchangeFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = load_wufr_static_load_path_source_documents(root=ROOT)

    def evaluate(self, documents):
        return evaluate_wufr_static_load_path_exchange(root=ROOT, source_documents=documents)

    def assert_failed(self, result, code) -> None:
        self.assertFalse(result.ok)
        self.assertIsNone(result.packet)
        self.assertEqual(result.failure_code, code)

    def test_missing_source_document_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        del documents["carrier_wrench"]
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_UNAVAILABLE,
        )

    def test_reordered_corner_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        corners = documents["carrier_wrench"]["corners"]
        corners[0], corners[1] = corners[1], corners[0]
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH,
        )

    def test_configuration_and_state_mismatch_reject_packet(self) -> None:
        documents = deepcopy(self.documents)
        documents["level1_interface"]["configuration_id"] = "wrong"
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.CONFIGURATION_MISMATCH,
        )
        documents = deepcopy(self.documents)
        documents["rocker_included"]["static_state_id"] = "wrong"
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.STATIC_STATE_MISMATCH,
        )

    def test_setting_mismatch_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        documents["vehicle_equilibrium"]["primary"]["front_arb_setting"] = 2
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.SETTING_MISMATCH,
        )

    def test_nonfinite_source_value_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        documents["rocker_included"]["corners"][0]["included"]["point_loads"][0]["force_N"][0] = math.nan
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.NONFINITE_SOURCE_VALUE,
        )

    def test_missing_frame_or_point_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        documents["carrier_wrench"]["corners"][0]["level1_wrench"]["frame_id"] = ""
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.FRAME_OR_POINT_IDENTITY_MISSING,
        )
        documents = deepcopy(self.documents)
        documents["level1_interface"]["corners"][0]["solve"]["upper_hinge"]["point_m"] = []
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.FRAME_OR_POINT_IDENTITY_MISSING,
        )

    def test_missing_kw_v5_boundary_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        documents["rocker_included"]["corners"][0]["included"]["missing_load_ids"] = []
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.MISSING_BOUNDARY_NOT_DECLARED,
        )

    def test_prohibited_authority_promotion_rejects_packet(self) -> None:
        for source_key, boundary_key in (
            ("carrier_wrench", "structural_load_case_authority"),
            ("level1_interface", "individual_a_arm_joint_split_authorized"),
            ("rocker_included", "complete_hardware_reaction"),
            ("rocker_included", "structural_release_authority"),
        ):
            with self.subTest(source_key=source_key, boundary_key=boundary_key):
                documents = deepcopy(self.documents)
                documents[source_key]["boundaries"][boundary_key] = True
                self.assert_failed(
                    self.evaluate(documents),
                    WUFRStaticLoadPathExchangeFailureCode.PROHIBITED_AUTHORITY_FLAG,
                )

    def test_unsuccessful_upstream_record_rejects_packet(self) -> None:
        documents = deepcopy(self.documents)
        documents["level1_interface"]["status"] = "failure"
        self.assert_failed(
            self.evaluate(documents),
            WUFRStaticLoadPathExchangeFailureCode.SOURCE_RECORD_FAILURE,
        )


if __name__ == "__main__":
    unittest.main()
