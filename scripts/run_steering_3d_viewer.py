#!/usr/bin/env python3
"""Generate the WUFR-27 rigid steering engineering scene and browser viewer."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from pssd_steering import load_geometry
from pssd_viz import sha256_file, write_scene_json
from pssd_viz.steering_scene import build_steering_engineering_scene
from pssd_viz.viewer3d import DEFAULT_THREE_VERSION, render_scene_viewer_html


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
INHERITED_PATH = ROOT / "configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("steering_3d_viewer"))
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)

    geometry = load_geometry(BASELINE_PATH)
    scene = build_steering_engineering_scene(geometry)
    scene = replace(
        scene,
        metadata=replace(
            scene.metadata,
            source_ids=(
                BASELINE_PATH.relative_to(ROOT).as_posix(),
                INHERITED_PATH.relative_to(ROOT).as_posix(),
            ),
        ),
    )
    scene_path = write_scene_json(scene, arguments.output_dir / "scene.json")
    viewer_path = render_scene_viewer_html(scene, arguments.output_dir / "viewer.html")

    manifest = {
        "schema": "pssd.engineering_scene_manifest/v0.1.0",
        "scene_id": scene.metadata.scene_id,
        "scene_fingerprint_sha256": scene.fingerprint(),
        "viewer": {
            "technology": "Three.js browser viewer",
            "three_version": DEFAULT_THREE_VERSION,
            "physics_computation_in_viewer": False,
            "network_requirement": (
                "viewer.html embeds scene data but loads the pinned Three.js module from jsDelivr"
            ),
        },
        "terminology_policy": {
            "body_axes": "x_B, y_B, z_B",
            "rack_displacement": "x_r",
            "upright_rotation": "theta_u,L and theta_u,R (rendered with Greek theta)",
            "tie_rod_length": "L_tr,L and L_tr,R",
            "closure_residual": "Delta L_tr,L and Delta L_tr,R (rendered with Greek delta)",
        },
        "artifacts": [
            {
                "path": scene_path.name,
                "sha256": sha256_file(scene_path),
                "size_bytes": scene_path.stat().st_size,
            },
            {
                "path": viewer_path.name,
                "sha256": sha256_file(viewer_path),
                "size_bytes": viewer_path.stat().st_size,
            },
        ],
        "authority": scene.metadata.authority,
    }
    manifest_path = arguments.output_dir / "viewer.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
