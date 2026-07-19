# Registry

The registry is the machine-readable model-assurance source of truth.

## Record layout

Records live under `registry/records/<type>/` and use TOML. Each file contains a `[record]` table. File names should match the stable record ID.

## Required concepts

- `status` describes whether the record is currently used.
- `disposition` describes the audit decision.
- `maturity` describes evidence and verification depth.
- `verification_level` describes the strongest completed verification layer.
- `affected_ids` and other ID lists form the dependency graph.

## Editing rules

- Never recycle an ID.
- Preserve deprecated records.
- Add provenance rather than overwriting conflicting observations.
- Keep human-readable explanation with machine-readable fields.
- Update benchmarks and migration records when implementation behavior changes.
