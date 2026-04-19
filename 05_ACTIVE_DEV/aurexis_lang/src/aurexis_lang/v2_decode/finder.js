/**
 * Aurexis Core V2 — Finder pattern detection
 *
 * QR-style 1:1:3:1:1 ratio scanning, cross-validation, clustering, triangle selection.
 * Extracted from aurexis_ed_unified.html (v12).
 * Pure JS, no DOM dependencies. Node-compatible.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

// --------------------------------------------------------------------------
// Image utilities
// --------------------------------------------------------------------------

function toGrayscale(imgData, W, H) {
  const gray = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) {
    const j = i * 4;
    gray[i] = Math.round(0.299 * imgData[j] + 0.587 * imgData[j + 1] + 0.114 * imgData[j + 2]);
  }
  return gray;
}

function otsuThreshold(gray, length) {
  const hist = new Int32Array(256);
  for (let i = 0; i < length; i++) hist[gray[i]]++;
  const total = length;
  let sumAll = 0;
  for (let i = 0; i < 256; i++) sumAll += i * hist[i];
  let sumBg = 0, wBg = 0, bestThresh = 128, bestVar = 0;
  for (let t = 0; t < 256; t++) {
    wBg += hist[t]; if (wBg === 0) continue;
    const wFg = total - wBg; if (wFg === 0) break;
    sumBg += t * hist[t];
    const diff = sumBg / wBg - (sumAll - sumBg) / wFg;
    const variance = wBg * wFg * diff * diff;
    if (variance > bestVar) { bestVar = variance; bestThresh = t; }
  }
  return bestThresh;
}

function downsampleGray(gray, W, H, factor) {
  const dW = Math.floor(W / factor), dH = Math.floor(H / factor);
  const out = new Uint8Array(dW * dH);
  const fSq = factor * factor;
  for (let dy = 0; dy < dH; dy++) {
    for (let dx = 0; dx < dW; dx++) {
      let sum = 0;
      const sy = dy * factor, sx = dx * factor;
      for (let fy = 0; fy < factor; fy++)
        for (let fx = 0; fx < factor; fx++)
          sum += gray[(sy + fy) * W + (sx + fx)];
      out[dy * dW + dx] = (sum / fSq + 0.5) | 0;
    }
  }
  return { gray: out, W: dW, H: dH };
}

// --------------------------------------------------------------------------
// Finder ratio checking
// --------------------------------------------------------------------------

function checkFinderRatio(runs) {
  const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
  if (total < 7) return false;
  const unit = total / 7;
  const tol = unit * 0.85;
  return Math.abs(runs[0] - unit) <= tol &&
         Math.abs(runs[1] - unit) <= tol &&
         Math.abs(runs[2] - 3 * unit) <= tol * 2.0 &&
         Math.abs(runs[3] - unit) <= tol &&
         Math.abs(runs[4] - unit) <= tol;
}

function crossCheckVertical(gray, W, H, cx, cy, estModSize, threshold) {
  const x = Math.round(cx);
  if (x < 0 || x >= W) return -1;

  let y0 = Math.round(cy), y1 = y0;
  const startBit = gray[y0 * W + x] < threshold ? 0 : 1;

  while (y0 > 0 && ((gray[(y0 - 1) * W + x] < threshold ? 0 : 1) === startBit)) y0--;
  while (y1 < H - 1 && ((gray[(y1 + 1) * W + x] < threshold ? 0 : 1) === startBit)) y1++;

  const scanStart = Math.max(0, y0 - Math.round(estModSize * 4));
  const scanEnd = Math.min(H - 1, y1 + Math.round(estModSize * 4));

  const runs = [0, 0, 0, 0, 0];
  let runIdx = -1;
  let lastBit = -1;

  for (let y = scanStart; y <= scanEnd; y++) {
    const bit = gray[y * W + x] < threshold ? 0 : 1;
    if (runIdx === -1) {
      if (bit === 0) { runIdx = 0; runs[0] = 1; lastBit = 0; }
      continue;
    }
    if (bit === lastBit) { runs[runIdx]++; }
    else {
      if (runIdx === 4) {
        if (checkFinderRatio(runs)) {
          const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
          return y - total / 2;
        }
        runs[0] = runs[2]; runs[1] = runs[3]; runs[2] = runs[4]; runs[3] = 0; runs[4] = 0; runIdx = 2;
      }
      if (runIdx < 4) { runIdx++; runs[runIdx] = 1; }
      lastBit = bit;
    }
  }
  if (runIdx === 4 && checkFinderRatio(runs)) {
    const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
    return scanEnd - total / 2;
  }
  return -1;
}

function scanFinderRow(gray, W, H, y, x0, x1, threshold, candidates) {
  const runs = [0, 0, 0, 0, 0];
  let runIdx = -1;
  let lastBit = -1;
  for (let x = x0; x <= x1; x++) {
    const bit = gray[y * W + x] < threshold ? 0 : 1;
    if (runIdx === -1) {
      if (bit === 0) { runIdx = 0; runs[0] = 1; lastBit = 0; }
      continue;
    }
    if (bit === lastBit) { runs[runIdx]++; continue; }
    if (runIdx === 4) {
      if (checkFinderRatio(runs)) {
        const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
        const ccx = x - total / 2;
        const estMod = total / 7;
        const vy = crossCheckVertical(gray, W, H, ccx, y, estMod, threshold);
        if (vy >= 0) {
          candidates.push({ x: ccx, y: (y + vy) / 2, estModSize: estMod });
        }
      }
      runs[0] = runs[2]; runs[1] = runs[3]; runs[2] = runs[4]; runs[3] = 0; runs[4] = 0; runIdx = 2;
    }
    if (runIdx < 4) { runIdx++; runs[runIdx] = 1; }
    lastBit = bit;
  }
  if (runIdx === 4 && checkFinderRatio(runs)) {
    const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
    const ccx = x1 - total / 2;
    const estMod = total / 7;
    const vy = crossCheckVertical(gray, W, H, ccx, y, estMod, threshold);
    if (vy >= 0) candidates.push({ x: ccx, y: (y + vy) / 2, estModSize: estMod });
  }
}

// --------------------------------------------------------------------------
// Full finder detection pipeline
// --------------------------------------------------------------------------

/**
 * Detect finder pattern candidates in RGBA image data.
 *
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA pixel data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {object} [bounds] - { x0, y0, x1, y1 } search region
 * @returns {Array<{x:number,y:number,estModSize:number}>} raw candidates
 */
function detectFinderPatterns(imgData, W, H, bounds) {
  let gray = toGrayscale(imgData, W, H);
  let scale = 1;
  const totalPx = W * H;
  if (totalPx > 2000000) { scale = 2; }

  let sW = W, sH = H;
  if (scale > 1) {
    const ds = downsampleGray(gray, W, H, scale);
    gray = ds.gray; sW = ds.W; sH = ds.H;
  }

  const x0 = bounds ? Math.floor(bounds.x0 / scale) : 0;
  const y0 = bounds ? Math.floor(bounds.y0 / scale) : 0;
  const x1 = bounds ? Math.min(Math.floor(bounds.x1 / scale), sW - 1) : sW - 1;
  const y1 = bounds ? Math.min(Math.floor(bounds.y1 / scale), sH - 1) : sH - 1;

  const otsuThresh = otsuThreshold(gray, gray.length);
  const candidates = [];

  const thresholds = [otsuThresh];
  if (Math.abs(otsuThresh - 128) > 25) thresholds.push(128);
  if (Math.abs(otsuThresh - 80) > 25 && Math.abs(128 - 80) > 25) thresholds.push(80);

  for (const threshold of thresholds) {
    for (let y = y0; y <= y1; y++) {
      scanFinderRow(gray, sW, sH, y, x0, x1, threshold, candidates);
    }
  }

  if (scale > 1) {
    for (const c of candidates) {
      c.x *= scale;
      c.y *= scale;
      c.estModSize *= scale;
    }
  }

  return candidates;
}

/**
 * Cluster finder candidates by spatial proximity.
 */
function clusterFinderCandidates(candidates) {
  if (candidates.length < 1) return [];
  candidates.sort((a, b) => a.x - b.x || a.y - b.y);
  const used = new Uint8Array(candidates.length);
  const clusters = [];

  for (let i = 0; i < candidates.length; i++) {
    if (used[i]) continue;
    const c = candidates[i];
    const radius = c.estModSize * 4;
    let sx = c.x, sy = c.y, sm = c.estModSize, cnt = 1;

    for (let j = i + 1; j < candidates.length; j++) {
      if (used[j]) continue;
      const d = candidates[j];
      if (d.x - c.x > radius * 3) break;
      if (Math.hypot(d.x - sx / cnt, d.y - sy / cnt) < radius) {
        sx += d.x; sy += d.y; sm += d.estModSize; cnt++; used[j] = 1;
      }
    }
    clusters.push({ x: sx / cnt, y: sy / cnt, estModSize: sm / cnt, votes: cnt });
  }
  return clusters;
}

/**
 * Find candidate TL/TR/BL triangles from clusters.
 * Returns up to maxResults triangles ranked by geometric score.
 */
function findFinderTriangles(clusters, maxResults) {
  if (clusters.length < 3) return [];
  const results = [];
  clusters.sort((a, b) => b.votes - a.votes);
  const n = Math.min(clusters.length, 20);

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      for (let k = j + 1; k < n; k++) {
        const pts = [clusters[i], clusters[j], clusters[k]];
        const mods = pts.map(p => p.estModSize);
        if (Math.max(...mods) > Math.min(...mods) * 3) continue;

        for (let v = 0; v < 3; v++) {
          const a = pts[v], b = pts[(v + 1) % 3], c = pts[(v + 2) % 3];
          const abx = b.x - a.x, aby = b.y - a.y, acx = c.x - a.x, acy = c.y - a.y;
          const lenAB = Math.hypot(abx, aby), lenAC = Math.hypot(acx, acy);
          if (lenAB < 20 || lenAC < 20) continue;
          const cosAngle = (abx * acx + aby * acy) / (lenAB * lenAC);
          const ratio = Math.max(lenAB, lenAC) / Math.min(lenAB, lenAC);
          if (Math.abs(cosAngle) < 0.35 && ratio < 2.2) {
            const score = (1 - Math.abs(cosAngle)) * (2.2 - ratio) * (a.votes + b.votes + c.votes);
            const cross = abx * acy - aby * acx;
            results.push({
              TL: a, TR: cross > 0 ? b : c, BL: cross > 0 ? c : b, score
            });
          }
        }
      }
    }
  }
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, maxResults || 10);
}

/**
 * Validate that 4 finder positions form a reasonable quadrilateral.
 */
function validateFinderQuad(fids) {
  const cx = (fids.TL.x + fids.TR.x + fids.BL.x + fids.BR.x) / 4;
  const cy = (fids.TL.y + fids.TR.y + fids.BL.y + fids.BR.y) / 4;
  if (fids.TL.x >= cx || fids.TL.y >= cy) return false;
  if (fids.TR.x <= cx || fids.TR.y >= cy) return false;
  if (fids.BL.x >= cx || fids.BL.y <= cy) return false;
  if (fids.BR.x <= cx || fids.BR.y <= cy) return false;
  const top = Math.hypot(fids.TR.x - fids.TL.x, fids.TR.y - fids.TL.y);
  const bot = Math.hypot(fids.BR.x - fids.BL.x, fids.BR.y - fids.BL.y);
  const left = Math.hypot(fids.BL.x - fids.TL.x, fids.BL.y - fids.TL.y);
  const right = Math.hypot(fids.BR.x - fids.TR.x, fids.BR.y - fids.TR.y);
  const sides = [top, bot, left, right];
  if (Math.max(...sides) / Math.min(...sides) > 2.5) return false;
  if ((top + bot + left + right) / 4 < 40) return false;
  const d1 = Math.hypot(fids.BR.x - fids.TL.x, fids.BR.y - fids.TL.y);
  const d2 = Math.hypot(fids.BL.x - fids.TR.x, fids.BL.y - fids.TR.y);
  if (d1 > 0 && d2 > 0 && Math.max(d1, d2) / Math.min(d1, d2) > 2.0) return false;
  return true;
}

/**
 * Full finder detection: detect patterns, cluster, find triangles, validate with timing.
 *
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA pixel data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {object} [bounds] - optional search bounds
 * @param {object} [opts] - options
 * @param {number} [opts.timingThreshold] - min timing accuracy (default 0.65)
 * @returns {object|null} { TL, TR, BL, BR } finder quad or null
 */
function detectFinders(imgData, W, H, bounds, opts = {}) {
  const timingThreshold = opts.timingThreshold || 0.65;
  const candidates = detectFinderPatterns(imgData, W, H, bounds);
  if (candidates.length < 3) return null;

  const clusters = clusterFinderCandidates(candidates);
  if (clusters.length < 3) return null;

  const triangles = findFinderTriangles(clusters, 15);
  if (triangles.length === 0) return null;

  const { computeHomography, applyHomography } = require("./homography");
  const { computeSymbolLayout } = require("./format");

  for (let ti = 0; ti < triangles.length; ti++) {
    const tri = triangles[ti];
    const br = {
      x: tri.TR.x + tri.BL.x - tri.TL.x,
      y: tri.TR.y + tri.BL.y - tri.TL.y,
    };
    const avgMod = (tri.TL.estModSize + tri.TR.estModSize + tri.BL.estModSize) / 3;

    const fids = {
      TL: { x: tri.TL.x, y: tri.TL.y, size: tri.TL.estModSize * 7 },
      TR: { x: tri.TR.x, y: tri.TR.y, size: tri.TR.estModSize * 7 },
      BL: { x: tri.BL.x, y: tri.BL.y, size: tri.BL.estModSize * 7 },
      BR: { x: br.x, y: br.y, size: avgMod * 5 },
    };

    if (!validateFinderQuad(fids)) continue;

    // Timing strip validation
    const topSpan = Math.hypot(fids.TR.x - fids.TL.x, fids.TR.y - fids.TL.y);
    const estTotalMod = Math.round(topSpan / avgMod) + 7;

    if (estTotalMod > 50 && imgData) {
      const testCanvasPx = estTotalMod * 8;
      const testLayout = computeSymbolLayout(estTotalMod - 16, testCanvasPx);
      const tqz = testLayout.qzPx, tmod = testLayout.modPx, ttot = testLayout.totalMod;
      const testCanon = [
        { x: tqz + 3.5 * tmod, y: tqz + 3.5 * tmod },
        { x: tqz + (ttot - 3.5) * tmod, y: tqz + 3.5 * tmod },
        { x: tqz + 3.5 * tmod, y: tqz + (ttot - 3.5) * tmod },
        { x: tqz + (ttot - 3.5) * tmod, y: tqz + (ttot - 3.5) * tmod },
      ];
      const testSrc = [fids.TL, fids.TR, fids.BL, fids.BR];
      const testH = computeHomography(testCanon, testSrc);
      if (testH) {
        let timOk = 0, timBad = 0;
        const sampleStep = Math.max(1, Math.floor((ttot - 15) / 20));
        for (let m = 8; m < ttot - 7; m += sampleStep) {
          const cx = tqz + m * tmod + tmod / 2;
          const cy = tqz + 6 * tmod + tmod / 2;
          const sp = applyHomography(testH, { x: cx, y: cy });
          const rx = Math.round(sp.x), ry = Math.round(sp.y);
          if (rx < 0 || ry < 0 || rx >= W || ry >= H) continue;
          const idx = (ry * W + rx) * 4;
          const lum = 0.299 * imgData[idx] + 0.587 * imgData[idx + 1] + 0.114 * imgData[idx + 2];
          const isDark = lum < 128;
          const shouldBeDark = (m % 2 === 0);
          if (isDark === shouldBeDark) timOk++; else timBad++;
        }
        const timTotal = timOk + timBad;
        const timPct = timTotal > 0 ? timOk / timTotal : 0;
        if (timPct < timingThreshold) continue;
      }
    }

    return fids;
  }

  return null;
}

module.exports = {
  toGrayscale,
  otsuThreshold,
  downsampleGray,
  checkFinderRatio,
  detectFinderPatterns,
  clusterFinderCandidates,
  findFinderTriangles,
  validateFinderQuad,
  detectFinders,
};
