"""Generate a lightweight browser viewer for an :class:`EngineeringScene`.

The viewer is intentionally a display client.  Solved state coordinates are embedded
into the generated HTML; JavaScript changes visibility/camera/state only and performs
no engineering calculations.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

from .scene3d import EngineeringScene

_THREE_VERSION_RE = re.compile(r"^0\.[0-9]+\.[0-9]+$")
DEFAULT_THREE_VERSION = "0.185.1"


def render_scene_viewer_html(
    scene: EngineeringScene,
    path: str | Path,
    *,
    three_version: str = DEFAULT_THREE_VERSION,
) -> Path:
    """Write a self-contained scene document with a pinned external Three.js module.

    The engineering scene JSON is embedded directly so the HTML can be opened from a
    local file without a separate local web server.  Three.js itself is loaded from a
    version-pinned jsDelivr URL; the generated page therefore needs network access to
    that module unless a future packaging layer vendors it explicitly.
    """

    if not _THREE_VERSION_RE.fullmatch(three_version):
        raise ValueError("three_version must be an explicit 0.x.y version")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(scene.canonical_payload(), ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    html = _HTML_TEMPLATE.replace("__THREE_VERSION__", three_version).replace(
        "__SCENE_JSON__", payload
    )
    output.write_text(html, encoding="utf-8")
    return output


_HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>PSSD engineering 3D viewer</title>
<style>
:root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; background: #0b0f14; color: #e5e7eb; overflow: hidden; }
#app { display: grid; grid-template-columns: minmax(0, 1fr) 330px; width: 100vw; height: 100vh; }
#viewport { position: relative; min-width: 0; background: radial-gradient(circle at 50% 35%, #17202b, #090d12 70%); }
canvas { display: block; width: 100%; height: 100%; }
#panel { overflow-y: auto; border-left: 1px solid #263241; padding: 18px 18px 28px; background: #10161e; }
h1 { font-size: 18px; line-height: 1.25; margin: 0 0 6px; }
.subtle { color: #9ca3af; font-size: 12px; line-height: 1.45; }
.section { border-top: 1px solid #263241; margin-top: 16px; padding-top: 14px; }
.section h2 { font-size: 13px; margin: 0 0 10px; text-transform: uppercase; letter-spacing: .06em; color: #cbd5e1; }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
button { background: #1c2734; color: #e5e7eb; border: 1px solid #344356; border-radius: 6px; padding: 6px 9px; cursor: pointer; }
button:hover { background: #263547; }
input[type="range"] { width: 100%; }
.layer { display: flex; align-items: center; gap: 8px; margin: 7px 0; font-size: 13px; }
.scalar { display: grid; grid-template-columns: 1fr auto; gap: 8px; font-size: 12px; margin: 5px 0; }
.scalar .symbol { font-family: "STIX Two Math", "Cambria Math", serif; color: #dbeafe; }
.element { font-size: 12px; margin: 4px 0; color: #bac4d1; }
.symbol { font-family: "STIX Two Math", "Cambria Math", serif; }
#state-label { font-weight: 650; margin: 8px 0 3px; }
#warning { position: absolute; inset: 16px auto auto 16px; max-width: min(640px, 80%); background: #441b1b; color: #fecaca; border: 1px solid #7f1d1d; border-radius: 8px; padding: 10px 12px; display: none; z-index: 2; }
#status { position: absolute; left: 14px; bottom: 12px; font-size: 11px; color: #cbd5e1; background: rgba(8, 12, 17, .72); padding: 6px 8px; border-radius: 5px; pointer-events: none; }
.note { font-size: 11px; line-height: 1.45; color: #9ca3af; margin: 6px 0; }
@media (max-width: 800px) { #app { grid-template-columns: 1fr; grid-template-rows: 65vh 35vh; } #panel { border-left: 0; border-top: 1px solid #263241; } }
</style>
</head>
<body>
<div id="app">
  <div id="viewport"><div id="warning"></div><div id="status"></div></div>
  <aside id="panel">
    <h1 id="title"></h1>
    <div class="subtle" id="identity"></div>

    <div class="section">
      <h2>State</h2>
      <input id="state-slider" type="range" min="0" step="1" value="0" />
      <div id="state-label"></div>
      <div class="subtle" id="state-symbol"></div>
      <div id="state-scalars"></div>
    </div>

    <div class="section">
      <h2>Camera</h2>
      <div class="row">
        <button data-camera="iso">Isometric</button>
        <button data-camera="top">Top (+z)</button>
        <button data-camera="front">Front (+x)</button>
        <button data-camera="side">Side (-y)</button>
      </div>
      <p class="note">Drag to orbit. Mouse wheel changes camera distance. Canonical body axes are +x forward, +y vehicle left, +z upward.</p>
    </div>

    <div class="section">
      <h2>Layers</h2>
      <div id="layers"></div>
    </div>

    <div class="section">
      <h2>Engineering primitives</h2>
      <div id="elements"></div>
    </div>

    <div class="section">
      <h2>Authority / notes</h2>
      <div class="note" id="authority"></div>
      <div id="notes"></div>
    </div>
  </aside>
</div>
<script type="module">
import * as THREE from "https://cdn.jsdelivr.net/npm/three@__THREE_VERSION__/build/three.module.js";

const sceneData = __SCENE_JSON__;
const viewport = document.getElementById("viewport");
const warning = document.getElementById("warning");
const status = document.getElementById("status");
const metadata = sceneData.metadata;

document.getElementById("title").textContent = metadata.title;
document.getElementById("identity").textContent = `${metadata.scene_id} · ${metadata.model_id} · ${metadata.configuration_id}`;
document.getElementById("authority").textContent = metadata.authority;
for (const note of metadata.notes) {
  const p = document.createElement("p"); p.className = "note"; p.textContent = note;
  document.getElementById("notes").appendChild(p);
}

const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
viewport.prepend(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.001, 100);
camera.up.set(0, 0, 1);

const layerColors = {
  body_frame: 0xd7dee8,
  rack: 0xf2c14e,
  tie_rods: 0x7dd3fc,
  steering_axes: 0xf59e9e,
};
const layerGroups = new Map();
for (const layer of sceneData.layers) {
  const group = new THREE.Group(); group.name = layer.layer_id; group.visible = layer.visible_by_default;
  layerGroups.set(layer.layer_id, group); scene.add(group);
  const label = document.createElement("label"); label.className = "layer";
  const input = document.createElement("input"); input.type = "checkbox"; input.checked = layer.visible_by_default;
  input.addEventListener("change", () => { group.visible = input.checked; });
  const span = document.createElement("span"); span.textContent = layer.label;
  label.append(input, span); document.getElementById("layers").appendChild(label);
}

const pointBase = new Map(sceneData.points.map(p => [p.point_id, new THREE.Vector3(...p.coordinates)]));
const pointObjects = new Map();
const pointRadius = 0.007;
for (const point of sceneData.points) {
  const geometry = new THREE.SphereGeometry(pointRadius, 18, 12);
  const material = new THREE.MeshBasicMaterial({color: layerColors[point.layer_id] ?? 0xd1d5db});
  const mesh = new THREE.Mesh(geometry, material); mesh.position.copy(pointBase.get(point.point_id));
  mesh.userData = point; pointObjects.set(point.point_id, mesh); layerGroups.get(point.layer_id).add(mesh);
}

function segmentColor(segment) {
  if (segment.segment_id === "BODY_X") return 0xef4444;
  if (segment.segment_id === "BODY_Y") return 0x22c55e;
  if (segment.segment_id === "BODY_Z") return 0x3b82f6;
  return layerColors[segment.layer_id] ?? 0xd1d5db;
}

const segmentObjects = new Map();
function makeLine(start, end, color) {
  const geometry = new THREE.BufferGeometry().setFromPoints([start, end]);
  return new THREE.Line(geometry, new THREE.LineBasicMaterial({color}));
}
function makeArrow(start, end, color) {
  const direction = end.clone().sub(start); const length = direction.length();
  if (length < 1e-12) direction.set(1,0,0); else direction.normalize();
  return new THREE.ArrowHelper(direction, start, Math.max(length, 1e-12), color, Math.min(length * 0.18, 0.025), Math.min(length * 0.08, 0.012));
}
for (const segment of sceneData.segments) {
  const start = pointBase.get(segment.start_point_id).clone();
  const end = pointBase.get(segment.end_point_id).clone();
  const object = segment.render_kind === "arrow" ? makeArrow(start, end, segmentColor(segment)) : makeLine(start, end, segmentColor(segment));
  object.userData = segment; segmentObjects.set(segment.segment_id, object); layerGroups.get(segment.layer_id).add(object);
}

for (const axis of sceneData.axes) {
  const p = new THREE.Vector3(...axis.point); const d = new THREE.Vector3(...axis.direction).normalize();
  const start = p.clone().addScaledVector(d, -axis.display_half_length);
  const end = p.clone().addScaledVector(d, axis.display_half_length);
  const line = makeLine(start, end, layerColors[axis.layer_id] ?? 0xd1d5db);
  line.material.transparent = true; line.material.opacity = 0.62;
  line.userData = axis; layerGroups.get(axis.layer_id).add(line);
}

const allPositions = [];
for (const point of sceneData.points) allPositions.push(new THREE.Vector3(...point.coordinates));
for (const stateDef of sceneData.states) for (const override of stateDef.point_overrides) allPositions.push(new THREE.Vector3(...override.coordinates));
for (const axis of sceneData.axes) {
  const p = new THREE.Vector3(...axis.point); const d = new THREE.Vector3(...axis.direction).normalize();
  allPositions.push(p.clone().addScaledVector(d, -axis.display_half_length));
  allPositions.push(p.clone().addScaledVector(d, axis.display_half_length));
}
const bounds = new THREE.Box3().setFromPoints(allPositions);
const target = bounds.getCenter(new THREE.Vector3());
const size = bounds.getSize(new THREE.Vector3());
const extent = Math.max(size.x, size.y, size.z, 0.25);
let cameraRadius = extent * 1.9;
let azimuth = -Math.PI * 0.55;
let elevation = Math.PI * 0.24;

const grid = new THREE.GridHelper(Math.max(2.0, extent * 2.5), 20, 0x52606f, 0x2a3542);
grid.rotation.x = Math.PI / 2; grid.position.z = 0; scene.add(grid);

function positionCamera() {
  const ce = Math.cos(elevation);
  camera.position.set(
    target.x + cameraRadius * ce * Math.cos(azimuth),
    target.y + cameraRadius * ce * Math.sin(azimuth),
    target.z + cameraRadius * Math.sin(elevation),
  );
  camera.lookAt(target);
}
function setCameraPreset(name) {
  if (name === "top") { azimuth = 0; elevation = Math.PI / 2 - 0.001; }
  if (name === "front") { azimuth = 0; elevation = 0.001; }
  if (name === "side") { azimuth = -Math.PI / 2; elevation = 0.001; }
  if (name === "iso") { azimuth = -Math.PI * 0.55; elevation = Math.PI * 0.24; }
  cameraRadius = extent * 1.9; positionCamera();
}
for (const button of document.querySelectorAll("button[data-camera]")) button.addEventListener("click", () => setCameraPreset(button.dataset.camera));

let dragging = false, lastX = 0, lastY = 0;
renderer.domElement.addEventListener("pointerdown", event => { dragging = true; lastX = event.clientX; lastY = event.clientY; renderer.domElement.setPointerCapture(event.pointerId); });
renderer.domElement.addEventListener("pointerup", event => { dragging = false; renderer.domElement.releasePointerCapture(event.pointerId); });
renderer.domElement.addEventListener("pointermove", event => {
  if (!dragging) return;
  azimuth -= (event.clientX - lastX) * 0.006;
  elevation = Math.max(-Math.PI * 0.48, Math.min(Math.PI * 0.48, elevation + (event.clientY - lastY) * 0.005));
  lastX = event.clientX; lastY = event.clientY; positionCamera();
});
renderer.domElement.addEventListener("wheel", event => { event.preventDefault(); cameraRadius *= Math.exp(event.deltaY * 0.001); cameraRadius = Math.max(extent * 0.25, Math.min(extent * 8, cameraRadius)); positionCamera(); }, {passive:false});

function updateSegmentGeometry(segment) {
  const object = segmentObjects.get(segment.segment_id);
  const start = pointObjects.get(segment.start_point_id).position.clone();
  const end = pointObjects.get(segment.end_point_id).position.clone();
  if (segment.render_kind === "arrow") {
    const direction = end.clone().sub(start); const length = direction.length();
    if (length > 1e-12) { object.position.copy(start); object.setDirection(direction.normalize()); object.setLength(length, Math.min(length * 0.18, 0.025), Math.min(length * 0.08, 0.012)); }
  } else {
    object.geometry.setFromPoints([start, end]); object.geometry.attributes.position.needsUpdate = true;
  }
}

const slider = document.getElementById("state-slider");
slider.max = Math.max(0, sceneData.states.length - 1);
slider.value = sceneData.states.findIndex(s => Math.abs(s.parameter_value) < 1e-12) >= 0 ? sceneData.states.findIndex(s => Math.abs(s.parameter_value) < 1e-12) : 0;

function formatScalar(scalar) {
  const value = Math.abs(scalar.value) < 1e-10 ? "0" : scalar.value.toFixed(Math.abs(scalar.value) >= 100 ? 1 : 4).replace(/0+$/, "").replace(/\.$/, "");
  return `${value} ${scalar.unit}`;
}
function applyState(index) {
  const stateDef = sceneData.states[index];
  for (const point of sceneData.points) pointObjects.get(point.point_id).position.copy(pointBase.get(point.point_id));
  for (const override of stateDef.point_overrides) pointObjects.get(override.point_id).position.set(...override.coordinates);
  for (const segment of sceneData.segments) updateSegmentGeometry(segment);
  document.getElementById("state-label").textContent = stateDef.label;
  document.getElementById("state-symbol").innerHTML = `<span class="symbol">${stateDef.parameter_symbol}</span> · ${stateDef.parameter_label}`;
  const scalars = document.getElementById("state-scalars"); scalars.innerHTML = "";
  for (const scalar of stateDef.scalars) {
    const row = document.createElement("div"); row.className = "scalar";
    const lhs = document.createElement("div"); lhs.innerHTML = `<span class="symbol">${scalar.symbol}</span> · ${scalar.label}`;
    const rhs = document.createElement("div"); rhs.textContent = formatScalar(scalar);
    row.append(lhs, rhs); scalars.appendChild(row);
  }
  if (stateDef.status !== "valid") { warning.style.display = "block"; warning.textContent = `STATE ${stateDef.status.toUpperCase()}: ${stateDef.message}`; }
  else warning.style.display = "none";
  status.textContent = `${metadata.frame_id} · ${metadata.axis_convention} · Three.js __THREE_VERSION__`;
}
slider.addEventListener("input", () => applyState(Number(slider.value)));

const elementRoot = document.getElementById("elements");
for (const item of [...sceneData.segments, ...sceneData.axes]) {
  const div = document.createElement("div"); div.className = "element";
  const symbol = item.symbol ? `<span class="symbol">${item.symbol}</span> · ` : "";
  div.innerHTML = `${symbol}${item.label}`; elementRoot.appendChild(div);
}

function resize() {
  const width = viewport.clientWidth, height = viewport.clientHeight;
  renderer.setSize(width, height, false); camera.aspect = width / Math.max(height, 1); camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewport); resize(); positionCamera(); applyState(Number(slider.value));

function animate() { requestAnimationFrame(animate); renderer.render(scene, camera); }
animate();
</script>
</body>
</html>
'''
