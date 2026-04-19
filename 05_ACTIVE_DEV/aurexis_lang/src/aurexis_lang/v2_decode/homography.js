/**
 * Aurexis Core V2 — Homography (perspective transform)
 *
 * Extracted from aurexis_ed_unified.html (v12).
 * Pure JS, no DOM dependencies. Node-compatible.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

/**
 * Solve Ax = b via Gaussian elimination with partial pivoting.
 * @param {number[][]} A - NxN matrix
 * @param {number[]} b - N-vector
 * @returns {number[]|null} solution vector or null if singular
 */
function solveLinear(A, b) {
  const n = A.length;
  const M = A.map((row, i) => row.concat([b[i]]));

  for (let i = 0; i < n; i++) {
    let mr = i, ma = Math.abs(M[i][i]);
    for (let k = i + 1; k < n; k++) {
      const v = Math.abs(M[k][i]);
      if (v > ma) { ma = v; mr = k; }
    }
    if (mr !== i) { const t = M[i]; M[i] = M[mr]; M[mr] = t; }
    const p = M[i][i];
    if (Math.abs(p) < 1e-12) return null;
    for (let j = i; j <= n; j++) M[i][j] /= p;
    for (let k = 0; k < n; k++) {
      if (k === i) continue;
      const f = M[k][i];
      for (let j = i; j <= n; j++) M[k][j] -= f * M[i][j];
    }
  }
  return M.map(r => r[n]);
}

/**
 * Compute a 3x3 homography from 4 source points to 4 destination points.
 * @param {Array<{x:number,y:number}>} src - 4 source points
 * @param {Array<{x:number,y:number}>} dst - 4 destination points
 * @returns {number[]|null} 9-element homography matrix [h0..h8] or null
 */
function computeHomography(src, dst) {
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const { x: sx, y: sy } = src[i];
    const { x: dx, y: dy } = dst[i];
    A.push([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy]);
    A.push([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy]);
    b.push(dx);
    b.push(dy);
  }
  const h = solveLinear(A, b);
  if (!h) return null;
  return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];
}

/**
 * Apply a homography to a point.
 * @param {number[]} H - 9-element homography
 * @param {{x:number,y:number}} p - input point
 * @returns {{x:number,y:number}} transformed point
 */
function applyHomography(H, p) {
  const w = H[6] * p.x + H[7] * p.y + H[8];
  return {
    x: (H[0] * p.x + H[1] * p.y + H[2]) / w,
    y: (H[3] * p.x + H[4] * p.y + H[5]) / w,
  };
}

module.exports = { solveLinear, computeHomography, applyHomography };
