from __future__ import annotations

import math
from pathlib import Path
import tempfile
import tomllib
import unittest

from pssd_tire.r25b_branch_classification import (
    ALL_CLASSIFICATION_IDS,
    CENTRAL_TRANSITION,
    DEFAULT_R25B_BRANCH_AUTHORIZATION,
    NEGATIVE_POST_PEAK,
    NEGATIVE_PRE_PEAK,
    POSITIVE_POST_PEAK,
    POSITIVE_PRE_PEAK,
    R25B_BRANCH_AUTHORIZATION_ID,
    R25B_BRANCH_CLASSIFICATION_AUTHORIZED,
    classify_r25b_curve_segments,
    require_r25b_branch_classification_authorization,
)
from pssd_tire.r25b_named_runtime import (
    evaluate_r25b_classified_lateral,
    invert_r25b_classified_lateral_force,
    load_r25b_classified_lateral_table,
)
from pssd_tire.r25b_runtime import (
    R25B_CANONICAL_SOURCE_CONVENTION_ID,
    load_r25b_steady_state_lateral_table,
)
from pssd_tire.r25b_source_native import EXPECTED_INTENDED_TIRE_ID, EXPECTED_SOURCE_TIRE_ID
from pssd_tire.steady_state_lateral import (
    SteadyStateLateralCurve,
    SteadyStateLateralFailure,
    SteadyStateLateralOperatingState,
    SteadyStateLateralTable,
)


class R25bBranchClassificationAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = load_r25b_steady_state_lateral_table()
        cls.classified = load_r25b_classified_lateral_table()

    def test_authorization_freezes_selected_package(self) -> None:
        self.assertTrue(R25B_BRANCH_CLASSIFICATION_AUTHORIZED)
        require_r25b_branch_classification_authorization()
        with DEFAULT_R25B_BRANCH_AUTHORIZATION.open("rb") as stream:
            authorization = tomllib.load(stream)
        self.assertEqual(authorization["authorization_id"], R25B_BRANCH_AUTHORIZATION_ID)
        self.assertEqual(authorization["status"], "reviewed")
        self.assertTrue(authorization["implementation_authorized"])
        scope = authorization["scope"]
        self.assertTrue(scope["named_branch_selection_authorized"])
        self.assertTrue(scope["exact_source_state_named_selection_authorized"])
        self.assertFalse(scope["interpolated_state_named_selection_authorized"])
        self.assertTrue(scope["generic_all_root_inverse_remains_authorized"])
        policy = authorization["branch_policy"]
        self.assertEqual(policy["pre_peak_semantics"], "strict_monotonic_prefix")
        self.assertEqual(policy["center_crossing_role"], "central_transition")
        self.assertEqual(policy["boundary_peak_post_peak_role"], "post_peak_unavailable")
        self.assertEqual(
            policy["multiple_named_roots_behavior"],
            "fail_closed_without_selected_candidate",
        )

    def test_classification_is_sample_identical_and_complete(self) -> None:
        self.assertEqual(len(self.base.curves), 60)
        self.assertEqual(len(self.classified.curves), 60)
        self.assertEqual(
            sum(len(curve.slip_angle_rad) for curve in self.classified.curves),
            9630,
        )
        for base_curve, classified_curve in zip(self.base.curves, self.classified.curves):
            self.assertEqual(base_curve.curve_id, classified_curve.curve_id)
            self.assertEqual(base_curve.slip_angle_rad, classified_curve.slip_angle_rad)
            self.assertEqual(base_curve.lateral_force_N, classified_curve.lateral_force_N)
            self.assertEqual(
                len(classified_curve.segment_branch_ids),
                len(classified_curve.slip_angle_rad) - 1,
            )
            self.assertEqual(
                classified_curve.segment_branch_ids.count(CENTRAL_TRANSITION),
                1,
            )
            self.assertTrue(
                set(classified_curve.segment_branch_ids).issubset(ALL_CLASSIFICATION_IDS)
            )

    def test_audit_counts_are_reproduced_by_executable_policy(self) -> None:
        classifications = tuple(
            classify_r25b_curve_segments(curve) for curve in self.base.curves
        )
        self.assertEqual(
            sum(item.positive_reversal_before_peak for item in classifications),
            4,
        )
        self.assertEqual(
            sum(item.negative_reversal_before_peak for item in classifications),
            9,
        )
        self.assertEqual(
            sum(item.positive_peak_at_source_boundary for item in classifications),
            13,
        )
        self.assertEqual(
            sum(item.negative_peak_at_source_boundary for item in classifications),
            18,
        )

    def test_published_prepeak_segments_are_strictly_monotonic_outward(self) -> None:
        for curve in self.classified.curves:
            for index, branch_id in enumerate(curve.segment_branch_ids):
                left_force = curve.lateral_force_N[index]
                right_force = curve.lateral_force_N[index + 1]
                if branch_id == POSITIVE_PRE_PEAK:
                    self.assertGreater(right_force, left_force, curve.curve_id)
                    self.assertGreater(curve.slip_angle_rad[index], 0.0)
                elif branch_id == NEGATIVE_PRE_PEAK:
                    self.assertGreater(-left_force, -right_force, curve.curve_id)
                    self.assertLess(curve.slip_angle_rad[index + 1], 0.0)

    def _midpoint_query(self, branch_id: str):
        for curve in self.classified.curves:
            for index, candidate_id in enumerate(curve.segment_branch_ids):
                if candidate_id == branch_id:
                    return curve, 0.5 * (
                        curve.lateral_force_N[index] + curve.lateral_force_N[index + 1]
                    )
        self.fail(f"no segment found for {branch_id}")

    def test_positive_and_negative_named_prepeak_selection(self) -> None:
        for branch_id in (POSITIVE_PRE_PEAK, NEGATIVE_PRE_PEAK):
            curve, force = self._midpoint_query(branch_id)
            result = invert_r25b_classified_lateral_force(
                normal_load_N=curve.normal_load_N,
                inclination_rad=curve.inclination_rad,
                pressure_Pa=curve.pressure_Pa,
                requested_lateral_force_N=force,
                branch_selector=branch_id,
                table=self.classified,
            )
            self.assertTrue(result.branch_selection_applied)
            self.assertIsNotNone(result.selected_candidate)
            assert result.selected_candidate is not None
            self.assertIn(branch_id, result.selected_candidate.contributing_branch_ids)
            if branch_id == POSITIVE_PRE_PEAK:
                self.assertGreater(result.selected_candidate.slip_angle_rad, 0.0)
            else:
                self.assertLess(result.selected_candidate.slip_angle_rad, 0.0)

    def test_boundary_peak_has_no_published_postpeak_branch(self) -> None:
        selected_curve = next(
            curve
            for curve in self.classified.curves
            if "positive_post_peak_unavailable_at_source_boundary"
            in curve.domain_and_censor_metadata
            and POSITIVE_PRE_PEAK in curve.segment_branch_ids
        )
        segment_index = selected_curve.segment_branch_ids.index(POSITIVE_PRE_PEAK)
        force = 0.5 * (
            selected_curve.lateral_force_N[segment_index]
            + selected_curve.lateral_force_N[segment_index + 1]
        )
        with self.assertRaises(SteadyStateLateralFailure) as context:
            invert_r25b_classified_lateral_force(
                normal_load_N=selected_curve.normal_load_N,
                inclination_rad=selected_curve.inclination_rad,
                pressure_Pa=selected_curve.pressure_Pa,
                requested_lateral_force_N=force,
                branch_selector=POSITIVE_POST_PEAK,
                table=self.classified,
            )
        self.assertEqual(context.exception.failure_code, "inverse_branch_unavailable")

    def test_named_selection_requires_exact_source_state(self) -> None:
        state = SteadyStateLateralOperatingState(
            slip_angle_rad=math.radians(2.0),
            normal_load_N=333.5,
            inclination_rad=math.radians(1.0),
            pressure_Pa=62_050.0,
            state_id="R25B_INTERPOLATED_NAMED_QUERY",
            source_id=EXPECTED_SOURCE_TIRE_ID,
            source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        )
        force = evaluate_r25b_classified_lateral(state, table=self.classified).lateral_force_N
        with self.assertRaises(SteadyStateLateralFailure) as context:
            invert_r25b_classified_lateral_force(
                normal_load_N=state.normal_load_N,
                inclination_rad=state.inclination_rad,
                pressure_Pa=state.pressure_Pa,
                requested_lateral_force_N=force,
                branch_selector=POSITIVE_PRE_PEAK,
                table=self.classified,
            )
        self.assertEqual(
            context.exception.failure_code,
            "inverse_named_branch_requires_exact_source_state",
        )

    def test_multiple_roots_inside_one_named_branch_fail_closed(self) -> None:
        curve = SteadyStateLateralCurve(
            curve_id="SYNTHETIC_R25B_MULTIPLE_POSTPEAK",
            normal_load_N=1000.0,
            inclination_rad=0.0,
            pressure_Pa=82_700.0,
            slip_angle_rad=(-0.2, -0.1, 0.05, 0.1, 0.2, 0.3),
            lateral_force_N=(-200.0, -100.0, 50.0, 200.0, 100.0, 180.0),
            source_tire_id=EXPECTED_SOURCE_TIRE_ID,
            intended_tire_id=EXPECTED_INTENDED_TIRE_ID,
            source_path="synthetic://r25b-branch-ambiguity",
            source_hash="sha256:synthetic-r25b-branch-ambiguity",
            source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
            adapter_id="ADAPTER-TIRE-R25B-SAE-J670-TO-CANONICAL-GAUGE-V1",
            fidelity_label="synthetic_software_verification",
            source_branch_role="synthetic_classified_curve",
            segment_branch_ids=(
                NEGATIVE_PRE_PEAK,
                CENTRAL_TRANSITION,
                POSITIVE_PRE_PEAK,
                POSITIVE_POST_PEAK,
                POSITIVE_POST_PEAK,
            ),
        )
        table = SteadyStateLateralTable(
            table_id="SYNTHETIC_R25B_MULTIPLE_POSTPEAK_TABLE",
            curves=(curve,),
        )
        with self.assertRaises(SteadyStateLateralFailure) as context:
            invert_r25b_classified_lateral_force(
                normal_load_N=curve.normal_load_N,
                inclination_rad=curve.inclination_rad,
                pressure_Pa=curve.pressure_Pa,
                requested_lateral_force_N=150.0,
                branch_selector=POSITIVE_POST_PEAK,
                table=table,
            )
        self.assertEqual(context.exception.failure_code, "inverse_branch_ambiguous")

    def test_branch_authorization_tampering_fails_closed(self) -> None:
        text = DEFAULT_R25B_BRANCH_AUTHORIZATION.read_text(encoding="utf-8")
        tampered = text.replace(
            'pre_peak_semantics = "strict_monotonic_prefix"',
            'pre_peak_semantics = "global_extremum_positional"',
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUTH-TIRE-0003.toml"
            path.write_text(tampered, encoding="utf-8")
            with self.assertRaises(SteadyStateLateralFailure) as context:
                require_r25b_branch_classification_authorization(path)
        self.assertEqual(context.exception.failure_code, "source_adapter_mismatch")


if __name__ == "__main__":
    unittest.main()
