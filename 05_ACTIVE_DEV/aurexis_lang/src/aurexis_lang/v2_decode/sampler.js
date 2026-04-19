/**
 * Aurexis Core V2 — Module sampling, color classification, frame fusion
 *
 * Extracted from aurexis_ed_unified.html (v12).
 * Pure JS, no DOM dependencies. Node-compatible.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

// --------------------------------------------------------------------------
// Color palettes
// --------------------------------------------------------------------------
const HD_PALETTE_4 = [
  [255, 255, 255], // 0 white
  [255, 0,   0  ], // 1 red
  [0,   0,   255], // 2 blue
  [0,   128, 0  ], // 3 green
];

const HD_PALETTE_8 = [
  [255, 255, 255], // 0 white
  [255, 0,   0  ], // 1 red
  [0,   0,   255], // 2 blue
  [0,   200, 0  ], // 3 green (brighter for camera)
  [255, 255, 0  ], // 4 yellow
  [255, 0,   255], // 5 magenta
  [0,   255, 255], // 6 cyan
  [0,   0,   0  ], // 7 black (replaces orange — max distance)
];

const HD_PALETTE_16 = [
  [255, 255, 255], [255, 0,   0  ], [0,   0,   255], [0,   255, 0  ],
  [255, 255, 0  ], [255, 0,   255], [0,   255, 255], [255, 128, 0  ],
  [128, 0,   255], [0,   128, 0  ], [128, 128, 128], [0,   0,   0  ],
  [255, 128, 128], [128, 255, 128], [128, 128, 255], [192, 192, 0  ],
];

function hdGetPalette(numColors) {
  if (numColors <= 4) return HD_PALETTE_4;
  if (numColors <= 8) return HD_PALETTE_8;
  if (numColors <= 16) return HD_PALETTE_16;
  // For higher counts, generate evenly spaced HSV
  const pal = [];
  for (let i = 0; i < numColors; i++) {
    const hue = (i / numColors) * 360;
    const sat = 0.7 + 0.3 * ((i % 3) / 2);
    const val = 0.6 + 0.4 * ((i % 5) / 4);
    const c = val * sat, x = c * (1 - Math.abs(((hue / 60) % 2) - 1)), m = val - c;
    let r, g, b;
    if (hue < 60)       { r = c; g = x; b = 0; }
    else if (hue < 120) { r = x; g = c; b = 0; }
    else if (hue < 180) { r = 0; g = c; b = x; }
    else if (hue < 240) { r = 0; g = x; b = c; }
    else if (hue < 300) { r = x; g = 0; b = c; }
    else                { r = c; g = 0; b = x; }
    pal.push([Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)]);
  }
  return pal;
}

// --------------------------------------------------------------------------
// Sampling
// --------------------------------------------------------------------------

/**
 * Sample the average RGB in a square region around a pixel.
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA pixel data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {number} px - center x (float)
 * @param {number} py - center y (float)
 * @param {number} radius - sample radius
 * @returns {number[]} [r, g, b]
 */
function sampleAvg(imgData, W, H, px, py, radius) {
  const rx = Math.round(px), ry = Math.round(py);
  let r = 0, g = 0, b = 0, n = 0;
  for (let dy = -radius; dy <= radius; dy++) {
    for (let dx = -radius; dx <= radius; dx++) {
      const x = rx + dx, y = ry + dy;
      if (x < 0 || y < 0 || x >= W || y >= H) continue;
      const idx = (y * W + x) * 4;
      r += imgData[idx]; g += imgData[idx + 1]; b += imgData[idx + 2]; n++;
    }
  }
  return n > 0 ? [r / n, g / n, b / n] : [255, 255, 255];
}

function colorDistSq(a, b) {
  const dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2];
  return dr * dr + dg * dg + db * db;
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  let h = 0;
  if (d > 0) {
    if (max === r) h = 60 * (((g - b) / d + 6) % 6);
    else if (max === g) h = 60 * ((b - r) / d + 2);
    else h = 60 * ((r - g) / d + 4);
  }
  return [h, max === 0 ? 0 : d / max, max];
}

// --------------------------------------------------------------------------
// Classification
// --------------------------------------------------------------------------

/**
 * Classify a module by nearest-palette RGB distance.
 */
function classifyModuleRgb(rgb, palette) {
  palette = palette || HD_PALETTE_4;
  let best = 0, bestD = Infinity;
  for (let i = 0; i < palette.length; i++) {
    const d = colorDistSq(rgb, palette[i]);
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

/**
 * Classify a module using HSV heuristics (proven for 4-color L2).
 */
function classifyModuleHsv(rgb, palette) {
  palette = palette || HD_PALETTE_4;
  const [h, s, v] = rgbToHsv(rgb[0], rgb[1], rgb[2]);
  if (s < 0.18 && v > 0.35) return 0; // white
  if (v > 0.60 && s < 0.25) return 0; // white
  if (h >= 320 || h < 25) return 1;    // red
  if (h >= 195 && h < 305) return 2;   // blue
  if (h >= 75 && h < 175) return 3;    // green
  return classifyModuleRgb(rgb, palette);
}

/**
 * Soft (probabilistic) N-color classifier.
 */
function softClassifyN(rgb, palette, sigma) {
  sigma = sigma || 800;
  const N = palette.length;
  const probs = new Float32Array(N);
  const [r, g, b] = rgb;
  let sum = 0;
  for (let i = 0; i < N; i++) {
    const dr = r - palette[i][0], dg = g - palette[i][1], db = b - palette[i][2];
    const w = Math.exp(-(dr * dr + dg * dg + db * db) / sigma);
    probs[i] = w;
    sum += w;
  }
  if (sum > 0) for (let i = 0; i < N; i++) probs[i] /= sum;
  return probs;
}

// --------------------------------------------------------------------------
// Module data packing
// --------------------------------------------------------------------------

function hdPackModules(modules, bpm) {
  const totalBits = modules.length * bpm;
  const bytes = new Uint8Array(Math.ceil(totalBits / 8));
  let bitPos = 0;
  for (let i = 0; i < modules.length; i++) {
    const val = modules[i];
    const byteIdx = bitPos >> 3;
    const bitOff = bitPos & 7;
    if (bitOff + bpm <= 8) {
      bytes[byteIdx] |= (val << (8 - bitOff - bpm));
    } else {
      const firstBits = 8 - bitOff;
      bytes[byteIdx] |= (val >> (bpm - firstBits));
      bytes[byteIdx + 1] |= ((val & ((1 << (bpm - firstBits)) - 1)) << (8 - (bpm - firstBits)));
    }
    bitPos += bpm;
  }
  return bytes;
}

function hdUnpackModules(bytes, totalModules, bpm) {
  const modules = new Uint8Array(totalModules);
  let bitPos = 0;
  const mask = (1 << bpm) - 1;
  for (let i = 0; i < totalModules; i++) {
    const byteIdx = bitPos >> 3;
    const bitOff = bitPos & 7;
    let val;
    if (bitOff + bpm <= 8) {
      val = (bytes[byteIdx] >> (8 - bitOff - bpm)) & mask;
    } else {
      const firstBits = 8 - bitOff;
      val = ((bytes[byteIdx] & ((1 << firstBits) - 1)) << (bpm - firstBits));
      val |= (bytes[byteIdx + 1] >> (8 - (bpm - firstBits))) & ((1 << (bpm - firstBits)) - 1);
    }
    modules[i] = val;
    bitPos += bpm;
  }
  return modules;
}

// --------------------------------------------------------------------------
// Frame fusion accumulator
// --------------------------------------------------------------------------

/**
 * Create a frame fusion accumulator for multi-frame evidence.
 * @param {number} totalModules - grid*grid
 * @returns {object} accumulator state
 */
function createFusionAccumulator(totalModules) {
  return {
    rgbAccum: new Float32Array(totalModules * 3),
    rgbCount: new Uint16Array(totalModules),
    framesSeen: 0,
  };
}

/**
 * Add one frame's module samples to the accumulator.
 * @param {object} accum - from createFusionAccumulator
 * @param {Array<number[]>} moduleRgbs - array of [r,g,b] per module
 */
function addFrameToAccumulator(accum, moduleRgbs) {
  for (let i = 0; i < moduleRgbs.length; i++) {
    const rgb = moduleRgbs[i];
    if (!rgb) continue;
    const base3 = i * 3;
    accum.rgbAccum[base3]     += rgb[0];
    accum.rgbAccum[base3 + 1] += rgb[1];
    accum.rgbAccum[base3 + 2] += rgb[2];
    accum.rgbCount[i]++;
  }
  accum.framesSeen++;
}

/**
 * Get consensus module classifications from accumulated evidence.
 * @param {object} accum - accumulator
 * @param {number} numColors - color count
 * @param {number[][]} palette - color palette
 * @returns {Uint8Array} module classifications
 */
function getConsensusModules(accum, numColors, palette) {
  const totalModules = accum.rgbCount.length;
  const modules = new Uint8Array(totalModules);
  for (let i = 0; i < totalModules; i++) {
    const n = accum.rgbCount[i];
    if (n === 0) continue;
    const base3 = i * 3;
    const avgR = accum.rgbAccum[base3] / n;
    const avgG = accum.rgbAccum[base3 + 1] / n;
    const avgB = accum.rgbAccum[base3 + 2] / n;

    if (numColors <= 4) {
      modules[i] = classifyModuleHsv([avgR, avgG, avgB], palette);
    } else {
      modules[i] = classifyModuleRgb([avgR, avgG, avgB], palette);
    }
  }
  return modules;
}

module.exports = {
  HD_PALETTE_4, HD_PALETTE_8, HD_PALETTE_16,
  hdGetPalette,
  sampleAvg, colorDistSq, rgbToHsv,
  classifyModuleRgb, classifyModuleHsv, softClassifyN,
  hdPackModules, hdUnpackModules,
  createFusionAccumulator, addFrameToAccumulator, getConsensusModules,
};
