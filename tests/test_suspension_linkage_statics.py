from __future__ import annotations

import math
import unittest

from pssd_suspension.linkage_statics import (
    IdealTwoForceLink,
    LinkageStaticsStatus,
    PrescribedExternalWrench,
    solve_linkage_statics,
)


FRAME = "synthetic_body_frame"
BODY_POINTS = (
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
)
UNIT_AXES = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
)
TARGET_FORCE_N = (100.0, 200.0, 300.0, 40.0, 50.0, 60.0)


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(s: float, a: tuple[float, float, float]) -> tuple[float, float, float]:
    return (s * a[0], s * a[1], s * a[2])


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def build_links(translation: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[IdealTwoForceLink, ...]:
    links = []
    for index, (body, axis) in enumerate(zip(BODY_POINTS, UNIT_AXES), start=1):
        body_t = _add(body, translation)
        remote_t = _add(_add(body, axis), translation)
        links.append(
            IdealTwoForceLink(
                link_id=f"L{index}",
                frame_id=FRAME,
                body_point_m=body_t,
                remote_point_m=remote_t,
                source_id="BENCH-SUSP-0018",
                configuration_id="ANALYTICAL_SIX_LINK_V0",
            )
        )
    return tuple(links)


def prescribed_wrench_for_forces(
    links: tuple[IdealTwoForceLink, ...],
    axial_force_N: tuple[float, ...],
    *,
    reference_point_m: tuple[float, float, float],
    load_case_id: str = "BENCH-SUSP-0018",
) -> PrescribedExternalWrench:
    force = (0.0, 0.0, 0.0)
    moment = (0.0, 0.0, 0.0)
    for link, axial in zip(links, axial_force_N):
        direction = _sub(link.remote_point_m, link.body_point_m)
        length = math.sqrt(sum(value * value for value in direction))
        unit = _scale(1.0 / length, direction)
        body_force = _scale(axial, unit)
        force = _add(force, body_force)
        moment = _add(moment, _cross(_sub(link.body_point_m, reference_point_m), body_force))
    return PrescribedExternalWrench(
        frame_id=FRAME,
        reference_point_m=reference_point_m,
        force_N=_scale(-1.0, force),
        moment_Nm=_scale(-1.0, moment),
        load_case_id=load_case_id,
        source_id="analytical_fixture",
    )


class SuspensionLinkageStaticsTests(unittest.TestCase):
    def test_bench_0018_exact_signed_solution(self) -> None:
        links = build_links()
        wrench = prescribed_wrench_for_forces(links, TARGET_FORCE_N, reference_point_m=(0.0, 0.0, 0.0))
        self.assertEqual(wrench.force_N, (-150.0, -260.0, -340.0))
        self.assertEqual(wrench.moment_Nm, (-40.0, -50.0, -60.0))

        result = solve_linkage_statics(links, wrench)
        self.assertEqual(result.status, LinkageStaticsStatus.SUCCESS)
        self.assertTrue(result.ok)
        self.assertEqual(result.link_order, ("L1", "L2", "L3", "L4", "L5", "L6"))
        for actual, expected in zip(result.axial_force_N, TARGET_FORCE_N):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertAlmostEqual(result.characteristic_length_m or 0.0, 1.0, places=12)
        self.assertAlmostEqual(result.condition_number_inf or 0.0, 4.0, places=12)
        self.assertLessEqual(result.force_residual_inf_norm_N or 0.0, 1.0e-12)
        self.assertLessEqual(result.moment_residual_inf_norm_Nm or 0.0, 1.0e-12)

    def test_action_reaction_and_compression_sign_are_preserved(self) -> None:
        target = (100.0, -25.0, 300.0, 40.0, -50.0, 60.0)
        links = build_links()
        wrench = prescribed_wrench_for_forces(links, target, reference_point_m=(0.0, 0.0, 0.0))
        result = solve_linkage_statics(links, wrench)
        self.assertTrue(result.ok, result.message)
        for force_state, expected in zip(result.link_forces, target):
            self.assertAlmostEqual(force_state.axial_force_N, expected, places=11)
            for body_component, remote_component in zip(force_state.body_force_N, force_state.remote_force_N):
                self.assertAlmostEqual(body_component + remote_component, 0.0, places=12)
        self.assertLess(result.axial_force_N[1], 0.0)
        self.assertLess(result.axial_force_N[4], 0.0)

    def test_bench_0019_reference_point_invariance(self) -> None:
        links = build_links()
        origin = (0.0, 0.0, 0.0)
        baseline_wrench = prescribed_wrench_for_forces(links, TARGET_FORCE_N, reference_point_m=origin)
        baseline = solve_linkage_statics(links, baseline_wrench)
        self.assertTrue(baseline.ok, baseline.message)

        reference_2 = (0.31, -0.17, 0.23)
        shift = _sub(origin, reference_2)
        moment_2 = _add(baseline_wrench.moment_Nm, _cross(shift, baseline_wrench.force_N))
        shifted_wrench = PrescribedExternalWrench(
            frame_id=FRAME,
            reference_point_m=reference_2,
            force_N=baseline_wrench.force_N,
            moment_Nm=moment_2,
            load_case_id="BENCH-SUSP-0019-reference",
        )
        shifted = solve_linkage_statics(links, shifted_wrench)
        self.assertTrue(shifted.ok, shifted.message)
        for actual, expected in zip(shifted.axial_force_N, baseline.axial_force_N):
            self.assertAlmostEqual(actual, expected, places=10)

    def test_bench_0019_rigid_translation_invariance(self) -> None:
        translation = (1.2, -0.8, 0.45)
        baseline_links = build_links()
        baseline_wrench = prescribed_wrench_for_forces(
            baseline_links,
            TARGET_FORCE_N,
            reference_point_m=(0.0, 0.0, 0.0),
        )
        baseline = solve_linkage_statics(baseline_links, baseline_wrench)
        self.assertTrue(baseline.ok, baseline.message)

        translated_links = build_links(translation)
        translated_wrench = PrescribedExternalWrench(
            frame_id=FRAME,
            reference_point_m=translation,
            force_N=baseline_wrench.force_N,
            moment_Nm=baseline_wrench.moment_Nm,
            load_case_id="BENCH-SUSP-0019-translation",
        )
        translated = solve_linkage_statics(translated_links, translated_wrench)
        self.assertTrue(translated.ok, translated.message)
        for actual, expected in zip(translated.axial_force_N, baseline.axial_force_N):
            self.assertAlmostEqual(actual, expected, places=10)


if __name__ == "__main__":
    unittest.main()
