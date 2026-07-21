# Measurement Schema Versioning Policy

- Patch changes clarify documentation or validation messages without changing accepted files.
- Minor changes add optional files or backward-compatible fields with explicit defaults.
- Major changes rename/remove columns, change units or meanings, or alter required relationships.
- Every semantic schema change requires validator tests, migration guidance, and a changelog entry.
- Raw data are never rewritten merely to match a new schema. A converted package references the original source and records the conversion code revision.
