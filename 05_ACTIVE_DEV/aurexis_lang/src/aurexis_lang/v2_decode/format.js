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
 * Compute alignment pattern center positions within the data grid.
 *
 * Alignment patterns are 3×3 module patterns (dark center, light ring, dark border)
 * placed on a regular grid within the data area. They provide distributed geometric
 * anchor points for local homography correction under perspective warp.
 *
 * Placement: centers are spaced approximately every `step` modules, avoiding the
 * edges (at least 4 modules from the data boundary). For gs=128 with step≈32,
 * this gives a 3×3 grid of alignment patterns = 9 anchors in the data region.
 *
 * @param {number} gs - grid size (data modules per axis)
 * @returns {{ centers: Array<{r:number, c:number}>, mask: Uint8Array, count: number }}
 *   centers: array of {r,c} center positions (data-grid-relative, 0-indexed)
 *   mask: gs*gs Uint8Array, 1 for modules occupied by alignment patterns
 *   count: total modules occupied
 */
function computeAlignmentPatternPositions(gs) {
  // Target spacing: place alignment centers ~every gs/4 modules, clamped to [24,64]
  const idealStep = Math.round(gs / 4);
  const step = Math.max(24, Math.min(64, idealStep));

  // Generate center positions: start at step/2, step to gs - step/2
  const starts = [];
  const margin = Math.max(4, Math.floor(step / 2));
  for (let p = margin; p < gs - margin + 1; p += step) {
    starts.push(p);
  }
  // Ensure we always have at least the endpoints
  if (starts.length === 0) return { centers: [], mask: new Uint8Array(gs * gs), count: 0 };
  if (starts[starts.length - 1] < gs - margin) starts.push(gs - margin);

  const centers = [];
  const mask = new Uint8Array(gs * gs);
  let count = 0;

  for (const cr of starts) {
    for (const cc of starts) {
      centers.push({ r: cr, c: cc });
      // Mark the 3×3 region around center
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          const mr = cr + dr, mc = cc + dc;
          if (mr >= 0 && mr < gs && mc >= 0 && mc < gs) {
            if (!mask[mr * gs + mc]) {
              mask[mr * gs + mc] = 1;
              count++;
            }
          }
        }
      }
    }
  }

  return { centers, mask, count };
}

/**
 * Get the 3×3 alignment pattern bitmap.
 * 1 = dark (black), 0 = light (white).
 * Pattern: dark ring, light inner, dark center — high contrast cross-hair.
 */
const ALIGNMENT_BITMAP = [
  [1, 1, 1],
  [1, 0, 1],
  [1, 1, 1],
];

// Actually, use inverted for better detectability (dark center, white ring, dark border
// makes a clear target visible against any color background):
const ALIGNMENT_PATTERN = [
  [0, 0, 0],
  [0, 1, 0],
  [0, 0, 0],
];

/**
 * Calculate HD capacity for a config, accounting for alignment pattern modules.
 *
 * @param {object} config - HD config entry
 * @param {object} [opts]
 * @param {number} [opts.nsym=32] - RS parity symbols per block (32=standard, 64=high-redundancy)
 * @returns {object} { totalModules, rawBytes, dataBytes, rawBits, numBlocks, alignInfo, nsym, blockK }
 */
function hdCalcCapacity(config, opts) {
  opts = opts || {};
  const nsym = opts.nsym || 32;
  const gs = config.grid;
  const alignInfo = computeAlignmentPatternPositions(gs);
  const dataModules = gs * gs - alignInfo.count;
  const rawBits = dataModules * config.bpm;
  const rawBytes = Math.floor(rawBits / 8);
  // numBlocks must use floor to match hdRsEncode/hdRsDecode — the RS frame
  // must fit entirely within the module grid's byte capacity.
  const blockSize = 255;
  const numBlocks = Math.max(1, Math.floor(rawBytes / blockSize));
  const blockK = blockSize - nsym;
  const dataBytes = blockK * numBlocks;
  return { totalModules: gs * gs, dataModules, rawBytes, dataBytes, rawBits, numBlocks, alignInfo, nsym, blockK };
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
  const candidates = opts.candidates || Object.keys(HD_CONFIGS);
  const minScore = opts.minScore || 0.70;

  // Quick reject: if quad is too small, likely standard L2
  const avgSide = (
    Math.hypot(fids.TR.x - fids.TL.x, fids.TR.y - fids.TL.y) +
    Math.hypot(fids.BL.x - fids.TL.x, fids.BL.y - fids.TL.y)
  ) / 2;
  if (avgSide < 200) return null;

  let bestScore = -1, bestConfig = null, bestName = "", bestTotalMod = 0;
  const allCandidates = [];

  // Compute actual finder quad side length for canvasPx tiebreaking
  const avgSideLen = (
    Math.hypot(fids.TR.x - fids.TL.x, fids.TR.y - fids.TL.y) +
    Math.hypot(fids.BL.x - fids.TL.x, fids.BL.y - fids.TL.y) +
    Math.hypot(fids.TR.x - fids.BR.x, fids.TR.y - fids.BR.y) +
    Math.hypot(fids.BL.x - fids.BR.x, fids.BL.y - fids.BR.y)
  ) / 4;

  for (const name of candidates) {
    const cfg = HD_CONFIGS[name];
    if (!cfg) continue;
    const result = scoreConfigTiming(fids, imgData, W, H, cfg);
    if (!result) continue;
    // Tiebreak: when timing scores are equal, prefer config whose canvasPx
    // best matches the actual image size. Finder-quad side ≈ canvasPx*(1-0.06)
    // (after quiet zone). Use ratio closeness as secondary score.
    const expectedSide = cfg.canvasPx * 0.94; // approximate after quiet zone
    const sizeRatio = Math.min(avgSideLen, expectedSide) / Math.max(avgSideLen, expectedSide);
    const combinedScore = result.score + sizeRatio * 0.001; // tiny tiebreaker
    allCandidates.push({ name, combinedScore, grid: cfg.grid });
    if (combinedScore > bestScore) {
      bestScore = combinedScore;
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
    // Ranked candidates: all configs above minScore, sorted by combined score
    candidates: allCandidates
      .filter(c => c.combinedScore >= minScore)
      .sort((a, b) => b.combinedScore - a.combinedScore)
      .slice(0, 5)
      .map(c => ({ name: c.name, score: c.combinedScore, grid: c.grid })),
  };
}

/**
 * Build data-index ↔ grid-position mapping that skips alignment pattern modules.
 *
 * dataToGrid[i] = { r, c } — the grid position of the i-th data module
 * gridToData[r*gs+c] = data index, or -1 if alignment pattern
 *
 * @param {number} gs - grid size
 * @param {Uint8Array} alignMask - gs*gs mask (1 = alignment, 0 = data)
 * @returns {{ dataToGrid: Array<{r:number,c:number}>, gridToData: Int32Array, dataCount: number }}
 */
function buildAlignmentMapping(gs, alignMask) {
  const gridToData = new Int32Array(gs * gs).fill(-1);
  const dataToGrid = [];
  let di = 0;
  for (let r = 0; r < gs; r++) {
    for (let c = 0; c < gs; c++) {
      const gi = r * gs + c;
      if (!alignMask[gi]) {
        gridToData[gi] = di;
        dataToGrid.push({ r, c });
        di++;
      }
    }
  }
  return { dataToGrid, gridToData, dataCount: di };
}

module.exports = {
  HD_CONFIGS,
  L2_CANVAS_PX, L2_GRID_MODULES,
  computeSymbolLayout,
  computeCanonicalFinderPoints,
  computeAlignmentPatternPositions,
  ALIGNMENT_PATTERN,
  buildAlignmentMapping,
  hdCalcCapacity,
  scoreConfigTiming,
  estimateFormat,
};
