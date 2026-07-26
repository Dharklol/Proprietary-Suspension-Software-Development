# Anti-Roll-Bar Source Audit

**Program:** PR #49 / `AUTH-SUSP-0005`  
**Configuration:** `WUFR27_SUSPENSION_BASELINE_V0`  
**Snapshot:** `data_catalog/wufr27_anti_roll_bar_package_v0.toml`

## Review question

Determine what can be authorized now for the WUFR Z-bar anti-roll-bar system without losing the left/right coupling or falsely promoting a reduced axle-level rate into a blade/component stiffness.

## Reviewer direction

The reviewer stated on 2026-07-26 that:

- the Z-bar geometry and blade calculations in the 2025 suspension `ARB Development`/ARB stiffness material should be used;
- the same concept is intended for WUFR-27;
- the ARBs are run with zero preload;
- the most reliable available ARB values are the MATLAB values `K_phif_neutral=2560` and `K_phir_neutral=2270`;
- available Instron data comes somewhat close, but the MATLAB/simulation values were more consistent for the stiffer settings.

That final statement changes the PR #49 authority decision. The 2560/2270 values are now the governing **reduced effective axle ARB roll-stiffness** values for the prototype. This does not make them measured blade stiffness or installed/as-built authority.

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

These establish hardware/geometry identity. No blade spring constant is inferred from them.

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

That fact is retained because it matters to configuration provenance. It is **not** generalized into either “WUFR-27 never has a rear ARB” or “the rear ARB geometry is invalid.” A later vehicle configuration must explicitly choose front/rear enabled/disabled state.

## 2025 ARB Development / stiffness evidence

The relevant 2025 folder is `WUFR-25 CAD & SOLIDWORKS DRAWINGS / 2. SUSPENSION / GEOMETRY AND POINTS / ARB Stiffness`, Box folder `312966793399`.

It contains the front blade CAD and SolidWorks Simulation result/support files, including:

- front blade part Box `1860740123335`, version `2051848182332`, SHA-1 `cdc59578f2109a7f21d076a7e799e73047d40a5f`;
- `SU-20701-AA FRONT, ARB, BLADE-Static 3.CWR`, Box `1860760496998`, version `2051863720679`, SHA-1 `b8d865c7b15330e947b531b8e39e148d5808829b`;
- simulation log Box `1860757976604`, version `2051863650815`, SHA-1 `05ba56e2a410fdc77c5071e949a19a692a407fc2`;
- associated PGF/GSZ/MFC files frozen in the source packet.

The text-accessible log provides mesh/solver statistics but not an actionable component force-deflection result. We did not recover the applied load/torque, constraints, deformation observable, units, traceable force-deflection/torque-angle curve, and mapping into the assembled Z-bar coordinate together. Therefore these files remain useful **future detailed blade-law recovery evidence**, not the source of the first reduced constitutive law.

## Reviewer-selected MATLAB values

`Weight_transfer_sensitivity.m`, Box `1760141970183`, version `2054072451786`, SHA-1 `230b4b7816726e3a7c613716860e09c582f606fb`, contains:

- `K_phif_neutral = 2560`
- `K_phir_neutral = 2270`

The plot axes explicitly label the corresponding front/rear stiffness quantities in `Nm/deg`. The front assignment also carries `%change and figure out`.

The script uses the K values primarily through their front/rear ratio in the lateral-load-transfer sensitivity expression. Consequently, the script itself does not independently prove the absolute magnitude. Nevertheless, the reviewer has explicitly designated these as the team's most reliable available ARB values based on the simulation history and comparison with available Instron data. That reviewer decision supplies the design-intent authority for the first reduced prototype.

The quantity is therefore frozen as **effective axle ARB roll stiffness**:

- front `K_phi = 2560 N*m/deg = 146677.19555349075 N*m/rad`;
- rear `K_phi = 2270 N*m/deg = 130061.41949469688 N*m/rad`.

The conversion is explicit:

`K_Nm_per_rad = K_Nm_per_deg * 180/pi`.

For a signed axle ARB deformation angle `phi_ARB` in radians:

`U_ARB = 0.5 K_phi phi_ARB^2`

`M_ARB = K_phi phi_ARB`.

Because `K_phi` is already an axle-level reduced quantity, **no additional blade/link/motion-ratio stiffness conversion may be applied**. A future detailed Z-bar/blade model must replace the reduced law, not be stacked on top of it.

## Instron boundary

No exact Instron ARB dataset was frozen in this audit. The reviewer states that the test data comes somewhat close to the MATLAB values but that the MATLAB/simulation values were more consistent for the stiffer settings.

That statement is retained as qualitative corroboration only. No averaging, fitting, uncertainty band, or quantitative correlation is created without the actual test file, fixtures, deformation definition, units, and selected range.

## 2026 FSAE spec sheet

The current spec sheet records `Suspension Roll rate` values of `556 N*m/deg` front and `458 N*m/deg` rear. Those describe whole-suspension roll stiffness, not explicitly ARB-only reduced stiffness, and may include spring/geometric contributions. They remain comparison/target evidence only and do not override the reviewer-selected 2560/2270 ARB values.

## Design decision for PR #49

PR #49 now authorizes:

- one coupled left/right elastic architecture;
- explicit zero-preload reference;
- source-defined bilateral or reduced axle differential coordinate;
- conservative energy/action law;
- signed virtual-work mapping;
- explicit no-bar configuration;
- the reviewer-selected reduced effective axle ARB roll stiffness `2560/2270 N*m/deg` for WUFR-27 prototype use;
- exact SI conversion and one-degree hand benchmarks;
- structured unavailable states for configurations without reviewed stiffness.

PR #49 does **not** authorize blade/component stiffness, detailed Z-bar stress/strain, installed/as-built correlation, or a quantitative Instron fit.

## Replacement evidence

A higher-fidelity detailed blade/system model can replace the reduced law with either a physical force-deflection/torque-angle test or a re-run/recovered FEA/analytical derivation with frozen load, fixture, deformation coordinate, units, geometry/material revision, fit/domain, and independent sanity check.

That detailed constitutive evidence is a **replacement** for the reduced 2560/2270 axle-level law. It must not be added to the reduced law or converted again through a second motion ratio.
