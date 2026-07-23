# External Suspension-Pose Source Audit

**Scope:** nonphysical source discovery for the steering suspension-pose provider.

## Required source

The steering optimizer requires a machine-readable series of left/right upright rigid transforms relative to the nominal upright reference pose. The source must represent suspension motion **before tie-rod-induced steering rotation is resolved** and must identify:

- state coordinates and units;
- source revision;
- source coordinate frame and handedness;
- translation and rotation conventions;
- left/right upright transforms;
- whether steering/tie-rod closure is already present;
- review authority.

A toe curve, camber curve, wheel-center displacement table, or already-steered upright orientation is not by itself this source.

## Team sources located

### 2026 Suspension Design Binder

- Google Drive ID: `1QjUfQWjII9rNlr8_E_wqP9NjUsBDuH-M5wquw4ZnZec`
- Role: descriptive design evidence.
- Relevant finding: the binder states that suspension/steering geometry and tie-rod pickup work used SolidWorks motion studies.
- Disposition: useful for identifying likely source lineage, but no reviewed machine-readable zero-steer upright transform series was recovered from the Drive search performed for this implementation.

### Kinematics Validation TRR

- Google Drive ID: `1V4eWwE49s16vMrV9NQ1U9VaELbgXJu_7j2kY4zDxBas`
- Role: historical validation-plan evidence.
- Relevant finding: the test plan compares measured toe/camber through suspension travel against simulated kinematics; related copies explicitly mention simulation software such as OptimumK.
- Disposition: establishes historical use of simulation for kinematics comparison, but the test document and validation data are not the required unresolved-steering upright transform input.

### Kinematics Validation Data Sheet

- Google Drive IDs surfaced during discovery include `1yiAEeKErDLKU-yRsQjzgothDo_en_LL-cYwBfvKsVN4` and `1E8AqIWk0qXePU_fGp8Td6g7waSFzZh0jpjj3MkT89yo`.
- Role: historical physical/validation evidence.
- Disposition: explicitly excluded from the present development path because physical correlation is deferred and because measured toe/camber does not define the unresolved zero-steer upright rigid transform required by `MOD-STEER-0002`.

## Current conclusion

As of the PR #26 source audit, **no reviewed machine-readable WUFR zero-steer upright transform series has been identified** in the searched project Drive material.

This does not block the steering software architecture. PR #26 therefore implements a canonical external exchange adapter and proves that an external rigid-transform table can reproduce the existing canonical pose contract exactly. The fixture remains synthetic software evidence.

## Acceptable future source routes

A later source can be promoted after review through any of these paths:

1. SolidWorks motion export converted to the canonical exchange table;
2. OptimumK output or a companion export that provides sufficient upright pose geometry to reconstruct the rigid transforms without importing tie-rod steering twice;
3. a reviewed explicit lookup table generated from the WUFR suspension model;
4. a future native suspension solver implementing the same provider contract.

The source-specific exporter or converter must document its own coordinate conversion. The steering package will not contain hidden vendor-specific frame assumptions.

## Promotion gate

A WUFR pose set may be used for design ranking only after its source path/revision, frame conversion, steering-DOF treatment, nominal-state identity, and at least one independent reconstruction check are reviewed. Until then, imported external fixtures remain software integration evidence only.
