/**
 * Phoxelis Frame Quality Gate v0.1 — JavaScript port
 *
 * Re-implements the Round 30 Python gate as pure JS for inlining in
 * the V2.1 decode pipeline (aurexis_ed_v2_unified.html). The gate
 * scores a single camera frame in [0, 1] using five Phoxelis
 * predicates composed multiplicatively. Frames below threshold get
 * skipped before Bayesian occupancy fusion, fixing the YELLOW
 * "blind averaging bakes in errors from bad frames" item from the
 * Donald handoff.
 *
 * Inputs:
 *   imgData : Uint8ClampedArray | Uint8Array — RGBA pixel buffer
 *             (length = W*H*4), as produced by canvas.getImageData
 *   W, H    : image dimensions
 *
 * Output:
 *   { score, passed, failed, blocked, reasoning }
 *     score ∈ [0, 1]
 *     passed/failed: array of component names
 *     reasoning: array of human-readable lines
 *
 * No DOM dependency, no browser APIs. Node-compatible. Scores match
 * the Python implementation in aurexis_workbench/frame_quality.py
 * within rounding error (formulas are identical; pixel resampling
 * may differ slightly).
 *
 * © 2026 Vincent Anderson — Phoxelis. All rights reserved.
 */
"use strict";

// --------------------------------------------------------------------------
// Component definitions — must match Python COMPONENTS table exactly
// --------------------------------------------------------------------------
const COMPONENTS = [
  { name: "has_overexposed_regions",  badWhen: true,  weight: 0.85,
    desc: "overexposed (clipped highlights)" },
  { name: "has_underexposed_regions", badWhen: true,  weight: 0.85,
    desc: "underexposed (clipped shadows)" },
  { name: "has_uniform_focus",        badWhen: false, weight: 0.70,
    desc: "non-uniform focus (motion or DOF blur)" },
  { name: "has_specular_highlights",  badWhen: true,  weight: 0.85,
    desc: "specular highlights (glare / mirror-like)" },
  // has_subframe_motion is omitted in single-frame JS — the V2
  // pipeline already operates on individual capture frames, and
  // burst-temporal variance is not available at this stage.
];

// Predicate parameter constants (must match vocab.aurex thresholds)
const OVEREXPOSED_LUMA_THRESH    = 0.97;
const OVEREXPOSED_FRAC_THRESH    = 0.05;
const UNDEREXPOSED_LUMA_THRESH   = 0.03;
const UNDEREXPOSED_FRAC_THRESH   = 0.05;
const FOCUS_GRADIENT_THRESH      = 0.20;   // |grad| < this => uniform
const SPECULAR_LUMA_THRESH       = 0.92;
const SPECULAR_SPOT_COUNT_THRESH = 3;       // > this => has specular highlights

// --------------------------------------------------------------------------
// Image utilities
// --------------------------------------------------------------------------

/**
 * RGBA buffer -> normalised luma Float64Array in [0, 1].
 * Uses the same 0.299/0.587/0.114 weights as the Python pipeline.
 */
function rgbaToLuma(imgData, W, H) {
  const out = new Float64Array(W * H);
  for (let i = 0; i < W * H; i++) {
    const j = i * 4;
    out[i] = (0.299 * imgData[j] + 0.587 * imgData[j + 1] + 0.114 * imgData[j + 2]) / 255.0;
  }
  return out;
}

/**
 * Optional resize: downsample by integer step so long side <= maxLong.
 * Matches the Python pipeline's `step = max(1, long_side // resize_to)`.
 */
function resampleLuma(luma, W, H, maxLong) {
  const longSide = Math.max(W, H);
  if (longSide <= maxLong) return { luma, W, H };
  const step = Math.max(1, Math.floor(longSide / maxLong));
  const newW = Math.floor(W / step);
  const newH = Math.floor(H / step);
  const out = new Float64Array(newW * newH);
  for (let y = 0; y < newH; y++) {
    for (let x = 0; x < newW; x++) {
      out[y * newW + x] = luma[y * step * W + x * step];
    }
  }
  return { luma: out, W: newW, H: newH };
}

// --------------------------------------------------------------------------
// Operator: bright_pixel_fraction(image, threshold)
// --------------------------------------------------------------------------
function brightPixelFraction(luma, threshold) {
  let count = 0;
  for (let i = 0; i < luma.length; i++) if (luma[i] > threshold) count++;
  return count / luma.length;
}

// --------------------------------------------------------------------------
// Operator: dark_pixel_fraction(image, threshold)
// --------------------------------------------------------------------------
function darkPixelFraction(luma, threshold) {
  let count = 0;
  for (let i = 0; i < luma.length; i++) if (luma[i] < threshold) count++;
  return count / luma.length;
}

// --------------------------------------------------------------------------
// Sobel-ish gradients (matches Python _gradients used by focus_blur_gradient)
// --------------------------------------------------------------------------
function gradientsAbs(luma, W, H) {
  // Forward differences with edge replication; we only need magnitude here.
  const mag = new Float64Array(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const xp = x + 1 < W ? x + 1 : x;
      const yp = y + 1 < H ? y + 1 : y;
      const gx = luma[y * W + xp] - luma[i];
      const gy = luma[yp * W + x] - luma[i];
      mag[i] = Math.sqrt(gx * gx + gy * gy);
    }
  }
  return mag;
}

// --------------------------------------------------------------------------
// Operator: focus_blur_gradient(image)
// Center-vs-edge sharpness ratio. (centerMean - edgeMean) / (centerMean + edgeMean).
// Range roughly [-1, 1]. Near 0 = uniform sharpness.
// --------------------------------------------------------------------------
function focusBlurGradient(luma, W, H) {
  if (H < 16 || W < 16) return 0.0;
  const mag = gradientsAbs(luma, W, H);
  const cy0 = Math.floor(H / 4), cy1 = Math.floor(3 * H / 4);
  const cx0 = Math.floor(W / 4), cx1 = Math.floor(3 * W / 4);
  let centerSum = 0, fullSum = 0;
  for (let i = 0; i < mag.length; i++) fullSum += mag[i];
  for (let y = cy0; y < cy1; y++) {
    for (let x = cx0; x < cx1; x++) centerSum += mag[y * W + x];
  }
  const centerPixels = (cy1 - cy0) * (cx1 - cx0);
  const edgePixels = mag.length - centerPixels;
  if (edgePixels <= 0 || centerPixels <= 0) return 0.0;
  const centerMean = centerSum / centerPixels;
  const edgeMean   = (fullSum - centerSum) / edgePixels;
  if (centerMean + edgeMean < 1e-12) return 0.0;
  return (centerMean - edgeMean) / (centerMean + edgeMean);
}

// --------------------------------------------------------------------------
// Operator: bright_spot_count(image, threshold)
// Connected-component count over the brightness mask. Uses union-find for
// 4-connected labeling. Filters tiny (>=1px) and small (<=20px or 1/1000 of
// image area, whichever is larger) components — matches Python.
// --------------------------------------------------------------------------
function brightSpotCount(luma, W, H, threshold) {
  // Build binary mask
  const N = W * H;
  const mask = new Uint8Array(N);
  let any = 0;
  for (let i = 0; i < N; i++) {
    if (luma[i] > threshold) { mask[i] = 1; any = 1; }
  }
  if (!any) return 0;

  // Union-find
  const parent = new Int32Array(N);
  for (let i = 0; i < N; i++) parent[i] = i;
  const find = (a) => {
    while (parent[a] !== a) { parent[a] = parent[parent[a]]; a = parent[a]; }
    return a;
  };
  const union = (a, b) => {
    const ra = find(a), rb = find(b);
    if (ra !== rb) parent[ra] = rb;
  };

  // 4-connected scan; check left and up neighbors
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      if (!mask[i]) continue;
      if (x > 0 && mask[i - 1])     union(i, i - 1);
      if (y > 0 && mask[i - W])     union(i, i - W);
    }
  }

  // Count component sizes
  const sizes = new Map();
  for (let i = 0; i < N; i++) {
    if (!mask[i]) continue;
    const r = find(i);
    sizes.set(r, (sizes.get(r) || 0) + 1);
  }

  // Filter: keep components in [1, max_size] where max_size = max(20, N/1000)
  const maxSize = Math.max(20, Math.floor(N / 1000));
  let count = 0;
  for (const sz of sizes.values()) {
    if (sz >= 1 && sz <= maxSize) count++;
  }
  return count;
}

// --------------------------------------------------------------------------
// The five predicates the gate composes
// --------------------------------------------------------------------------

function hasOverexposedRegions(luma) {
  return brightPixelFraction(luma, OVEREXPOSED_LUMA_THRESH) > OVEREXPOSED_FRAC_THRESH;
}

function hasUnderexposedRegions(luma) {
  return darkPixelFraction(luma, UNDEREXPOSED_LUMA_THRESH) > UNDEREXPOSED_FRAC_THRESH;
}

function hasUniformFocus(luma, W, H) {
  return Math.abs(focusBlurGradient(luma, W, H)) < FOCUS_GRADIENT_THRESH;
}

function hasSpecularHighlights(luma, W, H) {
  return brightSpotCount(luma, W, H, SPECULAR_LUMA_THRESH) > SPECULAR_SPOT_COUNT_THRESH;
}

// --------------------------------------------------------------------------
// The composed gate
// --------------------------------------------------------------------------

/**
 * Score a single frame.
 *
 * @param {Uint8ClampedArray|Uint8Array} imgData  RGBA pixel buffer
 * @param {number} W  image width
 * @param {number} H  image height
 * @param {object} [opts]
 * @param {number} [opts.resize=320]  downsample long side before scoring
 * @returns {{ score: number, passed: string[], failed: string[],
 *             blocked: string[], reasoning: string[] }}
 */
function scoreFrame(imgData, W, H, opts) {
  opts = opts || {};
  const resize = opts.resize || 320;
  let luma = rgbaToLuma(imgData, W, H);
  ({ luma, W, H } = resampleLuma(luma, W, H, resize));

  // Evaluate each component
  const verdicts = {
    has_overexposed_regions:  hasOverexposedRegions(luma),
    has_underexposed_regions: hasUnderexposedRegions(luma),
    has_uniform_focus:        hasUniformFocus(luma, W, H),
    has_specular_highlights:  hasSpecularHighlights(luma, W, H),
  };

  let score = 1.0;
  const passed = [], failed = [], blocked = [], reasoning = [];

  for (const c of COMPONENTS) {
    const v = verdicts[c.name];
    if (typeof v !== "boolean") {
      blocked.push(c.name);
      reasoning.push(`BLOCKED  ${c.name}`);
      continue;
    }
    const isBad = (v === c.badWhen);
    if (isBad) {
      score *= (1.0 - c.weight);
      failed.push(c.name);
      reasoning.push(`FAIL     ${c.name} = ${v}  (${c.desc})`);
    } else {
      passed.push(c.name);
      reasoning.push(`pass     ${c.name} = ${v}`);
    }
  }
  return { score, passed, failed, blocked, reasoning };
}

// --------------------------------------------------------------------------
// Convenience: per-component getters (for callers that want raw verdicts)
// --------------------------------------------------------------------------
function evaluateAll(imgData, W, H, opts) {
  opts = opts || {};
  const resize = opts.resize || 320;
  let luma = rgbaToLuma(imgData, W, H);
  ({ luma, W, H } = resampleLuma(luma, W, H, resize));
  return {
    has_overexposed_regions:  hasOverexposedRegions(luma),
    has_underexposed_regions: hasUnderexposedRegions(luma),
    has_uniform_focus:        hasUniformFocus(luma, W, H),
    has_specular_highlights:  hasSpecularHighlights(luma, W, H),
    bright_pixel_fraction_097: brightPixelFraction(luma, OVEREXPOSED_LUMA_THRESH),
    dark_pixel_fraction_003:   darkPixelFraction(luma, UNDEREXPOSED_LUMA_THRESH),
    focus_blur_gradient:       focusBlurGradient(luma, W, H),
    bright_spot_count_092:     brightSpotCount(luma, W, H, SPECULAR_LUMA_THRESH),
  };
}

// --------------------------------------------------------------------------
// Module exports (Node) + global hook (browser)
// --------------------------------------------------------------------------
const PhoxelisFrameQuality = {
  scoreFrame,
  evaluateAll,
  COMPONENTS,
  // Exposed for tests / debugging:
  rgbaToLuma,
  resampleLuma,
  brightPixelFraction,
  darkPixelFraction,
  focusBlurGradient,
  brightSpotCount,
  hasOverexposedRegions,
  hasUnderexposedRegions,
  hasUniformFocus,
  hasSpecularHighlights,
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = PhoxelisFrameQuality;
}
if (typeof window !== "undefined") {
  window.PhoxelisFrameQuality = PhoxelisFrameQuality;
}
