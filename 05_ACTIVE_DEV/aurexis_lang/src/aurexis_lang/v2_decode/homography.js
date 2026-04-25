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
 * Normalize a set of 2D points: translate centroid to origin, scale avg dist to √2.
 * Returns { pts, T } where T is the 3×3 normalization matrix (row-major 9-element).
 * Hartley 1997 — critical for numerical conditioning of DLT.
 */
function normalizePoints(pts) {
  let cx = 0, cy = 0;
  for (const p of pts) { cx += p.x; cy += p.y; }
  cx /= pts.length; cy /= pts.length;
  let d = 0;
  for (const p of pts) d += Math.hypot(p.x - cx, p.y - cy);
  d /= pts.length;
  const s = (d > 1e-12) ? Math.SQRT2 / d : 1;
  const normalized = pts.map(p => ({ x: s * (p.x - cx), y: s * (p.y - cy) }));
  // T = [[s, 0, -s*cx], [0, s, -s*cy], [0, 0, 1]]
  return { pts: normalized, T: [s, 0, -s * cx, 0, s, -s * cy, 0, 0, 1] };
}

/**
 * Invert a 3×3 normalization matrix (which is always [s,0,-s*cx; 0,s,-s*cy; 0,0,1]).
 * T_inv = [[1/s, 0, cx], [0, 1/s, cy], [0, 0, 1]]
 */
function invertNormT(T) {
  const s = T[0];
  const cx = -T[2] / s, cy = -T[5] / s;
  return [1 / s, 0, cx, 0, 1 / s, cy, 0, 0, 1];
}

/**
 * Multiply two 3×3 matrices (row-major 9-element arrays).
 */
function mat3Mul(A, B) {
  const C = new Array(9);
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      C[r * 3 + c] = A[r * 3] * B[c] + A[r * 3 + 1] * B[3 + c] + A[r * 3 + 2] * B[6 + c];
    }
  }
  return C;
}

/**
 * Compute a 3x3 homography from 4 source points to 4 destination points.
 * Uses Hartley-normalized DLT for numerical stability.
 *
 * @param {Array<{x:number,y:number}>} src - 4 source points
 * @param {Array<{x:number,y:number}>} dst - 4 destination points
 * @returns {number[]|null} 9-element homography matrix [h0..h8] or null
 */
function computeHomography(src, dst) {
  // Normalize both point sets (Hartley 1997)
  const ns = normalizePoints(src);
  const nd = normalizePoints(dst);

  // Solve normalized DLT
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const { x: sx, y: sy } = ns.pts[i];
    const { x: dx, y: dy } = nd.pts[i];
    A.push([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy]);
    A.push([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy]);
    b.push(dx);
    b.push(dy);
  }
  const h = solveLinear(A, b);
  if (!h) return null;
  const Hn = [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7], 1];

  // Denormalize: H = Td_inv * Hn * Ts
  const TdInv = invertNormT(nd.T);
  const H = mat3Mul(TdInv, mat3Mul(Hn, ns.T));

  // Normalize so H[8] = 1
  if (Math.abs(H[8]) < 1e-12) return null;
  for (let i = 0; i < 9; i++) H[i] /= H[8];
  return H;
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

module.exports = { solveLinear, normalizePoints, mat3Mul, computeHomography, applyHomography };
