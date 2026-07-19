# Steering Source-Recovery Log

**Status:** Active  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-EXT-0001` through `CAT-EXT-0004`, `CAT-EXT-0016`, `CAT-EXT-0025`

## Purpose

This log records actual searches and recovered steering artifacts separately from the recovery backlog. It prevents a similarly named file, copied curve, screenshot, or remembered value from being treated as the original source.

## Evidence-state vocabulary

- **Not searched:** no documented search has been performed.
- **Search attempted:** one or more locations were searched, but completeness is not established.
- **Candidate located:** a possibly relevant artifact was found; identity and lineage remain unverified.
- **Export recovered:** a derived table, screenshot, or report exists, but the generating model is missing.
- **Source recovered:** original bytes and required metadata are catalogued.
- **Benchmark frozen:** a versioned extract with parent hash and expected outputs is approved.
- **Formally unavailable:** required locations and responsible reviewers have completed and documented the search.

## Search record

### Search `SRCH-STEER-0001`

- **Date:** 2026-07-18
- **Performed by:** project documentation agent
- **Locations attempted:** indexed project sources available to ChatGPT; GitHub repository; direct Google Drive connector invocation
- **Queries:** `tie rod`, `tie rod length`, `C-factor`, `steering optimizer`, `Ackermann motion study`, `Steer Ratio`, `SolidWorks design study`, `WUFR-24`, `WUFR-25`, `WUFR-26`
- **Result:** no exact legacy tie-rod optimizer or original steering CAD assembly/motion-study definition was located in the indexed project source search.
- **Known evidence found:**
  - `Suspension Calculations 2026` contains imported WUFR-24/WUFR-25 steering-study tables and polynomial fits;
  - the Ackermann sheet contains historical WUFR-24/WUFR-25/WUFR-26 values;
  - the repository contains the structural inventory and transition specification;
  - literature sources describe rack-and-tie-rod geometry but are not team-design evidence.
- **Limitation:** the direct Google Drive search action was unavailable during this attempt. This search does not establish that the artifacts are absent from Drive, Box, team computers, or CAD storage.
- **Disposition:** `Search attempted`; continue with team-assisted artifact names and storage paths.

## Artifact-specific status

| Catalog ID | Artifact | Current state | Evidence presently available | Next recovery action |
|---|---|---|---|---|
| `CAT-EXT-0001` | Legacy tie-rod-length optimizer | Search attempted | Team description of inputs, sweeps, and tie-rod-length output | Obtain exact filename, tool type, author, storage path, and a copy of original bytes |
| `CAT-EXT-0002` | WUFR-24 steering CAD motion study | Export recovered | Pasted design-study table in `Steer Ratio` | Recover CAD assembly/configuration and study definition |
| `CAT-EXT-0003` | WUFR-25 steering CAD motion study | Export recovered | Pasted design-study table in `Steer Ratio` | Recover CAD assembly/configuration and study definition |
| `CAT-EXT-0004` | WUFR-26 steering study or measurement | Candidate evidence only | Historical values in `Ackerman Steering` | Identify whether values came from CAD, setup measurement, or calculation |
| `CAT-EXT-0016` | Steering geometry source | Search attempted | Spreadsheet values and team knowledge | Recover hardpoint export, drawing, CAD revision, or measurement record |
| `CAT-EXT-0025` | Physical steering sweep | Not searched in team storage | No confirmed raw test file | Identify any rack/wheel-angle test or plan a new fixture test |

## Team-assisted recovery worksheet

For each candidate file the reviewer should fill in:

| Field | Required entry |
|---|---|
| Exact filename | |
| Storage URL or controlled path | |
| File type | |
| Author/owner | |
| Created/modified date | |
| Software and version | |
| Vehicle revision | |
| CAD configuration/display state | |
| Input definition | |
| Output definitions | |
| Sweep start/stop/step | |
| Objective and constraints | |
| Coordinate and sign convention | |
| Source versus export relationship | |
| Known manual edits | |
| SHA-256 | |
| Access restrictions | |
| Reviewer | |

## Minimum recovery packages

### Legacy optimizer package

A complete package includes:

- original workbook, script, executable configuration, or CAD design study;
- all referenced input files;
- exact variable names, units, ranges, and sweep resolution;
- objective or selection rule;
- infeasibility behavior;
- tie-rod-length definition;
- one known input/output case;
- software/version and vehicle revision;
- source hash and owner.

### CAD motion-study package

A complete package includes:

- CAD assembly and configuration revision;
- steering and suspension mates or joint definitions;
- rack-center and reference ride-height state;
- motion-study driver definition;
- left/right wheel-angle measurement definition;
- sweep domain and resolution;
- raw export before spreadsheet fitting;
- solver settings and warnings;
- source and export hashes.

### Physical sweep package

A complete package includes:

- vehicle setup and alignment;
- steering input channel and measurement location;
- rack displacement and left/right road-wheel angle measurements;
- sensor/fixture calibrations;
- loading and compliance condition;
- sample rate and synchronization;
- repeated sweeps in both directions;
- raw immutable data and uncertainty report.

## Recovery decision rules

1. A polynomial copied into the spreadsheet is not the mechanism source.
2. A motion-study screenshot is not a benchmark table.
3. A current CAD model is not assumed identical to the historical model.
4. A value remembered by a member is a lead, not parameter authority.
5. Recreated geometry must be labeled reconstruction and cannot replace the original artifact in legacy-reproduction mode.
6. Failure to locate a source does not block a new analytical model forever, but it blocks claims of reproducing or validating against that source.
