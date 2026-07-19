# Data Catalog

Large files and raw telemetry are stored outside Git. Catalog entries should record:

- stable dataset ID;
- file name and cryptographic hash;
- storage location and access restriction;
- acquisition date and vehicle configuration;
- sensors, channels, units, and sample rates;
- calibration revisions;
- test maneuver and environmental conditions;
- data role: calibration, identification, validation, or regression;
- processing lineage and generated derivatives.

Raw files are immutable. Normalized or filtered datasets are new artifacts with explicit parentage.
