# V2 Benchmark Artifact Set — B1 Base Static Screen Family

**Status:** LOCKED
**Set ID:** `V2-BENCH-B1`
**Set version:** `1.0.0`
**Locked on:** 2026-04-14
**Branch:** `working/core-v2`
**Target resolution:** 1920 × 1080 (assumed MSI G27C4X native per prior context)

The B1 family is the first frozen V2 benchmark artifact set. It is deliberately small and stable: five mandatory static screen artifacts, each with a single declared measurement target. Nothing in B1 is "nice to have." If an artifact is not in B1, it does not count toward V2-M3 and V2-M6.

## Philosophy

- **Small, useful, stable.** Five artifacts is enough to exercise clean detection, edge behavior, routing, gradient response, and geometry — without creating a maintenance burden.
- **Deterministic.** The generators are pure Python stdlib, the PNG encoder uses uncompressed zlib (DEFLATE stored blocks), and SHA-256 values in the manifest are reproducible byte-for-byte across platforms and Python versions.
- **Screen-only.** No print path. No reliance on physical calibration boards.
- **Static-first.** No animation, no temporal benchmark. Temporal is explicitly out of scope for B1.
- **Solo-feasible.** One operator can render, display, and capture every artifact in one session on the locked rig (S23 Ultra, MSI G27C4X).

## The five B1 artifacts

| Artifact ID | Family | Generator | Params | Measurement target |
|---|---|---|---|---|
| `b1-clean-solid` | B1-base-static-screen | `gen_clean_solid` | `gray_level=128` | Clean-detection baseline / sensor noise floor |
| `b1-edge-half` | B1-base-static-screen | `gen_edge_half` | — | Edge / boundary stability |
| `b1-grid-64` | B1-base-static-screen | `gen_grid_64` | `cell=64` | Routing stability / moire observation |
| `b1-gradient-h` | B1-base-static-screen | `gen_gradient_h` | — | Gradient / signature stability |
| `b1-corners-fiducials` | B1-base-static-screen | `gen_corners_fiducials` | `marker_size=32, inset=10` | Angle / geometry baseline |

All five are mandatory. None is optional for V2-M3 or V2-M6.

### Derived observations (no new artifacts needed)

The following calibration-relevant behaviors fall out of capturing the five artifacts above at declared rig variations — they are **not** separate artifacts:

- **Distance sensitivity baseline** — capture any B1 artifact at two phone-to-screen distances (pilot baseline ± a declared delta) and compare deltas.
- **Angle sensitivity baseline** — measured directly against `b1-corners-fiducials` centroids.
- **Glare sensitivity baseline** — observable on `b1-clean-solid` (mid-gray shows reflections cleanly) and `b1-gradient-h` (ramp distortion near reflections).

Adding these as standalone artifacts would bloat B1 without adding information.

## File layout

```
V2_BENCHMARK_SET/
├── V2_BENCHMARK_SET_MANIFEST.json     # locked manifest, SHA-256 per asset
└── assets/
    ├── b1-clean-solid.png
    ├── b1-edge-half.png
    ├── b1-grid-64.png
    ├── b1-gradient-h.png
    └── b1-corners-fiducials.png
```

## Generator source

```
05_ACTIVE_DEV/aurexis_lang/src/aurexis_lang/v2_benchmark/
├── __init__.py                        # package metadata (SET_ID, SET_VERSION, defaults)
├── png_writer.py                      # zero-dep byte-deterministic PNG encoder
├── generators.py                      # five B1 generators + B1_ARTIFACTS registry
└── render.py                          # build_manifest / render_to_disk / verify_on_disk + CLI
```

## How to re-render / verify

Render-and-verify in one step (renders to `V2_BENCHMARK_SET/` and verifies byte-for-byte against fresh regeneration):

```bash
cd <V2 working folder>
python 05_ACTIVE_DEV/aurexis_lang/run_v2_benchmark_verify.py
```

Or via the package CLI:

```bash
# Render + overwrite manifest
python -m aurexis_lang.v2_benchmark.render render --root .

# Verify the current on-disk set
python -m aurexis_lang.v2_benchmark.render verify --root .
```

Tests live at `05_ACTIVE_DEV/aurexis_lang/tests/test_v2_benchmark.py` and are collected automatically by the project `pytest.ini`.

## What locks the set

The `set_version` (`1.0.0`) locks all of:

- the ordered list of five artifact IDs
- the generator function name and parameters per artifact
- the render resolution (1920 × 1080)
- the PNG encoder strategy (uncompressed zlib stored blocks)
- the resulting SHA-256 per asset

Any change to any of those requires a `set_version` bump and a re-lock.

## What does **not** lock the set

- Platform of origin (Linux / Windows / macOS) — output is byte-deterministic.
- Python minor version — `png_writer.py` avoids zlib compression, and `hashlib.sha256` is stable.
- Clock, random seed, environment variables — none are read.

## Relationship to V1

None of this modifies V1 substrate. Every source file under `v2_benchmark/` is new V2 code. Every asset and manifest entry lives under the V2-only `V2_BENCHMARK_SET/` directory. The V2-side tests are additive to V1's test suite and do not mutate V1 fixtures.

## Clean-room posture

The `png_writer.py` deflate-stored-block encoder and all five generators are original, written for Aurexis Core V2 in this working tree. No third-party code is vendored. No dependency outside the Python stdlib is required. The set inherits V1's clean-room provenance standard.
