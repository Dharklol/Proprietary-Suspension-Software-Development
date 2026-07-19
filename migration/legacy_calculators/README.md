# Legacy Calculator Migration

## Workflow

1. Inventory every sheet, table, formula block, lookup, macro, hidden constant, and external reference.
2. Map every input and output to a canonical quantity or mark it ambiguous.
3. Record equations, assumptions, units, signs, and source authority.
4. Reproduce the legacy output as a benchmark before changing the physics.
5. Assign a disposition and replacement path.
6. Preserve the original artifact and record its hash/revision.
7. Add tests that explain expected agreement or intentional disagreement.

## Initial targets

- `Suspension Calculations 2026`
- `LLTD Calculator`
- chassis/upright/linkage load calculators
- steering and tie-rod optimization calculators
- brake and aerodynamic-load calculations that feed suspension results
