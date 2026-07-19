# Contributing

## Workflow

- Create a focused branch from `main`.
- Make changes through a pull request.
- Link every implementation change to the affected registry IDs.
- Do not merge while required registry validation or benchmark checks fail.

## Stable identifiers

Use the following prefixes:

| Type | Prefix |
|---|---|
| Quantity | `QTY` |
| Equation | `EQ` |
| Model | `MOD` |
| Parameter | `PAR` |
| Sensor | `SNS` |
| Channel | `CH` |
| Assumption | `ASM` |
| Risk | `RISK` |
| Benchmark | `BENCH` |
| Migration item | `MIG` |

IDs are permanent. Do not recycle deleted or deprecated IDs.

## Definition of done for model work

A model change is not complete until the following are recorded where applicable:

- canonical quantity definitions;
- source and derivation;
- coordinate frames, reference points, units, and signs;
- assumptions and validity envelope;
- parameter provenance and uncertainty;
- numerical method and convergence criteria;
- analytical, limiting-case, or benchmark tests;
- downstream dependencies;
- migration impact and release notes.

## Data handling

Do not commit raw telemetry, large binary exports, private credentials, or licensed reference material. Add a catalog record containing the file hash, location, format, acquisition context, and access restrictions instead.

## Review expectations

Reviewers should challenge definitions and assumptions before debating numerical precision. Plausible output is not evidence of correctness.
