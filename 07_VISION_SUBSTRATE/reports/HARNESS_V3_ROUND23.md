# Round 23 — Phone Harness v3.0 (polarization-pair protocol)

**Date:** 2026-04-28
**Scope:** Add a fifth capture protocol to the Aurexis Phone Harness so the
phone can generate the two-axis bursts that Workbench's polarization
predicate (`has_polarization_signal`) needs.

## What changed

| Layer | File | Change |
|---|---|---|
| Resources | `app/src/main/res/values/strings.xml` | +3 strings: `proto_polarization_label`, `proto_polarization_id`, `proto_polarization_instructions` |
| Layout | `app/src/main/res/layout/activity_main.xml` | weightSum 4 → 5; new orange (#FFB74A) `protoPolarizationButton` |
| Logic | `app/src/main/java/com/aurexis/harness/MainActivity.kt` | new `POLARIZATION_PAIR` enum value, `axisLabel: String?` on `CaptureRecord`, two-axis state machine in `startBurst`/`finishBurst`, schemaVersion bumped to `aurex-session-1.2`, `app_version` bumped to `3.0.0` |

No existing protocol behaviour changed. CALIBRATION, REPETITION,
SYMMETRY, LOW_LIGHT all still write `axisLabel: null` and target 30
frames. POLARIZATION_PAIR targets 60 frames split 30/30 across axes.

## Two-axis flow

1. User taps **Polarization Pair** → instructions panel shows the new copy.
2. User points the lens at a glass / shiny / wet / display surface
   and taps **CAPTURE**.
3. Harness captures 30 frames tagged `axisLabel = "0deg"`.
4. Status flips to: `Axis 0 done. Rotate phone 90° clockwise around the
   lens axis, then tap CAPTURE for axis 90.`
5. User physically rotates the phone 90° (the lens stays pointed at
   the same surface) and taps **CAPTURE** again.
6. Harness captures 30 more frames tagged `axisLabel = "90deg"`,
   appended to the same `captureLog`.
7. **EXPORT** writes a single `.aurex-session` zip with all 60 frames
   and a manifest where every frame carries its axis label.

## Schema bump

`SessionManifest.schemaVersion` advanced from `aurex-session-1.1` to
`aurex-session-1.2`. The only payload-shape change is that
`frames[i].axisLabel` may now be a non-null string. Older readers that
ignore unknown fields will see the same shape they always did for the
four older protocols.

## Workbench bridge readiness

`vision_bridge.py` already branches on `axisLabel`:

```python
if any(str(a) in ("0", "0deg") for a in axis_labels) and \
   any(str(a) in ("90", "90deg") for a in axis_labels):
    idx_0  = [...]
    idx_90 = [...]
    cap0  = mean(frames[idx_0])
    cap90 = mean(frames[idx_90])
    bundle.add_value("cap_axis_0",  "image", cap0,  ...)
    bundle.add_value("cap_axis_90", "image", cap90, ...)
```

The harness writes `"0deg"` / `"90deg"` exactly. The polarization
predicates over `cap_axis_0` and `cap_axis_90` will populate as soon
as a v3.0 session lands.

## Build + install

Built and installed via Android Studio's Run button against the
connected Samsung S23 (samsung SM-S918U). Initial v3.0 install
reported by the IDE: **4 s 414 ms**. APK present on phone as
`com.aurexis.harness`.

## v3.0.1 hotfix — orientation-change activity restart

First field test surfaced a real bug: physically rotating the phone
90 deg between the two bursts triggered Android's default
configuration-change behaviour, which **destroys and recreates
MainActivity**. That wiped `captureLog` and `polAxis0Done` mid-
protocol, so axis-90 was treated as a fresh axis-0 and the original
30 frames were lost.

Fix in `AndroidManifest.xml`:

```xml
<activity
    android:name=".MainActivity"
    android:exported="true"
    android:screenOrientation="portrait"
    android:configChanges="orientation|screenSize|screenLayout|keyboardHidden|smallestScreenSize|uiMode">
```

Two layers of defence:

1. `screenOrientation="portrait"` — the system never rotates the UI,
   so physically rotating the phone leaves the activity untouched.
2. `configChanges="..."` — even if some other config delta arrives
   (keyboard, smallestScreenSize), Android calls
   `onConfigurationChanged()` instead of recreating the activity.

`app_version` bumped from `3.0.0` to `3.0.1` so manifests in captured
sessions tag which build produced them. Re-installed on Samsung S23
in **1 s 31 ms**.

## What is *not* done in this round

* No real polarization-pair session has been captured yet — that's
  the next step on the user side. A Round 24 IR re-run will pick up
  any change to `has_polarization_signal` once one exists.
* Raw Bayer (DNG) capture is still deferred. That requires migrating
  this code from CameraX to Camera2 RAW_SENSOR, which is a separate
  v3.1 round.
* Multispectral / IR / UV capture remains genuinely hardware-blocked
  on the Samsung S23 lens stack and is not in scope.
