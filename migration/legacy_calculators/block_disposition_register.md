# Legacy Calculator Block Disposition Register

**Status:** Initial block-level inventory  
**Authority:** Documentation only; no block is authorized for production implementation by this register  
**Purpose:** Give every meaningful legacy calculation, input, evidence, sweep, filter, or placeholder a stable migration identifier that survives spreadsheet reorganization.

## Identifier rule

Block identifiers use the `MIG` prefix because they describe source-material migration units rather than accepted equations or canonical quantities.

- `MIG-SC26-*`: `Suspension Calculations 2026`
- `MIG-LLTD-*`: `LLTD Calculator`
- `MIG-STR-*`: separate steering/tie-rod workflow

Cell ranges are evidence locators only. The stable ID is the durable reference.

## Suspension Calculations 2026

| Stable block ID | Sheet / source range | Observed purpose | Preliminary disposition | Next documentation gate |
|---|---|---|---|---|
| `MIG-SC26-VAR-001` | Variables `A1:C38` | Parameter names, values, definitions | Rewrite | Candidate-observation and quantity mapping |
| `MIG-SC26-VAR-002` | Variables `D` | Informal provenance and quality notes | Rewrite | Convert notes into structured provenance, uncertainty, and applicability fields |
| `MIG-SC26-VAR-003` | Variables `E2:F6` | Unit conversion constants | Benchmark only | Confirm canonical SI and adapter-only conversion policy |
| `MIG-SC26-VAR-004` | Variables `H1:I18` | Approximation and sign notes | Rewrite | Move valid content into conventions, assumptions, and risks |
| `MIG-SC26-LT-001` | Load Transfer `B3:F16` | Static mass distribution | Accepted with restrictions candidate | Re-derive and benchmark sum-of-load and moment balance |
| `MIG-SC26-LT-002` | Load Transfer `A33:L59` | Older transfer method and edge-case matrices | Benchmark only | Identify fixed fudge factors and freeze legacy reproduction case |
| `MIG-SC26-LT-003` | Load Transfer `A69:X116` | Fixed-coefficient aero load addition | Rewrite | Define coefficient signs, references, force application, and validity |
| `MIG-SC26-LT-004` | Load Transfer `A120:X186` | Later roll/load-transfer calculation | Rewrite | Split total, geometric, elastic, unsprung, aero, and wheel-load assembly equations |
| `MIG-SC26-LT-005` | Load Transfer `N133:R162` | Roll-stiffness and LLTD sensitivity sweeps | Rewrite workflow | Define sweep inputs, outputs, fixed assumptions, and benchmark points |
| `MIG-SC26-TIRE-001` | Tire Forces primary formulas | Cornering-stiffness fit versus normal load | Benchmark only | Recover source data, fit script, units, tire identity, and fit envelope |
| `MIG-SC26-TIRE-002` | Tire Forces notes/chart | Tire scaling and sanity observations | Research evidence | Separate observations from model corrections and recover source context |
| `MIG-SC26-FD-001` | Optimal Front and Rear Force Di `A1:Y65` | Non-dimensional acceleration/braking distribution | Benchmark only | Re-derive and state steady/fixed-CG assumptions |
| `MIG-SC26-FD-002` | Optimal Front and Rear Force Di `Z2:AO66` | Aero-adjusted force distribution | Rewrite | Depend on reviewed aero and four-corner load model |
| `MIG-SC26-FD-003` | Optimal Front and Rear Force Di `A67:Y108` | Constant-friction force curves | Benchmark only | Define force-request, tire-limit, bias, and lock-sequence quantities separately |
| `MIG-SC26-PITCH-001` | Pitch & dive `B11:C18` | Linear pitch without load transfer | Accepted with restrictions candidate | Independent derivation and small-angle limiting tests |
| `MIG-SC26-PITCH-002` | Pitch & dive `B19:C23` | Pitch with added load-transfer term | Rewrite | Complete derivation and reconcile wheelbase, sign, tire stiffness, and motion ratio |
| `MIG-SC26-ARB-001` | ARB & Roll pointer | Link to `ARB Calculations.xlsx` | Unknown | Recover exact artifact or deprecate missing pointer |
| `MIG-SC26-CAL-001` | Sheet8 | Corner-weight/ride-height stiffness inference | Unknown | Recover test configuration, method, raw readings, and uncertainty |
| `MIG-SC26-ALIGN-001` | Alignment front block | Front string-to-toe conversion | Rewrite | Correct trigonometry and define fixture geometry and per-wheel/axle toe |
| `MIG-SC26-ALIGN-002` | Alignment rear block | Rear string-to-toe conversion | Rewrite | Correct trigonometry and define fixture geometry and per-wheel/axle toe |
| `MIG-SC26-ALIGN-003` | Alignment target/guidance block | Desired toe and tie-rod-turn guidance | Rewrite | Separate setup target, adjustment mechanism, and technician instruction |
| `MIG-SC26-NF-001` | Natural Frequency pointer | External source link | Unknown | Recover source or deprecate pointer |
| `MIG-SC26-SB-001` | Steering Breakaway | Single-scenario tire/steering estimate | Rewrite | Recover MATLAB result and separate parked, low-speed, and moving cases |
| `MIG-SC26-ACK-001` | Ackerman Steering ideal block | Low-speed ideal Ackermann reference | Benchmark only | Freeze exact track, wheelbase, steering-axis, and angle definitions |
| `MIG-SC26-ACK-002` | Ackerman Steering historical block | WUFR-24/25/26 steering observations | Evidence | Add vehicle/CAD revision, source, sweep, and uncertainty |
| `MIG-SC26-ACK-003` | Ackerman Steering adjusted estimates | Ackermann percentage and slip adjustment | Rewrite or retire | Freeze metric definition and replace ad hoc slip adjustment with tire-informed objective later |
| `MIG-SC26-SR-001` | Steer Ratio `B3:BN17` | WUFR-24 CAD motion-study export | Evidence | Recover CAD revision and input/output conventions |
| `MIG-SC26-SR-002` | Steer Ratio `T13:V17` | WUFR-24 polynomial fits | Benchmark only | Restrict to interpolation range and compare against direct mechanism data |
| `MIG-SC26-SR-003` | Steer Ratio `B30:BN42` | WUFR-25 CAD motion-study export | Evidence | Recover CAD revision and input/output conventions |
| `MIG-SC26-SR-004` | Steer Ratio `T40:V42` | WUFR-25 polynomial fits | Benchmark only | Restrict to interpolation range and compare against direct mechanism data |
| `MIG-SC26-US-001` | Understeer Gradient `B1:E21` | Bicycle-model quantities | Accepted with restrictions candidate | Define exact steering gradient and validity envelope |
| `MIG-SC26-US-002` | Understeer Gradient `A25:W61` | Explicitly rejected method | Deprecated | Preserve rejection rationale and prohibit reuse |
| `MIG-SC26-US-003` | Understeer Gradient `A62:W76` | ARB/load-transfer case | Rewrite | Split steering-wheel, road-wheel, tire-angle, and yaw-rate metrics |
| `MIG-SC26-US-004` | Understeer Gradient `A79:T92` | Roll-balance case | Research/benchmark | Identify model variant and freeze inputs |
| `MIG-SC26-US-005` | Understeer Gradient `A94:T107` | Neutral case | Research/benchmark | Identify model variant and freeze inputs |
| `MIG-SC26-US-006` | Understeer Gradient `A109:T122` | Alternate balance case | Research/benchmark | Identify model variant and freeze inputs |
| `MIG-SC26-US-007` | Understeer Gradient `A124:T137` | High-rear/low-front case | Research/benchmark | Identify model variant and freeze inputs |
| `MIG-SC26-US-008` | Understeer Gradient `A139:T152` | Stiffer-front/neutral case | Research/benchmark | Identify model variant and freeze inputs |
| `MIG-SC26-SF-001` | Steering Forces `B16:D27` | Straight-line braking steering moment | Rewrite | Re-derive force directions, lever arms, trail, and steering-axis signs |
| `MIG-SC26-SF-002` | Steering Forces `B42:P50` | Combined corner-entry force/moment | Rewrite | Depend on reviewed tire and four-corner force state |
| `MIG-SC26-SF-003` | Steering Forces `B54:J62` | Lateral-force contribution | Rewrite | Shared steering-axis geometry and sign audit |
| `MIG-SC26-SF-004` | Steering Forces `B66:N74` | Vertical-force contribution | Rewrite | Shared steering-axis geometry and sign audit |
| `MIG-SC26-SF-005` | Steering Forces `B78:J86` | Aligning-moment contribution | Rewrite | Canonical tire moment and trail interface |
| `MIG-SC26-SF-006` | Steering Forces `B103:E122` | Parked scrub/breakaway estimate | Rewrite | Separate contact-patch scrub, friction, compliance, and breakaway model |
| `MIG-SC26-SCF-001` | Steering Column Forces `B3:C24` | Rack and column torque conversion | Accepted with restrictions candidate | Authorize only after upstream rack force is trusted |
| `MIG-SC26-SCF-002` | Steering Column Forces `B26:F49` | Miter-gear geometry and forces | Accepted with restrictions candidate | Re-derive free-body diagrams, signs, efficiency, and load reversal |
| `MIG-SC26-SCF-003` | Steering Column Forces `B63:F76` | Shaft bearing reactions | Accepted with restrictions candidate | Re-derive supports and load-case identity |
| `MIG-SC26-BEAM-001` | Beam Deflection | Empty sheet | Deprecated | No replacement dependency |
| `MIG-SC26-UNK-001` | Sheet18 | Unknown sweep and torque conversion | Blocked | Recover source context before assigning purpose |

## LLTD Calculator

| Stable block ID | Sheet / source range | Observed purpose | Preliminary disposition | Next documentation gate |
|---|---|---|---|---|
| `MIG-LLTD-IN-001` | Inputs `A6:G14` | Geometry, sprung mass, roll arm, axle fractions | Rewrite into registry | Quantity mapping and provenance resolution |
| `MIG-LLTD-IN-002` | Inputs `A16:G25` | Spring, motion ratio, tire stiffness, sensor calibration, wheel rate | Rewrite into parameter/sensor/channel records | Separate component parameters from calibration records |
| `MIG-LLTD-IN-003` | Inputs `A27:J36` | ARB, chassis stiffness, scenario multipliers | Rewrite | Resolve physical stiffness definitions and scenario semantics |
| `MIG-LLTD-IN-004` | Inputs `A38:G47` | Chassis/ARB sensitivity controls | Rewrite workflow | Typed sweep specification and output definitions |
| `MIG-LLTD-IN-005` | Inputs `A49:G53` | Automatic steady-state filter controls | Rewrite | Selection-rule record and circular-validation controls |
| `MIG-LLTD-RIG-001` | Rigid_Model `B7:E13` | Active wheel and tire vertical rates | Accepted with restrictions candidate | Units, motion-ratio convention, and direct/calculated precedence |
| `MIG-LLTD-RIG-002` | Rigid_Model `B14:B25` | Axle suspension/tire/effective roll stiffness | Accepted with restrictions candidate | Re-derive, document symmetry assumptions, and limiting tests |
| `MIG-LLTD-RIG-003` | Rigid_Model `B27:B29` | Total stiffness, elastic LLTD, roll gradient | Accepted with restrictions candidate | Rename elastic quantities and document exclusions |
| `MIG-LLTD-COMP-001` | Compliance_Model `B6:B16` | Independent-series chassis placeholder | Deprecated/rewrite | Preserve reproduction, replace with coupled torsional model |
| `MIG-LLTD-COMP-002` | Compliance_Model `A20:H40` | Chassis-stiffness sweep | Rewrite workflow | Use coupled model and typed sweep |
| `MIG-LLTD-COMP-003` | Compliance_Model `J20:P40` | Front-ARB sweep | Rewrite workflow | Use reviewed front axle model |
| `MIG-LLTD-COMP-004` | Compliance_Model `R20:X40` | Rear-ARB sweep | Rewrite workflow | Use reviewed rear axle model |
| `MIG-LLTD-RAW-001` | Raw_Data `A:L` | Pasted logger channels | Evidence only | Recover immutable raw file and channel metadata |
| `MIG-LLTD-RAW-002` | Raw_Data `M4:M1003` | Automatic row-selection mask | Rewrite | Derived mask with reason codes and versioned rule |
| `MIG-LLTD-DER-001` | Derived_Data `D:G` | Wheel travel from damper pots | Rewrite | State-dependent kinematics and calibration lineage |
| `MIG-LLTD-DER-002` | Derived_Data `H:J` | Front/rear/mean body roll proxies | Research quantity | Sensor geometry, road plane, heave/pitch separation, and uncertainty |
| `MIG-LLTD-DER-003` | Derived_Data `K` | Front-minus-rear angle labelled chassis twist | Research quantity | Measurement model proving what portion is chassis twist |
| `MIG-LLTD-DER-004` | Derived_Data `L:M` | Front/rear suspension roll | Rewrite | Kinematic maps, sign, and body/wheel state definitions |
| `MIG-LLTD-DER-005` | Derived_Data `N:P` | Roll-moment and LLTD proxies | Research/model-assisted evidence | Make model dependence explicit and prohibit direct-validation claim |
| `MIG-LLTD-SUM-001` | Summary prediction outputs | Rigid/compliant stiffness and LLTD comparison | Rewrite report | Reviewed model revisions and uncertainty bands |
| `MIG-LLTD-SUM-002` | Summary regressions | Measured roll/twist/suspension gradients | Rewrite identification report | Dataset role, weighting, residuals, confidence, hysteresis, and holdout status |
| `MIG-LLTD-SUM-003` | Summary error metrics | Proxy-to-model comparison | Research | Define residual meaning and avoid circular validation |
| `MIG-LLTD-MAP-001` | Cell_Map | Human-readable cell map | Preserve as migration evidence | Future UI generates ID-based discoverability without cell-address authority |

## Separate steering workflow

| Stable block ID | Source | Observed purpose | Preliminary disposition | Next documentation gate |
|---|---|---|---|---|
| `MIG-STR-0001` | External tie-rod optimizer + CAD motion study + SC26 steering sheets | Steering linkage inverse design and map generation | First migration candidate | Complete source recovery, quantity definitions, requirement-role assignment, equation cards, and benchmark freeze |

## Register maintenance

1. IDs are permanent and are not recycled.
2. Splitting a block creates new child IDs; the parent remains as a historical aggregation record.
3. Merging blocks into a future model does not delete the original IDs.
4. Every equation, quantity, parameter, benchmark, risk, and implementation PR must reference the affected migration block IDs.
5. A preliminary disposition is not implementation authorization.
