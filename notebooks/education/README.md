# Vehicle Dynamics Education Notebooks

These notebooks are the teaching/front-end layer for the WashU Racing vehicle-dynamics model. They are not a second physics codebase.

## Contract

- **Notebooks explain and orchestrate; `src/` owns reusable physics.**
- Derive the governing relationship by hand before relying on a shared model call.
- Keep one transparent calculation in the notebook and correlate it against the reusable implementation when that implementation exists.
- Do not duplicate reviewed vehicle constants in notebooks. Load them through source selectors and production provider loaders.
- Preserve units, frame conventions, state identity, assumptions, and authority boundaries from the underlying repository records.
- Add widgets only when changing a parameter materially improves physical intuition. Whiteboardable calculations remain the default.
- Quantitative figures should use the same naming, units, and provenance conventions as `pssd_viz`. Do not create a separate educational plotting standard.
- Commit notebooks with outputs cleared so review diffs remain readable and deterministic.

## Notebook sequence

`00_course_setup.ipynb` establishes the environment, reviewed WUFR-27 reference state, coordinate convention, and the derive -> explicit calculation -> shared model -> correlation workflow.

`01_contact_patch.ipynb` applies that workflow to the complete-car free-body diagram, static front/rear axle-load derivation, reviewed scale-state consistency check, limiting cases, and the first lateral-force demand calculation.

Later lesson notebooks should use two-digit ordering and one physical question per file:

```text
00_course_setup.ipynb
01_contact_patch.ipynb
02_tire_lateral_force.ipynb
03_load_sensitivity_camber.ipynb
...
```

The codebase expands across the year; the notebooks remain small lesson-specific views over it.

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[education]"
jupyter lab
```

Run the repository checks separately:

```bash
python scripts/validate_registry.py
python -m unittest discover -s tests
```

## Source selector

The education notebooks start from:

```text
configurations/education/WUFR27_EDUCATION_BASELINE_V0.toml
```

That file intentionally contains no duplicated mass, CG, track, or wheelbase values. It points at reviewed source records. `pssd_vehicle.load_vehicle_reference(...)` loads those records through their existing provider loaders and exposes only the small read-only surface needed by early lessons.

When a later lesson needs tire, suspension, steering, aero, or damper data, extend the model only as far as that lesson requires.
