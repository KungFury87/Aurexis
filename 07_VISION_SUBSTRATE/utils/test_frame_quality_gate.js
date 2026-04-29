/**
 * Node test for the JS port of the Phoxelis frame-quality gate.
 *
 * Generates the same six synthetic frames as Round 31 (Python) and
 * verifies the JS gate produces the right verdicts and score bands.
 * The synthetic generators here are deterministic LCG-seeded so
 * re-runs reproduce exactly. Pixel values won't match Python's numpy
 * output byte-for-byte (different RNG), but the structural assertions
 * — which predicates fire, what bucket the score lands in — must
 * agree.
 *
 * Run:
 *     node test_frame_quality_gate.js
 *
 * Exit code 0 if all cases pass, 1 otherwise.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const FQ = require("./frame_quality_gate");

// --------------------------------------------------------------------------
// Deterministic RNG (LCG, good enough for reproducible test data)
// --------------------------------------------------------------------------
function makeRNG(seed) {
  let s = (seed >>> 0) || 1;
  return {
    int: (lo, hi) => {  // [lo, hi)
      s = (s * 1664525 + 1013904223) >>> 0;
      return lo + (s % (hi - lo));
    },
    f01: () => {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    },
    normal: function (mu, sigma) {
      const u = this.f01() || 1e-12, v = this.f01();
      return mu + sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    },
  };
}

// --------------------------------------------------------------------------
// Synthetic-frame generators — match Round 31 cases conceptually
// --------------------------------------------------------------------------

function clamp8(v) { return v < 0 ? 0 : (v > 255 ? 255 : Math.round(v)); }

function makeRGBA(W, H) {
  const buf = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) buf[i * 4 + 3] = 255;
  return buf;
}

function fillRect(buf, W, H, y0, x0, h, w, r, g, b) {
  for (let y = y0; y < y0 + h && y < H; y++) {
    for (let x = x0; x < x0 + w && x < W; x++) {
      const j = (y * W + x) * 4;
      buf[j] = r; buf[j + 1] = g; buf[j + 2] = b;
    }
  }
}

function genCleanReference(size, seed) {
  const rng = makeRNG(seed || 42);
  const buf = makeRGBA(size, size);
  for (let i = 0; i < size * size; i++) {
    const j = i * 4;
    buf[j] = 128; buf[j + 1] = 128; buf[j + 2] = 128;
  }
  for (let k = 0; k < 8; k++) {
    const y = rng.int(20, size - 60), x = rng.int(20, size - 60);
    const h = rng.int(30, 50), w = rng.int(30, 50);
    fillRect(buf, size, size, y, x, h, w,
             rng.int(60, 200), rng.int(60, 200), rng.int(60, 200));
  }
  // Mild noise
  for (let i = 0; i < size * size; i++) {
    const j = i * 4;
    buf[j]     = clamp8(buf[j]     + rng.normal(0, 4));
    buf[j + 1] = clamp8(buf[j + 1] + rng.normal(0, 4));
    buf[j + 2] = clamp8(buf[j + 2] + rng.normal(0, 4));
  }
  return { buf, W: size, H: size, label: "clean_reference" };
}

function genOverexposed(size, seed) {
  const rng = makeRNG(seed || 43);
  const buf = makeRGBA(size, size);
  // Mid-tone background
  for (let i = 0; i < size * size; i++) {
    const j = i * 4;
    buf[j]     = rng.int(60, 200);
    buf[j + 1] = rng.int(60, 200);
    buf[j + 2] = rng.int(60, 200);
  }
  // Top 60% saturated to near-max
  const bandH = Math.floor(size * 0.6);
  for (let y = 0; y < bandH; y++) {
    for (let x = 0; x < size; x++) {
      const j = (y * size + x) * 4;
      buf[j]     = rng.int(248, 256);
      buf[j + 1] = rng.int(248, 256);
      buf[j + 2] = rng.int(248, 256);
    }
  }
  return { buf, W: size, H: size, label: "overexposed" };
}

function genUnderexposed(size, seed) {
  const rng = makeRNG(seed || 44);
  const buf = makeRGBA(size, size);
  for (let i = 0; i < size * size; i++) {
    const j = i * 4;
    buf[j]     = rng.int(60, 200);
    buf[j + 1] = rng.int(60, 200);
    buf[j + 2] = rng.int(60, 200);
  }
  const bandH = Math.floor(size * 0.6);
  for (let y = 0; y < bandH; y++) {
    for (let x = 0; x < size; x++) {
      const j = (y * size + x) * 4;
      buf[j]     = rng.int(0, 7);
      buf[j + 1] = rng.int(0, 7);
      buf[j + 2] = rng.int(0, 7);
    }
  }
  return { buf, W: size, H: size, label: "underexposed" };
}

function genGlare(size, seed) {
  const rng = makeRNG(seed || 45);
  const buf = makeRGBA(size, size);
  for (let i = 0; i < size * size; i++) {
    const j = i * 4;
    buf[j]     = rng.int(50, 130);
    buf[j + 1] = rng.int(50, 130);
    buf[j + 2] = rng.int(50, 130);
  }
  // 6 small bright "specular" disks
  for (let k = 0; k < 6; k++) {
    const cy = rng.int(15, size - 15);
    const cx = rng.int(15, size - 15);
    const r = rng.int(4, 9);
    const r2 = r * r;
    for (let y = cy - r; y <= cy + r; y++) {
      for (let x = cx - r; x <= cx + r; x++) {
        if (y < 0 || y >= size || x < 0 || x >= size) continue;
        if ((y - cy) * (y - cy) + (x - cx) * (x - cx) >= r2) continue;
        const j = (y * size + x) * 4;
        buf[j] = 250; buf[j + 1] = 250; buf[j + 2] = 250;
      }
    }
  }
  return { buf, W: size, H: size, label: "glare" };
}

function genMotionBlur(size, seed) {
  // Reference frame, then 21-pixel horizontal box blur
  const ref = genCleanReference(size, seed || 46).buf;
  const k = 21, pad = (k - 1) >> 1;
  const out = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      let sR = 0, sG = 0, sB = 0;
      for (let dx = -pad; dx <= pad; dx++) {
        const xx = Math.min(size - 1, Math.max(0, x + dx));
        const j = (y * size + xx) * 4;
        sR += ref[j]; sG += ref[j + 1]; sB += ref[j + 2];
      }
      const o = (y * size + x) * 4;
      out[o] = sR / k; out[o + 1] = sG / k; out[o + 2] = sB / k; out[o + 3] = 255;
    }
  }
  return { buf: out, W: size, H: size, label: "motion_blur" };
}

function genMultiProblem(size, seed) {
  const oe = genOverexposed(size, seed || 47).buf;
  const rng = makeRNG((seed || 47) + 100);
  // Overlay 8 glare spots
  for (let k = 0; k < 8; k++) {
    const cy = rng.int(15, size - 15);
    const cx = rng.int(15, size - 15);
    const r = rng.int(4, 9);
    const r2 = r * r;
    for (let y = cy - r; y <= cy + r; y++) {
      for (let x = cx - r; x <= cx + r; x++) {
        if (y < 0 || y >= size || x < 0 || x >= size) continue;
        if ((y - cy) * (y - cy) + (x - cx) * (x - cx) >= r2) continue;
        const j = (y * size + x) * 4;
        oe[j] = 254; oe[j + 1] = 254; oe[j + 2] = 254;
      }
    }
  }
  return { buf: oe, W: size, H: size, label: "multi_problem" };
}

// --------------------------------------------------------------------------
// Test cases — must match Round 31 expectations
// --------------------------------------------------------------------------
const SIZE = 256;
const CASES = [
  // [generator, mustFailSubset, [scoreLow, scoreHigh]]
  [genCleanReference, [],                                           [0.85, 1.001]],
  [genOverexposed,    ["has_overexposed_regions"],                  [0.0, 0.30]],
  [genUnderexposed,   ["has_underexposed_regions"],                 [0.0, 0.30]],
  [genGlare,          ["has_specular_highlights"],                  [0.0, 0.30]],
  [genMotionBlur,     [],                                           [0.0, 1.001]],  // not enforced
  [genMultiProblem,   ["has_overexposed_regions",
                       "has_specular_highlights"],                  [0.0, 0.05]],
];

function runTests() {
  console.log("\n  case                     score    expected             result");
  console.log("  " + "-".repeat(72));

  let nPass = 0;
  for (const [gen, mustFail, [lo, hi]] of CASES) {
    const frame = gen(SIZE);
    const result = FQ.scoreFrame(frame.buf, frame.W, frame.H);
    const failedSet = new Set(result.failed);
    const missing = mustFail.filter((p) => !failedSet.has(p));
    const scoreOk = result.score >= lo && result.score <= hi;
    const failsOk = missing.length === 0;
    const ok = scoreOk && failsOk;
    if (ok) nPass++;
    let status = ok ? "PASS" : "FAIL";
    if (!ok) {
      if (!scoreOk) status += `  (score outside [${lo.toFixed(2)}, ${hi.toFixed(2)}])`;
      if (!failsOk) status += `  (missing fails: ${missing.join(",")})`;
    }
    const expected = mustFail.length ? mustFail.join(",").slice(0, 18) : "pass-all";
    console.log(`  ${frame.label.padEnd(22)} ${result.score.toFixed(3).padStart(7)}  ` +
                `${expected.padEnd(18)}  ${status}`);
    if (result.failed.length) {
      console.log(`  ${" ".repeat(22)} ${" ".repeat(7)}  failed: ${result.failed.join(", ")}`);
    }
  }
  console.log("  " + "-".repeat(72));
  console.log(`  verified: ${nPass}/${CASES.length}\n`);
  return nPass === CASES.length ? 0 : 1;
}

const rc = runTests();
process.exit(rc);
