/**
 * Aurexis Core V2 — Format definitions, layout computation, format estimation
 *
 * Extracted from aurexis_ed_unified.html (v12).
 * Pure JS, no DOM dependencies. Node-compatible.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

const { computeHomography, applyHomography } = require("./homography");

// --------------------------------------------------------------------------
// HD Configs — grid dimensions, color counts, bits per module, canvas sizes
// --------------------------------------------------------------------------
const HD_CONFIGS = {
  "128x128-4c":    { grid: 128,  colors: 4,  bpm: 2, canvasPx: 1136 },
  "192x192-4c":    { grid: 192,  colors: 4,  bpm: 2, canvasPx: 1648 },
  "256x256-4c":    { grid: 256,  colors: 4,  bpm: 2, canvasPx: 2160 },
  "384x384-4c":    { grid: 384,  colors: 4,  bpm: 2, canvasPx: 3184 },
  "512x512-4c":    { grid: 512,  colors: 4,  bpm: 2, canvasPx: 4208 },
  "128x128-8c":    { grid: 128,  colors: 8,  bpm: 3, canvasPx: 1420 },
  "192x192-8c":    { grid: 192,  colors: 8,  bpm: 3, canvasPx: 2060 },
  "256x256-8c":    { grid: 256,  colors: 8,  bpm: 3, canvasPx: 2700 },
  "384x384-8c":    { grid: 384,  colors: 8,  bpm: 3, canvasPx: 3980 },
  "768x768-4c":    { grid: 768,  colors: 4,  bpm: 2, canvasPx: 6256 },
  "1024x1024-4c":  { grid: 1024, colors: 4,  bpm: 2, canvasPx: 8304 },
  "1536x1536-4c":  { grid: 1536, colors: 4,  bpm: 2, canvasPx: 12400 },
  "1792x1792-4c":  { grid: 1792, colors: 4,  bpm: 2, canvasPx: 14448 },
  "2048x2048-4c":  { grid: 2048, colors: 4,  bpm: 2, canvasPx: 16496 },
  "256x256-16c":   { grid: 256,  colors: 16, bpm: 4, canvasPx: 4320 },
  "384x384-16c":   { grid: 384,  colors: 16, bpm: 4, canvasPx: 6368 },
  "512x512-16c":   { grid: 512,  colors: 16, bpm: 4, canvasPx: 8416 },
};

// Standard L2 constants
const L2_CANVAS_PX = 1024;
const L2_GRID_MODULES = 48;

// --------------------------------------------------------------------------
// Symbol layout computation
// --------------------------------------------------------------------------

/**
 * Compute the physical layout of a symbol given its data grid size and canvas px.
 *
 * Layout anatomy:
 *   quietZone (1 mod) | finder (7 mod) | timing (1 mod) | data (grid mod) |
 *   timing (1 mod) | finder (7 mod) | quietZone (1 mod)
 *
 * totalMod = grid + 16 (2 quiet + 2×7 finder + ... but empirically grid+16 from source)
 *
 * @param {number} dataModules - grid dimension (e.g. 128 for 128x128)
 * @param {number} canvasPx - canvas pixel size
 * @returns {object} layout with modPx, qzPx, totalMod, dataOriginPx
 */
function computeSymbolLayout(dataModules, canvasPx) {
  const totalMod = dataModules + 16; // grid + 2*(finder7 + separator1)
  const qzPx = Math.round(canvasPx * 0.03); // quiet zone: 3% of canvas
  const symbolPx = canvasPx - 2 * qzPx;
  const modPx = symbolPx / totalMod;
  const dataOriginPx = qzPx + 8 * modPx; // after quiet + finder(7) + separator(1)
  return { modPx, qzPx, totalMod, symbolPx, dataOriginPx, canvasPx, dataModules };
}

/**
 * Compute canonical finder center points for a given layout.
 * Finder centers are at module position 3.5 from the edge (center of 7-module finder).
 *
 * @param {object} layout - from computeSymbolLayout
 * @returns {Array<{x:number,y:number}>} [TL, TR, BL, BR] canonical points
 */
function computeCanonicalFinderPoints(layout) {
  const { qzPx, modPx, totalMod } = layout;
  return [
    { x: qzPx + 3.5 * modPx, y: qzPx + 3.5 * modPx },
    { x: qzPx + (totalMod - 3.5) * modPx, y: qzPx + 3.5 * modPx },
    { x: qzPx + 3.5 * modPx, y: qzPx + (totalMod - 3.5) * modPx },
    { x: qzPx + (totalMod - 3.5) * modPx, y: qzPx + (totalMod - 3.5) * modPx },
  ];
}

/**
 * Calculate HD capacity for a config.
 * @param {object} config - HD config entry
 * @returns {object} { totalModules, rawBytes, dataBytes, rawBits }
 */
function hdCalcCapacity(config) {
  const totalModules = config.grid * config.grid;
  const rawBits = totalModules * config.bpm;
  const rawBytes = Math.floor(rawBits / 8);
  // numBlocks must use floor to match hdRsEncode/hdRsDecode — the RS frame
  // must fit entirely within the module grid's byte capacity.
  const blockSize = 255;
  const numBlocks = Math.max(1, Math.floor(rawBytes / blockSize));
  const blockK = blockSize - 32; // 223 data bytes per block
  const dataBytes = blockK * numBlocks;
  return { totalModules, rawBytes, dataBytes, rawBits, numBlocks };
}

// --------------------------------------------------------------------------
// Format estimation — try-all-configs scoring
// --------------------------------------------------------------------------

/**
 * Score a candidate config's timing strip accuracy using a homography.
 *
 * Given finder positions in image space and a candidate config, compute a
 * homography from canonical → image, then sample timing strip positions and
 * check B/W alternation.
 *
 * @param {object} fids - { TL, TR, BL, BR } finder positions in image space
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA image data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {object} config - HD config entry
 * @returns {{ score: number, ok: number, bad: number, totalMod: number }|null}
 */
function scoreConfigTiming(fids, imgData, W, H, config) {
  const layout = computeSymbolLayout(config.grid, config.canvasPx);
  const canonPts = computeCanonicalFinderPoints(layout);
  const sourcePts = [fids.TL, fids.TR, fids.BL, fids.BR];
  const Hmat = computeHomography(canonPts, sourcePts);
  if (!Hmat) return null;

  const { qzPx, modPx, totalMod } = layout;
  let ok = 0, bad = 0;
  const step = Math.max(1, Math.floor((totalMod - 15) / 30));

  // Horizontal timing strip: row 6, cols 8 to totalMod-8
  for (let m = 8; m < totalMod - 7; m += step) {
    const cx = qzPx + m * modPx + modPx / 2;
    const cy = qzPx + 6 * modPx + modPx / 2;
    const sp = applyHomography(Hmat, { x: cx, y: cy });
    const rx = Math.round(sp.x), ry = Math.round(sp.y);
    if (rx < 0 || ry < 0 || rx >= W || ry >= H) continue;
    const idx = (ry * W + rx) * 4;
    const lum = 0.299 * imgData[idx] + 0.587 * imgData[idx + 1] + 0.114 * imgData[idx + 2];
    const isDark = lum < 128;
    const shouldBeDark = (m % 2 === 0);
    if (isDark === shouldBeDark) ok++; else bad++;
  }

  // Vertical timing strip: col 6, rows 8 to totalMod-8
  for (let m = 8; m < totalMod - 7; m += step) {
    const cx = qzPx + 6 * modPx + modPx / 2;
    const cy = qzPx + m * modPx + modPx / 2;
    const sp = applyHomography(Hmat, { x: cx, y: cy });
    const rx = Math.round(sp.x), ry = Math.round(sp.y);
    if (rx < 0 || ry < 0 || rx >= W || ry >= H) continue;
    const idx = (ry * W + rx) * 4;
    const lum = 0.299 * imgData[idx] + 0.587 * imgData[idx + 1] + 0.114 * imgData[idx + 2];
    const isDark = lum < 128;
    const shouldBeDark = (m % 2 === 0);
    if (isDark === shouldBeDark) ok++; else bad++;
  }

  const total = ok + bad;
  const score = total > 0 ? ok / total : 0;
  return { score, ok, bad, totalMod };
}

/**
 * Estimate artifact format by trying each candidate HD config.
 *
 * @param {object} fids - { TL, TR, BL, BR } finder positions
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA image data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {object} [opts] - options
 * @param {string[]} [opts.candidates] - config names to try (default: 4c sweep)
 * @param {number} [opts.minScore] - minimum timing score to accept (default: 0.70)
 * @returns {object|null} { config, name, score, totalMod } or null
 */
function estimateFormat(fids, imgData, W, H, opts = {}) {
  const candidates = opts.candidates || [
    "128x128-4c", "192x192-4c", "256x256-4c", "384x384-4c", "512x512-4c",
  ];
  const minScore = opts.minScore || 0.70;

  // Quick reject: if quad is too small, likely standard L2
  const avgSide = (
    Math.hypot(fids.TR.x - fids.TL.x, fids.TR.y - fids.TL.y) +
    Math.hypot(fids.BL.x - fids.TL.x, fids.BL.y - fids.TL.y)
  ) / 2;
  if (avgSide < 200) return null;

  let bestScore = -1, bestConfig = null, bestName = "", bestTotalMod = 0;

  for (const name of candidates) {
    const cfg = HD_CONFIGS[name];
    if (!cfg) continue;
    const result = scoreConfigTiming(fids, imgData, W, H, cfg);
    if (!result) continue;
    if (result.score > bestScore) {
      bestScore = result.score;
      bestConfig = cfg;
      bestName = name;
      bestTotalMod = result.totalMod;
    }
  }

  if (bestScore < minScore || !bestConfig) return null;

  return {
    config: bestConfig,
    name: bestName,
    score: bestScore,
    totalMod: bestTotalMod,
    dataModules: bestConfig.grid,
  };
}

module.exports = {
  HD_CONFIGS,
  L2_CANVAS_PX, L2_GRID_MODULES,
  computeSymbolLayout,
  computeCanonicalFinderPoints,
  hdCalcCapacity,
  scoreConfigTiming,
  estimateFormat,
};
