# Exploratory local ride parameter study

Reproduce: `PYTHONPATH=src python scripts/run_ride_parameter_study.py`.

All four local geometry derivative checks and 36 sensitivity cases pass the
predeclared specification. This combines current nominal CAD/spring sources,
static corner mass proxies, legacy workbook tire-rate scenarios and assumed
damping; it is not an installed vehicle modal prediction.

| Nominal local quantity | Front | Rear |
|---|---:|---:|
| Spring elastic contribution | 24.635 N/mm | 31.990 N/mm |
| Loaded geometric contribution | 0.407–0.408 N/mm | 0.504 N/mm |
| Total local tangent | 25.043 N/mm | 32.494 N/mm |
| Exploratory low-mode range | 2.669–2.764 Hz | 3.133–3.274 Hz |
| Exploratory high-mode range | 29.285–34.958 Hz | 30.607–36.349 Hz |

Mode ranges span tire multipliers and corner mass proxies; damping does not
change these undamped eigenvalues. No coupled heave/pitch/roll interpretation is
claimed. The nominal CAD state has not been replaced by a solved equilibrium.
The independent second energy derivative agrees with the mapped tangent; two
geometry sampling steps check sensitivity to finite differencing.

The 1 mm, 0.2 s cosine bump cases use explicit damping proxies, 10 mm numerical
study travel bounds, and dt=0.0002/0.0001 s. All accepted histories preserve
positive contact at sampled stages and satisfy peak-metric refinement and energy
closure. These bounds are not measured hardware travel or operational limits.
Full inputs, source hashes, per-case metrics and numerical checks are in
`results.json`.

Source recovery: the LLTD workbook contains 180000/190000 N/m front/rear tire
inputs. Tire/pressure/load provenance remains unresolved. The reviewed mass
catalog supplies 5 kg unsprung corner lumps and individual scale readings. The
historical calculator's 10 kg-per-corner value is not used. KW vendor curve
recovery/settings remains separate from the static gas/friction hold.

Subsequent source recovery found the KW vendor document at Box file
1791709004896. It maps reviewed piggyback part 3980599103 to standard S2FS01
and gives adjustment ranges at 0.25 m/s: rebound 300–1060 N and compression
magnitudes 460–1350 N (negative on the vendor plot). This is not a linear
viscous coefficient. Plot digitization/click-specific curve verification is the
next data task; the present results continue to use labelled damping proxies.
See `data_catalog/kw_v5_dynamic_source_recovery_v0.toml`.
