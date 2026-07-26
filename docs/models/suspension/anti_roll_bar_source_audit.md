# Anti-Roll-Bar Source Audit

**Program:** PR #49 / `AUTH-SUSP-0005`  
**Configuration:** `WUFR27_SUSPENSION_BASELINE_V0`  
**Snapshot:** `data_catalog/wufr27_anti_roll_bar_package_v0.toml`

## Review question

Determine what can be authorized now for the WUFR Z-bar anti-roll-bar system without inventing blade stiffness or losing the left/right coupling that makes the element physically meaningful.

## Reviewer direction

The reviewer stated on 2026-07-26 that:

- the Z-bar geometry and blade calculations in the 2025 suspension `ARB Development`/ARB stiffness material should be used;
- the same concept is intended for WUFR-27;
- the ARBs are run with zero preload.

This is design-intent authority. It does not, by itself, supply a force-deflection curve or installed/as-built dimensions.

## Populated geometry evidence

### Suspension geometry

The current populated suspension geometry remains:

- `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`
- Box file `1943897977651`
- version `2546941960247`
- SHA-1 `2cfb771f296961be0857161f7b57a6c178180d7a`

The reviewer exporter provides raw 3D sketch coordinates for the hidden-unsuppressed `Front ARB` and `Rear ARB` features. Those coordinates are frozen in the source packet.

The exporter has an already documented sketch-transform defect and does not preserve sketch-entity connectivity. Therefore point row order is **not** accepted as authority for which points are connected, which member is a blade/link, or which scalar deformation coordinate should be used.

### Current WUFR-26 front ARB

Current populated front sources include:

- assembly `SU-A0703-AA FRONT ANTI-ROLL BAR.SLDASM`, Box `1966622548582`, version `2419939815902`, SHA-1 `af57e21fb1f152297c21e51a09ab41b9fee1b3d3`;
- assembly PDF Box `2135607229280`, SHA-1 `34823b5b6a2c0a09a8d2441b6d19525c7219e4cb`;
- blade drawing `SU-70301-AA FRONT, ARB, BLADE.pdf`, Box `2120263458420`, SHA-1 `f1b4e9cca2b1ff8f9e080e8a7ec5ef17eb44514e`, Ti-6Al-4V;
- linkage drawing `SU-70308-AA FRONT, ARB, LINKAGE.pdf`, Box `2120271107980`, SHA-1 `4c64619a9f57a785a1fe50cc6617012027a7e1cb`, carbon fiber, nominal length `7.22 in`, OD `0.50 in`, wall note `0.063 in`.

These establish hardware/geometry identity. No spring constant is inferred from them.

### Current WUFR-26 rear ARB

Current populated rear sources include:

- assembly `SU-A0705-AA REAR ANTI-ROLL BAR.SLDASM`, Box `1966622815072`, version `2547286451403`, SHA-1 `d04059e2b6b53737459c9df3cc35dcb3f71100b5`;
- assembly PDF Box `2135614149053`, SHA-1 `4cda02930ab2ee853c82cf024fc5bde5edf406c1`;
- blade drawing `SU-70502-AA REAR, ARB, BLADE.pdf`, Box `2135720924601`, SHA-1 `c7ab08c916e9e72721572bb65238b9cd5b53e73a`, Ti-6Al-4V;
- linkage drawing `SU-70508-AA REAR, ARB, LINKAGE.pdf`, Box `2135748483981`, SHA-1 `e2e81b398c162321e41ac3b20682aeb2300b4282`, carbon fiber, nominal length `6.22 in`, OD `0.50 in`, drawing thickness note `0.125 in`.

Again, these are geometry/hardware evidence only.

## WUFR-27 direct CAD state

The WUFR-27 ARB folder contains direct front/rear assembly files:

- front `SU-A0303-AA FRONT ANTI-ROLL BAR.SLDASM`, Box `2297763875346`, version `2544178295346`;
- rear `SU-A0305-AA REAR ANTI-ROLL BAR.SLDASM`, Box `2297762603071`, version `2544177011071`.

At audit time both files have the same SHA-1 `8a5ca3ceaece773cb2d877290f07650d77c55042`, the same size `141646` bytes, and the same modification snapshot. They are therefore treated as placeholder/copy evidence, not independent populated front/rear WUFR-27 geometry authority.

The current carryover model uses the populated WUFR-26 geometry plus the reviewer's explicit WUFR-27 carryover statement until a new populated WUFR-27 revision exists.

## Active assembly-state evidence

The exported WUFR-26 `FSA` assembly configuration shows the top-level front ARB active and the top-level rear ARB suppressed.

That fact is retained because it matters to configuration provenance. It is **not** generalized into either of these unsupported claims:

- “WUFR-27 never has a rear ARB”; or
- “the rear ARB geometry is invalid.”

A later vehicle configuration must explicitly choose front/rear enabled/disabled state.

## 2025 ARB Development / stiffness evidence

The relevant 2025 folder is:

`WUFR-25 CAD & SOLIDWORKS DRAWINGS / 2. SUSPENSION / GEOMETRY AND POINTS / ARB Stiffness`

Box folder `312966793399`.

It contains the front blade CAD and SolidWorks Simulation result/support files, including:

- front blade part Box `1860740123335`, version `2051848182332`, SHA-1 `cdc59578f2109a7f21d076a7e799e73047d40a5f`;
- `SU-20701-AA FRONT, ARB, BLADE-Static 3.CWR`, Box `1860760496998`, version `2051863720679`, SHA-1 `b8d865c7b15330e947b531b8e39e148d5808829b`;
- simulation log Box `1860757976604`, version `2051863650815`, SHA-1 `05ba56e2a410fdc77c5071e949a19a692a407fc2`;
- associated PGF/GSZ/MFC files frozen in the source packet.

The text-accessible log provides mesh/solver statistics but not an actionable load-deflection result. In this audit we did **not** recover all of the following required items together:

1. applied force or torque and direction/application point;
2. constraints/fixtures;
3. deformation observable and its location/direction;
4. result units;
5. a traceable force-deflection or torque-angle pair/curve;
6. a derivation showing how that result maps to the assembled Z-bar deformation coordinate.

Therefore the SolidWorks files are valuable source-recovery evidence but are **not yet constitutive stiffness authority**.

## Historical values rejected as constitutive substitutes

### Weight-transfer sensitivity script

`Weight_transfer_sensitivity.m`, Box `1760141970183`, SHA-1 `230b4b7816726e3a7c613716860e09c582f606fb`, contains:

- `K_phif_neutral = 2560`
- `K_phir_neutral = 2270`

The front line carries the source comment `%change and figure out`. The script also uses those values in a broader weight-transfer sensitivity calculation rather than documenting a blade test/FEA derivation. They remain historical exploratory comparison values only.

### 2026 FSAE spec sheet

The current spec sheet records `Suspension Roll rate` values of:

- front `556 Nm/deg`;
- rear `458 Nm/deg`.

Those describe suspension roll stiffness, not explicitly ARB-only blade/system stiffness. They may include spring and geometry contributions, so they are comparison/target evidence only for this program.

## Design decision for PR #49

The source evidence is sufficient to authorize the **physics architecture** and **geometry/provenance boundary** now:

- one coupled left/right elastic element;
- explicit zero-preload reference;
- source-defined mechanism deformation coordinate/vector;
- conservative energy/action law;
- signed virtual-work mapping;
- explicit no-bar configuration;
- structured unavailable state when constitutive authority is missing.

It is **not** sufficient to authorize numeric WUFR ARB force/energy yet.

This is preferable to embedding a plausible-looking rate and contaminating later QSS/load-transfer results. PR #50 may implement the generic mechanics and WUFR geometry/reference adapter, but WUFR force output must remain `missing_stiffness_authority` until a reviewed stiffness source is recovered or generated.

## Replacement evidence

The stiffness gap can be closed with either:

- a physical blade/system force-deflection or torque-angle test; or
- a re-run/recovered FEA/analytical derivation with frozen load, fixture, deformation coordinate, units, geometry/material revision, fit/domain, and independent sanity check.

The result should be stored as constitutive evidence rather than as an already-converted “wheel rate,” so the exact bilateral geometry/Jacobian remains responsible for mapping it into suspension/vehicle generalized coordinates.