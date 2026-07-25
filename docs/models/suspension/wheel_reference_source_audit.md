# WUFR wheel reference and physical-state source audit

**Scope:** source review for `AUTH-SUSP-0002` / `MOD-SUSP-0002`  
**Purpose:** determine what the current WUFR sources actually support for wheel-center construction, wheel-plane orientation, historical OptimumK source-steering removal, and a physical suspension-state coordinate.

## 1. Primary source set

### OptimumK vehicle setup

`WUFR-26 FINAL 8.21.2025.xlsx`

- Box file ID: `2014803790843`
- frozen version: `2224178574043`
- provider SHA-1: `15eadfb93369192038888da92ebaa6674db56cfa`
- OptimumK coordinate transform declared by the source: `[[1,0,0],[0,-1,0],[0,0,1]]`
- `Reference Distance = 1562.400 mm`; the team confirmed during PR39 review that this is the WUFR wheelbase.

Source wheel setup values:

| Axle | Half track | Long. offset | Lat. offset | Vert. offset | Static camber | Static toe | Tire diameter |
|---|---:|---:|---:|---:|---:|---:|---:|
| Front | 615.986 mm in Box text representation | 0 | 0 | 0 | -2.250 deg | -1.000 deg | 464.820 mm |
| Rear | 603.286 mm in Box text representation | 0 | 0 | 0 | -1.000 deg | +0.500 deg | 464.820 mm |

The Box text representation rounds the half-track fields to 0.001 mm. The frozen OptimumK result workbook exposes the corresponding higher-precision nominal values `615.98556 mm` front and `603.28556 mm` rear.

### OptimumK pure-heave result

`WUFR-26 8.21 Heaves 1inch.xlsx`

- SHA-256: `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`
- OptimumK Result version: `2.3.0`
- 11 frozen pure-heave states from `-25.4` to `+25.4 mm`.

PR39/PR40 already established the source-result frame rule for this pure-heave workbook:

```text
p_body,optk = p_export,optk - [0,0,h]
p_body,can  = 0.001 * [x_body,optk, -y_body,optk, z_body,optk]
```

This rule is evidence for this pure-heave export only and is not generalized to roll, pitch, or arbitrary OptimumK result exports.

### Physical CAD/drawing evidence

Current WUFR-26 front outboard hardware exists in the source tree and supports the physical idealization that the wheel/hub axis is rigidly carried by bearings in the upright:

- `WT-80201-ZZ CNC UPRIGHT, FRONT, RIGHT.pdf`
  - Box ID `2071451248395`
  - SHA-1 `74a6afa2b8d712f240a84f2b864f1771cb382491`
  - drawing shows the machined upright and bearing-seat geometry.
- `WT-80101-AA FRONT HUB.pdf`
  - Box ID `2013149176102`
  - SHA-1 `dc9777af31a179c5ef840cdb34cda39923fe5a3d`
  - drawing shows the hub's coaxial bearing/shaft geometry.
- `WT-A0801-AA FRONT HUBS.pdf`
  - Box ID `2181097379981`
  - SHA-1 `d567e7e8b24808a4716f2ca7e95921acff46a95e`
  - BOM includes two `61909-2RS1` wheel bearings plus the hub, bearing spacer, retainer, wheel-speed gear, and bearing abutment ring.

These drawings support rigid upright-to-hub-axis transport for the ideal-joint model. They do **not** provide installed/as-built bearing play, compliance, alignment, or metrology authority.

Raw STEP/SolidWorks geometry is present in Box, but the current connector cannot expose the STEP binary through the available content interface. That limitation does not block the first source-bounded wheel-reference authorization because the OptimumK setup/result already supplies stronger direct kinematic evidence for the nominal wheel reference.

## 2. Source-verified nominal wheel-center construction

The current OptimumK source uses zero longitudinal, lateral, and vertical wheel offsets. For that source state, the nominal wheel center is reproduced from the source half-track, tire radius, side identity, and static camber alone.

Use canonical axes `+x` forward, `+y` vehicle left, `+z` upward and side sign

```text
s = +1 left
s = -1 right.
```

Let

```text
R = tire_diameter / 2
h_t = half_track
gamma = source static camber,
```

where positive camber follows the already reviewed project convention: wheel top outward.

For the frozen zero-offset WUFR source:

```text
x_wc = 0
y_wc = s * (h_t + R sin(gamma))
z_wc = R cos(gamma).
```

This is a source-specific reconstruction rule, not a proposed universal wheel-center formula.

### Front

Using `h_t = 615.98556 mm`, `R = 232.41 mm`, `gamma = -2.25 deg`:

```text
|y_wc| = 606.8611862194348 mm
z_wc   = 232.2308203127064 mm.
```

The nominal OptimumK result reports the same wheel-center coordinates to floating-point precision after canonical orientation conversion.

### Rear

Using `h_t = 603.28556 mm`, `R = 232.41 mm`, `gamma = -1.0 deg`:

```text
|y_wc| = 599.2294462199110 mm
z_wc   = 232.3746028312969 mm.
```

Again, the frozen result reproduces these coordinates to the available result precision.

### Boundary

This evidence authorizes the **current zero-offset source case only**. The meanings of nonzero OptimumK longitudinal/lateral/vertical wheel offsets have not been reviewed and must not be guessed by extending the formula.

## 3. Nominal wheel-plane orientation

The steering stack already has a reviewed source convention for centered wheel-plane orientation in `src/pssd_steering/projection.py` and `WUFR26_DESIGN_NOMINAL_V0`:

- `+x` forward, `+y` left, `+z` up;
- side-local positive toe = toe-out;
- side-local positive camber = top-out;
- heading is `side_sign * toe_out`;
- a wheel-plane normal plus a forward reference resolves the plane's 180-degree ambiguity.

`MOD-SUSP-0002` should reuse that convention rather than define a second interpretation of source toe/camber.

Frozen nominal basis values are stored in `WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml`.

The result workbook's scalar `Toe Angle` and `Camber Angle` values are retained as descriptive external channels. They differ slightly from the exact setup values even at the nominal state and therefore are not promoted to a unique three-dimensional plane basis for the new source adapter.

## 4. Exact removal of source tie-rod steering from historical front results

The front pure-heave OptimumK result already contains tie-rod-constrained upright steering. Feeding that pose directly into `MOD-STEER-0001` would double count steering. Earlier work therefore correctly excluded it as a direct `SuspensionPoseSet` provider.

The current result contains enough three-dimensional geometry to remove that steering without using the ambiguous scalar `Steer Angle` output.

For each frozen front state:

1. Convert the nominal and current lower-upright, upper-upright, and upright tie points to the same canonical body frame.
2. Use `EQ-SUSP-0003` to transport the nominal upright into the current minimum-twist unresolved-steering reference pose.
3. Let `p_T,ref` be the transported nominal upright tie point, `p_T` the actual source result tie point, `p_L` the current lower joint, and

```text
k = normalize(p_U - p_L).
```

4. Form radius vectors from `p_L` and project each perpendicular to `k`:

```text
a_perp = (p_T,ref - p_L) - k [k dot (p_T,ref - p_L)]
b_perp = (p_T     - p_L) - k [k dot (p_T     - p_L)].
```

5. The signed source upright twist is

```text
psi = atan2(k dot (a_perp cross b_perp), a_perp dot b_perp).
```

6. Remove source steering from any upright-attached source point `p` by

```text
p_unresolved = p_L + R(k,-psi)(p-p_L).
```

Applying this to the source wheel-center states makes the unsteered result agree with the minimum-twist rigid transport of the nominal wheel center at floating-point scale over all 11 frozen front-heave states.

The left-front reconstructed twists are:

| Heave mm | reconstructed 3D twist deg |
|---:|---:|
| -25.40 | -0.243537954171 |
| -20.32 | -0.194249654619 |
| -15.24 | -0.145370121099 |
| -10.16 | -0.096779903458 |
| -5.08 | -0.048361667369 |
| 0.00 | 0.000000000000 |
| +5.08 | +0.048418793705 |
| +10.16 | +0.097006904221 |
| +15.24 | +0.145875240221 |
| +20.32 | +0.195133661309 |
| +25.40 | +0.244891221124 |

The OptimumK scalar `Steer Angle [Left] [Front]` does **not** equal these three-dimensional twists. For example, the source channel is about `-0.1534 deg` at `-25.4 mm` and `+0.1582 deg` at `+25.4 mm`, whereas the actual tie-point-derived upright twists are approximately `-0.2435 deg` and `+0.2449 deg` respectively.

Therefore `Steer Angle` must not be used as the rotation that strips source steering from a 3D upright pose.

## 5. Physical suspension-state coordinate

`q_L` remains a useful internal mechanism coordinate but should not be exposed to users as wheel travel/jounce/heave by renaming it.

The first physical state coordinate should be

```text
delta_z_wc_body = z_wc(q_L) - z_wc(0),
```

with positive sign upward in the canonical suspension/body frame.

A state adapter can then solve the bounded inverse problem

```text
z_wc(q_L) - z_wc(0) - requested_delta_z_wc_body = 0
```

on the continuous nominal assembly branch.

This also avoids a source trap: the OptimumK result channel `Wheel Center Displacement Z` is expressed in the result/road-fixed motion convention and is **not** the same thing as body-relative wheel travel. In the pure-heave export, body translation must first be removed before a body-relative wheel-center displacement is formed.

## 6. Contact-reference boundary

The OptimumK result also contains contact-reference coordinates. Their relationship to wheel center, tire radius, static camber, and static toe is a source convention that is not needed to authorize the first wheel-center/upright-state provider.

`AUTH-SUSP-0002` therefore does not promote a generic contact-patch point or tire-envelope construction. Tire contact, loaded radius/deflection, and force application remain separate future model questions.

## 7. Conclusion

The existing project sources are sufficient for the next bounded suspension slice without requesting new user data:

1. nominal WUFR wheel center is directly reconstructible and cross-checked against OptimumK;
2. nominal wheel-plane orientation already has a reviewed static-alignment convention;
3. historical source tie-rod steering can be removed exactly from 3D result geometry using the upright tie point rather than the scalar `Steer Angle` channel;
4. body-frame wheel-center vertical displacement provides a physically meaningful state coordinate that can be inverted to the internal `q_L` mechanism coordinate.

The next missing evidence becomes important only when expanding beyond this scope: nonzero source wheel-offset semantics, a whole-vehicle front/rear source-origin adapter, actuation-linkage kinematics, and installed/as-built metrology.