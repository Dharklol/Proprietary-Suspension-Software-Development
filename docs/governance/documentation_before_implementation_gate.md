# Documentation-Before-Implementation Gate

**Status:** Adopted for Phase 0  
**Applies to:** Vehicle-dynamics physics, calculator migration, canonical schema, telemetry-derived engineering quantities, and optimization objectives

## Rule

No legacy physics block is implemented in the production package until its documentation packet has been reviewed.

A documentation packet contains:

1. source identity and migration ID;
2. canonical quantities and definitions;
3. governing equation or algorithm;
4. units, frames, signs, and reference points;
5. parameter sources and uncertainty;
6. assumptions and validity envelope;
7. numerical behavior and failure cases;
8. dependencies;
9. preliminary disposition;
10. verification plan.

Scaffolding that only supports documentation, registry storage, validation of registry structure, or file import metadata is permitted. Physics outputs, design recommendations, and optimizers are not.

## Why this gate exists

Copying formulas before resolving definitions creates an implementation that is easier to trust than it deserves. It also makes later corrections expensive because the software interface begins to depend on accidental spreadsheet terminology and structure.

## Exit condition

A physics block may enter implementation when:

- all critical quantities have stable canonical IDs;
- unresolved conflicts are either closed or represented as explicit selectable model variants;
- the equation source and derivation are recorded;
- the intended fidelity and applicability are stated;
- verification cases exist before or alongside implementation;
- the migration disposition is approved.

## Change control

A later discovery that changes a definition, equation, or applicability range reopens the documentation gate for the affected model and downstream dependents. Existing results remain reproducible under their original model revision.
