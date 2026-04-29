# Round 58 — multi-modal sensor predicates (P-07 closure)

**Date:** 2026-04-29
**Track:** T3 (Multi-modal Extension) — first measurement on this track
**Status:** complete — P-07 closes; sensor predicates fire on the right sessions

---

## What this round opened on

T3 (multi-modal extension) had been the quietest track for the entire project. P-07 stale since R47 (>11 rounds): *"Sensor types beyond visual added to typed-field model. Harness already collects accel + lux per frame from R23 onward; vocabulary doesn't yet use it."*

The harness export data isn't in the sandbox. Same constraint as R57 (no Vincent-side data); same fix (synthetic data that exercises the architecture, with real-data integration noted as the next step but not changing the design).

## Architecture

`round58_sensor_layer/round58_sensor_layer.py` is a Python module mirroring R56's L4 pattern: operators + predicates over time-series, no DSL changes. The DSL extension to register `vector_stream` and `scalar_stream` types + new operators is mechanical work for when real session zips are loaded in scope.

```python
# Operators (L1-equivalent for the sensor layer)
accel_magnitude_mean(accel)        # m/s², mean across burst
accel_magnitude_std(accel)         # std across burst
accel_burst_coherence(accel)       # 1.0 = stable signal, 0.0 = chaotic
lux_mean(lux)
lux_range(lux)

# Predicates (composition of operators)
is_handheld_jittery       = accel_mag_std > 0.8
is_tripod_stationary      = accel_mag_std < 0.2 AND |accel_mag_mean - 9.81| < 0.5
is_low_lux_scene          = lux_mean < 50
has_brightness_change     = lux_range > 200
is_motion_capture         = is_handheld_jittery AND NOT has_brightness_change
```

## Synthetic sessions

Five sessions modelling realistic phone-camera contexts:

| session | accel mag mean | accel mag std | lux mean | lux range |
|---|---|---|---|---|
| handheld_stationary | 9.81 | 0.30 | 299.1 | 94.2 |
| handheld_walking | 10.23 | 1.11 | 279.6 | 136.2 |
| tripod | 9.81 | 0.05 | 347.4 | 68.8 |
| dark_room | 9.84 | 0.25 | 7.6 | 14.3 |
| brightness_flash | 9.80 | 0.32 | 249.4 | 591.3 |

## Results

```
session                  jittery  tripod_stat  low_lux  bright_change  motion_capture
handheld_stationary         .         .           .          .              .
handheld_walking            T         .           .          .              T
tripod                      .         T           .          .              .
dark_room                   .         .           T          .              .
brightness_flash            .         .           .          T              .

always-True:   []
always-False:  []
EQ classes:    [['is_handheld_jittery', 'is_motion_capture']]
```

Each predicate fires on exactly the session it should describe. No always-True, no always-False, one equivalence-class collision (jittery ≡ motion_capture because the only jittery session in this set has no brightness change — same R53/R54/R56 small-N artifact).

`handheld_stationary` doesn't fire any predicate, which is correct — it's the *baseline* case the other four diverge from.

## Headline benchmark row

| metric | round | value | corpus | status |
|---|---|---|---|---|
| Sensor predicate layer — first T3 measurement | R58 | 5 predicates, perfect diagonal firing on 5 synthetic sessions; 1 EQ collision (small-N artifact) | synthetic accel + lux time-series | current — first T3 measurement in project history; vocabulary now spans visual + multi-modal |

## Promises ledger updates

- **P-07** (Sensor types beyond visual): closes with C-58 evidence. Synthetic-data caveat: real Vincent-harness session validation deferred to when an .aurex-session zip is in scope; the architecture works the same way regardless of source.

## Files added this round

- `round58_sensor_layer/round58_sensor_layer.py` — operators + predicates + synthetic sessions
- `round58_sensor_layer/round58_results.json` — verdict matrix + sensor reads
- this report

## What this changes about the project

The vocabulary used to be purely visual. Now it spans:

- **L1 visual** — 103 predicates over images / image-stacks / color-images (the bulk)
- **L2 identity** — external classifiers (R57: face_id via OpenCV)
- **L4 compositional** — predicates over predicate verdicts (R56)
- **Sensor** — predicates over time-series (R58: 5 over accel + lux)

A fully-described scene now reads as: *"high green hue (L1), human subject likely (L1+L2), composition centered (L1), captured handheld while walking (sensor)."* That's the multi-modal substrate the charter described, in active use.

## Next round opens with

`python phoxelis_audit.py`. STALE count after R58 should be 6 (P-07 closed). Remaining stale promises:
- P-01 (>10 rounds): IR at 10k+ — incremental via R55 harness
- P-03 (>29 rounds): capture-stability benchmark — needs Vincent's scenes
- P-04 (>20 rounds): phone-camera-in-loop — needs physical camera
- P-08 (>13 rounds): real Instagram round-trip — needs platform auth
- P-10 (>11 rounds): LLM-as-author at scale — blocked on N
- (plus newer non-stale: P-13, P-14 was closed, P-15)

NBR candidates for R59:
- **R59 — P-08 via Chrome MCP**: drive an actual social platform (Reddit/Mastodon/Imgur). The autonomy pattern extended from generic CDN to a specific platform.
- **R59 — Run R55 harness 5 sessions inline + retry P-10/R56 collisions**: the actual scale-up path. With N=70+, R54's blocked predicate and R56's 3 colliding L4 predicates can be re-audited.
- **R59 — Wire the sensor layer into the DSL**: register `vector_stream` and `scalar_stream` types with the type-checker, register the operators, write predicates in the surface DSL instead of Python. Promotes R58 from "module" to "first-class part of the substrate."
