"""Tests for the provider-neutral 3D scene contract and steering viewer adapter."""

from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
import unittest

from pssd_steering import load_geometry
from pssd_viz.scene3d import (
    EngineeringScene,
    SceneContractError,
    SceneLayer,
    SceneMetadata,
    ScenePoint,
    SceneSegment,
    SceneState,
    write_scene_json,
)
from pssd_viz.steering_scene import build_steering_engineering_scene
from pssd_viz.viewer3d import DEFAULT_THREE_VERSION, render_scene_viewer_html


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"


class SceneContractTests(unittest.TestCase):
    def _minimal_scene(self) -> EngineeringScene:
        return EngineeringScene(
            metadata=SceneMetadata(
                scene_id="SCENE-TEST-001",
                title="Scene test",
                frame_id="BODY",
                length_unit="m",
                axis_convention="+x forward, +y left, +z up",
                configuration_id="TEST",
                model_id="MODEL",
                authority="test only",
            ),
            layers=(SceneLayer("geometry", "Geometry"),),
            points=(
                ScenePoint("A", "point A", (0.0, 0.0, 0.0), "geometry", symbol="A"),
                ScenePoint("B", "point B", (1.0, 0.0, 0.0), "geometry", symbol="B"),
            ),
            segments=(SceneSegment("AB", "segment AB", "A", "B", "geometry"),),
            states=(
                SceneState(
                    "center",
                    "center",
                    "Rack displacement",
                    "x_r",
                    0.0,
                    "mm",
                ),
            ),
        )

    def test_fingerprint_and_json_are_deterministic(self) -> None:
        first = self._minimal_scene()
        second = self._minimal_scene()
        self.assertEqual(first.fingerprint(), second.fingerprint())
        with tempfile.TemporaryDirectory() as temporary:
            path = write_scene_json(first, Path(temporary) / "scene.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "pssd.engineering_scene/v0.1.0")
        self.assertEqual(payload["metadata"]["scene_id"], "SCENE-TEST-001")

    def test_unknown_segment_point_is_rejected(self) -> None:
        with self.assertRaises(SceneContractError):
            EngineeringScene(
                metadata=self._minimal_scene().metadata,
                layers=(SceneLayer("geometry", "Geometry"),),
                points=(ScenePoint("A", "A", (0.0, 0.0, 0.0), "geometry"),),
                segments=(SceneSegment("AB", "AB", "A", "B", "geometry"),),
            )


class SteeringSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_geometry(BASELINE_PATH)
        cls.scene = build_steering_engineering_scene(cls.geometry)

    def test_scene_preserves_canonical_axes_and_standard_symbols(self) -> None:
        self.assertEqual(self.scene.metadata.frame_id, "CANONICAL_ISO8855_BODY")
        self.assertIn("+x forward", self.scene.metadata.axis_convention)
        symbols = {item.symbol for item in self.scene.segments}
        self.assertTrue({"x_B", "y_B", "z_B", "L_tr,L", "L_tr,R"}.issubset(symbols))
        axis_symbols = {item.symbol for item in self.scene.axes}
        self.assertTrue({"e_r", "k_s,L", "k_s,R"}.issubset(axis_symbols))
        self.assertTrue(all(state.parameter_symbol == "x_r" for state in self.scene.states))

    def test_center_and_endpoint_states_are_explicit_and_valid(self) -> None:
        self.assertEqual(len(self.scene.states), 9)
        center = next(state for state in self.scene.states if state.state_id == "rack_center")
        self.assertAlmostEqual(center.parameter_value, 0.0)
        self.assertEqual(center.status, "valid")
        self.assertEqual(self.scene.states[0].status, "valid")
        self.assertEqual(self.scene.states[-1].status, "valid")

    def test_state_tie_rod_lengths_match_reviewed_geometry(self) -> None:
        for state in self.scene.states:
            overrides = dict(state.point_overrides)
            self.assertIn("RACK_IN_L", overrides)
            self.assertIn("RACK_IN_R", overrides)
            self.assertIn("TIEROD_OUT_L", overrides)
            self.assertIn("TIEROD_OUT_R", overrides)
            for side, expected in (
                ("L", self.geometry.left.tie_rod_length),
                ("R", self.geometry.right.tie_rod_length),
            ):
                inner = overrides[f"RACK_IN_{side}"]
                outer = overrides[f"TIEROD_OUT_{side}"]
                actual = math.sqrt(sum((a - b) ** 2 for a, b in zip(inner, outer)))
                self.assertAlmostEqual(actual, expected, places=9)

    def test_viewer_html_embeds_scene_without_physics_solver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = render_scene_viewer_html(self.scene, Path(temporary) / "viewer.html")
            content = path.read_text(encoding="utf-8")
        self.assertIn(self.scene.metadata.scene_id, content)
        self.assertIn(f"three@{DEFAULT_THREE_VERSION}/build/three.module.js", content)
        self.assertIn("x_r", content)
        self.assertIn("θ_u,L", content)
        self.assertNotIn("__SCENE_JSON__", content)
        self.assertNotIn("solve_corner_position", content)
        self.assertNotIn("closure_squared_residual", content)

    def test_wheel_centres_are_not_invented(self) -> None:
        point_ids = {point.point_id for point in self.scene.points}
        self.assertFalse(any("WHEEL_CENTER" in point_id for point_id in point_ids))
        self.assertTrue(any("Wheel centres" in note for note in self.scene.metadata.notes))


if __name__ == "__main__":
    unittest.main()
