# WUFR-26 CAD Observations — 2026-07-21

**Status:** Source observation; selected-entity definitions remain partly unresolved  
**Scope:** `GEOMETRY FINAL.SLDPRT`, steering column sketches, rack center, nominal symmetry, and screenshot-visible dimensions

## Team-supplied statements

The team supplied the following design-source observations:

- the nominal CAD left-side hardpoints are an exact reflection of the right-side hardpoints;
- the SolidWorks setup uses the static toe and camber from `WUFR-26 FINAL 8.21.2025.xlsx`;
- the centered rack coordinate in the SolidWorks steering-study axis order is `[0.000, 162.865, -79.298] mm`;
- the inboard tie-rod pickup points are the moving rack points and translate by `1.00 in` to either side in the nominal study;
- the FDR projected full-input wheel-turn values are `22.22 deg` for the less-steered/right wheel and `32.81 deg` for the more-steered/left wheel;
- CAD angular exports are reported to use `+/-0.1 deg` tolerance;
- the reported CAD length tolerance was phrased as `+/-0.005 thou` and needs exact unit confirmation;
- the intended model use is future steering-system development, not retrospective as-built certification.

## General steering-geometry screenshot

The general 3D screenshot shows the rack, tie rods, steering-column path, front and right reference planes, and several dimension callouts. Legible values include approximately:

- `330.20 mm` on the long tie-rod/steering geometry region;
- `159.55 mm` and `79.30 mm` near the rack/plane region;
- `50.80 mm` near the upper steering-column or steering-wheel region;
- angular callouts near `27.640 deg` and `69.85 deg`;
- additional overlapping values near the rack and intermediate column joints that cannot be assigned unambiguously from the screenshot alone.

The screenshot is useful for topology and rough packaging confirmation, but the selected entities and projection directions for several dimensions are not visible. Those values are not promoted to active parameters.

## Upper steering-column screenshot

The upper-column screenshot clearly shows the following callout values:

- `269.65 mm` along the main upper-column bounding dimension;
- `57.91 mm` near the lower end of that bounding construction;
- `50.80 mm` near the upper end;
- `6.35 mm` near the upper shaft/offset feature.

The screenshot also shows the upper-column quadrilateral, a center/intermediate joint, a long segment to the right-side assembly, and the steering-wheel bounding construction. The exact selected entities for `50.80 mm`, `57.91 mm`, and `6.35 mm` are not sufficiently explicit to assign them as shaft diameter, offset, or packaging-envelope values without a named sketch or dimension export.

## Feature-tree screenshot

The supplied SolidWorks tree shows:

- `GEOMETRY FINAL ->?`;
- a `Steering Geometry` folder;
- `Column ->?`;
- `3D (-) Full Steering`;
- `3D (-) Front Axel`;
- `3D (-) Rack ACTUAL`;
- `3D (-) Tie Rod ACTUAL`.

This confirms the named geometry sketches and that the current part contains explicit `Rack ACTUAL` and `Tie Rod ACTUAL` constructions. The screenshot does not show the ConfigurationManager tab or a textual active-configuration name. The meaning of the visible `->?` indicators is therefore recorded as unresolved rather than interpreted as a specific warning state.

## Model-use disposition

The rack/tie-rod geometry and wheel-plane response evidence are sufficient for the frozen nominal rigid model. The steering-column and steering-wheel screenshot dimensions are retained as packaging observations only. They should become active parameters only after the corresponding sketch, selected entities, direction, and tolerance are exported or documented.

## Requested follow-up when convenient

The most useful future CAD export would be a small table containing:

- dimension name;
- value and unit;
- two selected entities or reference points;
- direction or projection plane;
- configuration name;
- whether the dimension is driving, driven, or reference-only.

No additional CAD work is required for the current Level E freeze.
