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

// --------------------------------------------------------------------------
// Sauvola adaptive thresholding (Shafait integral-image optimization)
// T(x,y) = mean(x,y) * (1 + k * (stdev(x,y)/R - 1))
// O(1) per pixel regardless of window size.
// --------------------------------------------------------------------------

/**
 * Compute Sauvola adaptive binary image using integral images.
 *
 * @param {Uint8Array} gray - grayscale image
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {number} [winSize] - local window size (default: 15% of min dimension, odd)
 * @param {number} [k] - sensitivity parameter (default: 0.2)
 * @param {number} [R] - dynamic range of std dev (default: 128)
 * @returns {Uint8Array} binary image (0 = dark, 255 = light)
 */
function sauvolaBinarize(gray, W, H, winSize, k, R) {
  k = k || 0.2;
  R = R || 128;
  if (!winSize) winSize = Math.max(7, (Math.min(W, H) * 0.15) | 1);
  if (winSize % 2 === 0) winSize++;
  const half = (winSize - 1) >> 1;

  // Integral images: sum and sum-of-squares
  const intI = new Float64Array((W + 1) * (H + 1));
  const intI2 = new Float64Array((W + 1) * (H + 1));
  const stride = W + 1;

  for (let y = 0; y < H; y++) {
    let rowSum = 0, rowSum2 = 0;
    for (let x = 0; x < W; x++) {
      const v = gray[y * W + x];
      rowSum += v;
      rowSum2 += v * v;
      intI[(y + 1) * stride + (x + 1)] = rowSum + intI[y * stride + (x + 1)];
      intI2[(y + 1) * stride + (x + 1)] = rowSum2 + intI2[y * stride + (x + 1)];
    }
  }

  // Compute per-pixel threshold and binarize
  const binary = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const y0 = Math.max(0, y - half), y1 = Math.min(H - 1, y + half);
      const x0 = Math.max(0, x - half), x1 = Math.min(W - 1, x + half);
      const area = (y1 - y0 + 1) * (x1 - x0 + 1);
      const sum = intI[(y1 + 1) * stride + (x1 + 1)]
                - intI[y0 * stride + (x1 + 1)]
                - intI[(y1 + 1) * stride + x0]
                + intI[y0 * stride + x0];
      const sum2 = intI2[(y1 + 1) * stride + (x1 + 1)]
                 - intI2[y0 * stride + (x1 + 1)]
                 - intI2[(y1 + 1) * stride + x0]
                 + intI2[y0 * stride + x0];
      const mean = sum / area;
      const variance = Math.max(0, sum2 / area - mean * mean);
      const stdev = Math.sqrt(variance);
      const threshold = mean * (1 + k * (stdev / R - 1));
      binary[y * W + x] = gray[y * W + x] < threshold ? 0 : 255;
    }
  }
  return binary;
}

/**
 * Compute per-pixel Sauvola threshold (returns threshold image, not binary).
 * Useful for finder detection where scanlines need the threshold value.
 */
function sauvolaThresholdMap(gray, W, H, winSize, k, R) {
  k = k || 0.2;
  R = R || 128;
  if (!winSize) winSize = Math.max(7, (Math.min(W, H) * 0.15) | 1);
  if (winSize % 2 === 0) winSize++;
  const half = (winSize - 1) >> 1;

  const intI = new Float64Array((W + 1) * (H + 1));
  const intI2 = new Float64Array((W + 1) * (H + 1));
  const stride = W + 1;

  for (let y = 0; y < H; y++) {
    let rowSum = 0, rowSum2 = 0;
    for (let x = 0; x < W; x++) {
      const v = gray[y * W + x];
      rowSum += v;
      rowSum2 += v * v;
      intI[(y + 1) * stride + (x + 1)] = rowSum + intI[y * stride + (x + 1)];
      intI2[(y + 1) * stride + (x + 1)] = rowSum2 + intI2[y * stride + (x + 1)];
    }
  }

  const threshMap = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const y0 = Math.max(0, y - half), y1 = Math.min(H - 1, y + half);
      const x0 = Math.max(0, x - half), x1 = Math.min(W - 1, x + half);
      const area = (y1 - y0 + 1) * (x1 - x0 + 1);
      const sum = intI[(y1 + 1) * stride + (x1 + 1)]
                - intI[y0 * stride + (x1 + 1)]
                - intI[(y1 + 1) * stride + x0]
                + intI[y0 * stride + x0];
      const sum2 = intI2[(y1 + 1) * stride + (x1 + 1)]
                 - intI2[y0 * stride + (x1 + 1)]
                 - intI2[(y1 + 1) * stride + x0]
                 + intI2[y0 * stride + x0];
      const mean = sum / area;
      const variance = Math.max(0, sum2 / area - mean * mean);
      const stdev = Math.sqrt(variance);
      threshMap[y * W + x] = Math.round(Math.min(255, Math.max(0, mean * (1 + k * (stdev / R - 1)))));
    }
  }
  return threshMap;
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

function checkFinderRatio(runs, toleranceMul) {
  toleranceMul = toleranceMul || 1.0;
  const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
  if (total < 7) return false;
  const unit = total / 7;
  const tol = unit * 0.85 * toleranceMul;
  return Math.abs(runs[0] - unit) <= tol &&
         Math.abs(runs[1] - unit) <= tol &&
         Math.abs(runs[2] - 3 * unit) <= tol * 2.0 &&
         Math.abs(runs[3] - unit) <= tol &&
         Math.abs(runs[4] - unit) <= tol;
}

/**
 * Relaxed ratio check for aggressive perspective.
 * Allows wider tolerance (1.5x) for foreshortened finder patterns.
 */
function checkFinderRatioRelaxed(runs) {
  return checkFinderRatio(runs, 1.5);
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

/**
 * Relaxed scanFinderRow: uses checkFinderRatioRelaxed for wider tolerance.
 * Used in the second-chance pass for aggressive perspective.
 */
function scanFinderRowRelaxed(gray, W, H, y, x0, x1, threshold, candidates) {
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
      if (checkFinderRatioRelaxed(runs)) {
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
  if (runIdx === 4 && checkFinderRatioRelaxed(runs)) {
    const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
    const ccx = x1 - total / 2;
    const estMod = total / 7;
    const vy = crossCheckVertical(gray, W, H, ccx, y, estMod, threshold);
    if (vy >= 0) candidates.push({ x: ccx, y: (y + vy) / 2, estModSize: estMod });
  }
}

/**
 * Scan a row for finder patterns using a per-pixel adaptive threshold map.
 * Same logic as scanFinderRow but reads threshold per-pixel from threshMap.
 */
function scanFinderRowAdaptive(gray, W, H, y, x0, x1, threshMap, candidates) {
  const runs = [0, 0, 0, 0, 0];
  let runIdx = -1;
  let lastBit = -1;
  for (let x = x0; x <= x1; x++) {
    const bit = gray[y * W + x] < threshMap[y * W + x] ? 0 : 1;
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
        // Use midpoint of threshMap at candidate center for vertical cross-check
        const midThresh = threshMap[y * W + Math.round(ccx)] || 128;
        const vy = crossCheckVertical(gray, W, H, ccx, y, estMod, midThresh);
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
    const midThresh = threshMap[y * W + Math.round(ccx)] || 128;
    const vy = crossCheckVertical(gray, W, H, ccx, y, estMod, midThresh);
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

  // Sauvola adaptive threshold pass — catches finders missed by global thresholds
  // under uneven lighting (gradient, vignette, shadow).
  // We compute the per-pixel threshold map once, then scan rows using it.
  const sauvolaMap = sauvolaThresholdMap(gray, sW, sH);
  for (let y = y0; y <= y1; y++) {
    scanFinderRowAdaptive(gray, sW, sH, y, x0, x1, sauvolaMap, candidates);
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
 * Relaxed finder pattern detection with wider ratio tolerance.
 * Used as a second-chance pass when standard detection fails,
 * e.g. under aggressive perspective that foreshortens finder bars.
 */
function detectFinderPatternsRelaxed(imgData, W, H, bounds) {
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

  // More threshold candidates for relaxed pass
  const thresholds = [otsuThresh];
  if (Math.abs(otsuThresh - 128) > 15) thresholds.push(128);
  if (Math.abs(otsuThresh - 80) > 15) thresholds.push(80);
  if (Math.abs(otsuThresh - 170) > 15) thresholds.push(170);

  for (const threshold of thresholds) {
    for (let y = y0; y <= y1; y++) {
      scanFinderRowRelaxed(gray, sW, sH, y, x0, x1, threshold, candidates);
    }
  }

  // Also run Sauvola with relaxed ratio
  const sauvolaMap = sauvolaThresholdMap(gray, sW, sH);
  for (let y = y0; y <= y1; y++) {
    // Use the adaptive threshold map with the relaxed ratio scanner
    const runs = [0, 0, 0, 0, 0];
    let runIdx = -1, lastBit = -1;
    for (let x = x0; x <= x1; x++) {
      const bit = gray[y * sW + x] < sauvolaMap[y * sW + x] ? 0 : 1;
      if (runIdx === -1) {
        if (bit === 0) { runIdx = 0; runs[0] = 1; lastBit = 0; }
        continue;
      }
      if (bit === lastBit) { runs[runIdx]++; continue; }
      if (runIdx === 4) {
        if (checkFinderRatioRelaxed(runs)) {
          const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
          const ccx = x - total / 2;
          const estMod = total / 7;
          const midThresh = sauvolaMap[y * sW + Math.round(ccx)] || 128;
          const vy = crossCheckVertical(gray, sW, sH, ccx, y, estMod, midThresh);
          if (vy >= 0) candidates.push({ x: ccx, y: (y + vy) / 2, estModSize: estMod });
        }
        runs[0] = runs[2]; runs[1] = runs[3]; runs[2] = runs[4]; runs[3] = 0; runs[4] = 0; runIdx = 2;
      }
      if (runIdx < 4) { runIdx++; runs[runIdx] = 1; }
      lastBit = bit;
    }
    if (runIdx === 4 && checkFinderRatioRelaxed(runs)) {
      const total = runs[0] + runs[1] + runs[2] + runs[3] + runs[4];
      const ccx = x1 - total / 2;
      const estMod = total / 7;
      const midThresh = sauvolaMap[y * sW + Math.round(ccx)] || 128;
      const vy = crossCheckVertical(gray, sW, sH, ccx, y, estMod, midThresh);
      if (vy >= 0) candidates.push({ x: ccx, y: (y + vy) / 2, estModSize: estMod });
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
  // If corner distances were computed by the caller (_detectFindersPass),
  // sort by corner proximity so real finders (at image corners) are tried
  // first. Otherwise fall back to votes-based sort.
  if (clusters[0] && clusters[0]._cornerDist !== undefined) {
    clusters.sort((a, b) => a._cornerDist - b._cornerDist);
  } else {
    clusters.sort((a, b) => b.votes - a.votes);
  }
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

// --------------------------------------------------------------------------
// Subpixel finder center refinement (gradient-based, cornerSubPix style)
// --------------------------------------------------------------------------

/**
 * Refine a finder center to subpixel accuracy using gradient convergence.
 * For each pixel in a window, the gradient vector should be perpendicular to
 * the vector from the true center to that pixel. We minimize:
 *   sum_i (g_i · (p - q_i))^2
 * which gives: A*p = b where A = sum(g*g'), b = sum(g*g'*q)
 *
 * @param {Uint8Array} gray - grayscale image
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {number} cx - initial center x
 * @param {number} cy - initial center y
 * @param {number} winRadius - half-window size in pixels
 * @returns {{x:number, y:number}} refined center
 */
function subpixelRefineGradient(gray, W, H, cx, cy, winRadius) {
  const ix = Math.round(cx), iy = Math.round(cy);
  let a00 = 0, a01 = 0, a11 = 0, b0 = 0, b1 = 0;

  for (let dy = -winRadius; dy <= winRadius; dy++) {
    for (let dx = -winRadius; dx <= winRadius; dx++) {
      const x = ix + dx, y = iy + dy;
      if (x < 1 || y < 1 || x >= W - 1 || y >= H - 1) continue;
      // Sobel-like gradient
      const gx = (gray[y * W + x + 1] - gray[y * W + x - 1]) * 0.5;
      const gy = (gray[(y + 1) * W + x] - gray[(y - 1) * W + x]) * 0.5;
      a00 += gx * gx;
      a01 += gx * gy;
      a11 += gy * gy;
      b0 += gx * gx * x + gx * gy * y;
      b1 += gx * gy * x + gy * gy * y;
    }
  }

  const det = a00 * a11 - a01 * a01;
  if (Math.abs(det) < 1e-6) return { x: cx, y: cy };

  const rx = (a11 * b0 - a01 * b1) / det;
  const ry = (a00 * b1 - a01 * b0) / det;

  // Reject if refinement moves too far (likely a false convergence)
  if (Math.abs(rx - cx) > winRadius || Math.abs(ry - cy) > winRadius) {
    return { x: cx, y: cy };
  }
  return { x: rx, y: ry };
}

// --------------------------------------------------------------------------
// BR orientation pattern detection
// --------------------------------------------------------------------------

/**
 * The 5x5 orientation bitmap expected at the bottom-right corner.
 * 1 = dark, 0 = light.
 */
const ORIENT_BITMAP = [
  [1,1,1,1,1],
  [1,0,0,0,1],
  [1,0,1,0,1],
  [1,0,0,0,1],
  [1,1,1,1,1],
];

/**
 * Score a candidate BR center by matching the 5x5 orientation pattern.
 * Uses the grayscale image and estimated module size to check each cell.
 *
 * @param {Uint8Array} gray - grayscale image
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {number} cx - candidate center x
 * @param {number} cy - candidate center y
 * @param {number} modPx - estimated module size in pixels
 * @param {number} threshold - binarization threshold
 * @returns {number} score 0..1 (fraction of cells matching expected pattern)
 */
function scoreOrientAt(gray, W, H, cx, cy, modPx, threshold) {
  let match = 0, total = 0;
  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 5; c++) {
      // Sample center of this cell relative to the orient pattern center (cell 2,2)
      const px = Math.round(cx + (c - 2) * modPx);
      const py = Math.round(cy + (r - 2) * modPx);
      if (px < 0 || py < 0 || px >= W || py >= H) continue;
      const lum = gray[py * W + px];
      const isDark = lum < threshold;
      const shouldBeDark = ORIENT_BITMAP[r][c] === 1;
      if (isDark === shouldBeDark) match++;
      total++;
    }
  }
  return total > 0 ? match / total : 0;
}

/**
 * Search for the 5x5 orientation pattern near an estimated BR position.
 * Returns the refined BR center or the original estimate if not found.
 *
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA image data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {object} estBR - { x, y } estimated BR center (parallelogram)
 * @param {number} estModPx - estimated module size in image pixels
 * @param {object} [opts]
 * @param {number} [opts.searchRadius] - search radius in pixels (default: estModPx * 8)
 * @param {number} [opts.step] - search step in pixels (default: max(1, estModPx/4))
 * @param {number} [opts.minScore] - minimum match score to accept (default: 0.72)
 * @returns {{ x: number, y: number, score: number, refined: boolean }}
 */
function detectOrientPattern(imgData, W, H, estBR, estModPx, opts = {}) {
  const searchRadius = opts.searchRadius || Math.round(estModPx * 8);
  const step = opts.step || Math.max(1, Math.round(estModPx / 4));
  const minScore = opts.minScore || 0.72;

  // Build grayscale for the search region
  const gray = toGrayscale(imgData, W, H);
  const threshold = otsuThreshold(gray, gray.length);

  let bestScore = 0, bestX = estBR.x, bestY = estBR.y;

  const x0 = Math.max(0, Math.round(estBR.x - searchRadius));
  const x1 = Math.min(W - 1, Math.round(estBR.x + searchRadius));
  const y0 = Math.max(0, Math.round(estBR.y - searchRadius));
  const y1 = Math.min(H - 1, Math.round(estBR.y + searchRadius));

  for (let py = y0; py <= y1; py += step) {
    for (let px = x0; px <= x1; px += step) {
      const s = scoreOrientAt(gray, W, H, px, py, estModPx, threshold);
      if (s > bestScore) {
        bestScore = s;
        bestX = px;
        bestY = py;
      }
    }
  }

  // Sub-pixel refinement: search ±step around best with step=1
  if (bestScore >= minScore && step > 1) {
    const rx0 = Math.max(0, Math.round(bestX - step));
    const rx1 = Math.min(W - 1, Math.round(bestX + step));
    const ry0 = Math.max(0, Math.round(bestY - step));
    const ry1 = Math.min(H - 1, Math.round(bestY + step));
    for (let py = ry0; py <= ry1; py++) {
      for (let px = rx0; px <= rx1; px++) {
        const s = scoreOrientAt(gray, W, H, px, py, estModPx, threshold);
        if (s > bestScore) {
          bestScore = s;
          bestX = px;
          bestY = py;
        }
      }
    }
  }

  return {
    x: bestX, y: bestY,
    score: bestScore,
    refined: bestScore >= minScore,
  };
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

  // Pass 1: standard detection
  let result = _detectFindersPass(imgData, W, H, bounds, timingThreshold, false);
  if (result) return result;

  // Pass 2: relaxed ratio tolerance + lower timing threshold
  // Catches aggressively foreshortened finders from steep perspective
  result = _detectFindersPass(imgData, W, H, bounds, 0.50, true);
  return result;
}

/**
 * Internal finder detection pass.
 * @param {boolean} relaxed - if true, use relaxed ratio tolerance and more triangle candidates
 */
function _detectFindersPass(imgData, W, H, bounds, timingThreshold, relaxed) {
  const candidates = relaxed
    ? detectFinderPatternsRelaxed(imgData, W, H, bounds)
    : detectFinderPatterns(imgData, W, H, bounds);
  if (candidates.length < 3) return null;

  const clusters = clusterFinderCandidates(candidates);
  if (clusters.length < 3) return null;

  // ── Corner-priority sort ──────────────────────────────────────
  // Sort clusters so that candidates near image corners are tried
  // first in triangle formation.  This ensures real finders (which
  // sit at image corners) take priority over false positives in
  // uniform data regions.
  const corners = [
    { x: 0, y: 0 }, { x: W, y: 0 },
    { x: 0, y: H }, { x: W, y: H },
  ];
  for (const c of clusters) {
    c._cornerDist = Math.min(
      ...corners.map(cr => Math.hypot(c.x - cr.x, c.y - cr.y))
    );
  }
  clusters.sort((a, b) => a._cornerDist - b._cornerDist);

  const maxTriangles = relaxed ? 30 : 15;
  const triangles = findFinderTriangles(clusters, maxTriangles);

  // ── Corner-trio fast path ─────────────────────────────────────
  // The 3 clusters closest to image corners are the best candidates
  // for real finders.  If they form a valid right-angle triangle,
  // prepend it to the triangle list so it's tried first — even if
  // high-vote false-positive triangles outscore it.
  if (clusters.length >= 3) {
    const a = clusters[0], b = clusters[1], c = clusters[2];
    const mods = [a.estModSize, b.estModSize, c.estModSize];
    if (Math.max(...mods) <= Math.min(...mods) * 3) {
      // Try all 3 vertex assignments for the right-angle corner
      for (let v = 0; v < 3; v++) {
        const p = [a, b, c];
        const pa = p[v], pb = p[(v + 1) % 3], pc = p[(v + 2) % 3];
        const abx = pb.x - pa.x, aby = pb.y - pa.y;
        const acx = pc.x - pa.x, acy = pc.y - pa.y;
        const lenAB = Math.hypot(abx, aby), lenAC = Math.hypot(acx, acy);
        if (lenAB < 20 || lenAC < 20) continue;
        const cosAngle = (abx * acx + aby * acy) / (lenAB * lenAC);
        const ratio = Math.max(lenAB, lenAC) / Math.min(lenAB, lenAC);
        if (Math.abs(cosAngle) < 0.35 && ratio < 2.2) {
          const cross = abx * acy - aby * acx;
          const tri = {
            TL: pa, TR: cross > 0 ? pb : pc, BL: cross > 0 ? pc : pb,
            score: Infinity, // ensure it sorts first
          };
          triangles.unshift(tri);
          break; // only need one valid assignment
        }
      }
    }
  }

  if (triangles.length === 0) return null;

  const { computeHomography, applyHomography } = require("./homography");
  const { computeSymbolLayout, HD_CONFIGS } = require("./format");

  // Candidate totalMod values: all known HD configs + estimate from module size
  const candidateTotalMods = new Set();
  for (const [, cfg] of Object.entries(HD_CONFIGS)) {
    candidateTotalMods.add(cfg.grid + 16);
  }

  // Build full-resolution grayscale for subpixel refinement (once)
  const fullGray = toGrayscale(imgData, W, H);

  for (let ti = 0; ti < triangles.length; ti++) {
    const tri = triangles[ti];
    const avgMod = (tri.TL.estModSize + tri.TR.estModSize + tri.BL.estModSize) / 3;

    // Subpixel refinement of TL, TR, BL finder centers
    const winR = Math.max(3, Math.round(avgMod * 2));
    const tlRef = subpixelRefineGradient(fullGray, W, H, tri.TL.x, tri.TL.y, winR);
    const trRef = subpixelRefineGradient(fullGray, W, H, tri.TR.x, tri.TR.y, winR);
    const blRef = subpixelRefineGradient(fullGray, W, H, tri.BL.x, tri.BL.y, winR);
    tri.TL.x = tlRef.x; tri.TL.y = tlRef.y;
    tri.TR.x = trRef.x; tri.TR.y = trRef.y;
    tri.BL.x = blRef.x; tri.BL.y = blRef.y;

    const brEst = {
      x: tri.TR.x + tri.BL.x - tri.TL.x,
      y: tri.TR.y + tri.BL.y - tri.TL.y,
    };

    // Attempt explicit BR detection via 5x5 orientation pattern search
    const brResult = detectOrientPattern(imgData, W, H, brEst, avgMod);
    const br = brResult.refined ? { x: brResult.x, y: brResult.y } : brEst;

    const fids = {
      TL: { x: tri.TL.x, y: tri.TL.y, size: tri.TL.estModSize * 7 },
      TR: { x: tri.TR.x, y: tri.TR.y, size: tri.TR.estModSize * 7 },
      BL: { x: tri.BL.x, y: tri.BL.y, size: tri.BL.estModSize * 7 },
      BR: { x: br.x, y: br.y, size: avgMod * 5, orientScore: brResult.score, orientRefined: brResult.refined },
    };

    if (!validateFinderQuad(fids)) continue;

    // ── Minimum span check (per-axis) ─────────────────────────────
    // Reject finder quads whose bounding box doesn't span a significant
    // fraction of the image on BOTH axes.  Real finders sit near the
    // image corners (~95% span); false positives from uniform data
    // regions cluster in a sub-area (~60-70% on one or both axes).
    const allX = [fids.TL.x, fids.TR.x, fids.BL.x, fids.BR.x];
    const allY = [fids.TL.y, fids.TR.y, fids.BL.y, fids.BR.y];
    const spanX = Math.max(...allX) - Math.min(...allX);
    const spanY = Math.max(...allY) - Math.min(...allY);
    // Both axes must span ≥ 60% of the image dimension.
    // Real finders span ~85-95% of artifact; with background padding
    // they can drop to ~65-70%. False positives from data regions
    // typically cluster within 50-55%.
    if (W > 0 && spanX / W < 0.60) continue;
    if (H > 0 && spanY / H < 0.60) continue;

    // Also add the noisy estimate
    const topSpan = Math.hypot(fids.TR.x - fids.TL.x, fids.TR.y - fids.TL.y);
    candidateTotalMods.add(Math.round(topSpan / avgMod) + 7);

    // Try-all-configs timing validation: test each candidate totalMod,
    // accept the triangle if ANY config's timing strip scores above threshold.
    // This avoids promoting a noisy estModSize into a hard format decision.
    let bestTimPct = 0;

    for (const ttot of candidateTotalMods) {
      if (ttot < 30) continue;
      const testCanvasPx = ttot * 8;
      const testLayout = computeSymbolLayout(ttot - 16, testCanvasPx);
      const tqz = testLayout.qzPx, tmod = testLayout.modPx;
      const testCanon = [
        { x: tqz + 3.5 * tmod, y: tqz + 3.5 * tmod },
        { x: tqz + (ttot - 3.5) * tmod, y: tqz + 3.5 * tmod },
        { x: tqz + 3.5 * tmod, y: tqz + (ttot - 3.5) * tmod },
        { x: tqz + (ttot - 3.5) * tmod, y: tqz + (ttot - 3.5) * tmod },
      ];
      const testSrc = [fids.TL, fids.TR, fids.BL, fids.BR];
      const testH = computeHomography(testCanon, testSrc);
      if (!testH) continue;

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
      if (timPct > bestTimPct) bestTimPct = timPct;
      if (bestTimPct >= timingThreshold) break; // early exit
    }

    if (bestTimPct < timingThreshold) continue;
    return fids;
  }

  return null;
}

module.exports = {
  toGrayscale,
  otsuThreshold,
  sauvolaBinarize,
  sauvolaThresholdMap,
  downsampleGray,
  checkFinderRatio,
  checkFinderRatioRelaxed,
  detectFinderPatterns,
  detectFinderPatternsRelaxed,
  clusterFinderCandidates,
  findFinderTriangles,
  validateFinderQuad,
  subpixelRefineGradient,
  scoreOrientAt,
  detectOrientPattern,
  detectFinders,
};
