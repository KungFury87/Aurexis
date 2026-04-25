/**
 * Aurexis Core V2 — GF(2^8) Galois Field + Reed-Solomon Codec
 *
 * Extracted from aurexis_ed_unified.html (v12).
 * Pure JS, no DOM dependencies. Node-compatible.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

// --------------------------------------------------------------------------
// GF(2^8) field arithmetic — primitive polynomial 0x11d
// --------------------------------------------------------------------------
const PP = 0x11d;
const gfExp = new Uint8Array(512);
const gfLog = new Uint8Array(256);

(function initGF() {
  let x = 1;
  for (let i = 0; i < 255; i++) {
    gfExp[i] = x;
    gfExp[i + 255] = x;
    gfLog[x] = i;
    x <<= 1;
    if (x & 0x100) x ^= PP;
  }
  gfLog[0] = 255;
})();

function gfMul(a, b) {
  return (a === 0 || b === 0) ? 0 : gfExp[gfLog[a] + gfLog[b]];
}

function gfDiv(a, b) {
  return a === 0 ? 0 : gfExp[gfLog[a] + 255 - gfLog[b]];
}

function gfPow(a, n) {
  return a === 0 ? 0 : gfExp[(gfLog[a] * n) % 255];
}

function gfInv(a) {
  return a === 0 ? 0 : gfExp[255 - gfLog[a]];
}

function polyMul(p, q) {
  const r = new Uint8Array(p.length + q.length - 1);
  for (let i = 0; i < p.length; i++)
    for (let j = 0; j < q.length; j++)
      r[i + j] ^= gfMul(p[i], q[j]);
  return r;
}

function polyEval(p, x) {
  let r = 0;
  for (let i = 0; i < p.length; i++)
    r = gfMul(r, x) ^ p[i];
  return r;
}

function generatorPoly(nsym) {
  let g = new Uint8Array([1]);
  for (let i = 0; i < nsym; i++)
    g = polyMul(g, new Uint8Array([1, gfPow(2, i)]));
  return g;
}

// --------------------------------------------------------------------------
// RS encode
// --------------------------------------------------------------------------
function rsEncode(data, nsym) {
  const gen = generatorPoly(nsym);
  const out = new Uint8Array(data.length + nsym);
  out.set(data);
  for (let i = 0; i < data.length; i++) {
    const c = out[i];
    if (c !== 0) {
      for (let j = 1; j < gen.length; j++)
        out[i + j] ^= gfMul(gen[j], c);
    }
  }
  out.set(data);
  return out;
}

// --------------------------------------------------------------------------
// RS decode — exact port from aurexis_ed_unified.html
// Uses plain JS arrays for Berlekamp-Massey (push/slice needed)
// --------------------------------------------------------------------------
function rsDecode(received, nsym) {
  const n = received.length;
  const r = new Uint8Array(received);

  // Syndromes
  const S = new Array(nsym);
  let hasErr = false;
  for (let i = 0; i < nsym; i++) {
    S[i] = polyEval(r, gfPow(2, i));
    if (S[i] !== 0) hasErr = true;
  }
  if (!hasErr) {
    return { ok: true, data: r.slice(0, n - nsym), corrected: 0 };
  }

  // Berlekamp-Massey — uses plain arrays exactly as original
  let C = [1], B = [1], L = 0, m = 1, b = 1;
  for (let nn = 0; nn < nsym; nn++) {
    let d = S[nn];
    for (let i = 1; i <= L; i++) {
      if (i < C.length && nn - i >= 0) d ^= gfMul(C[i], S[nn - i]);
    }
    if (d === 0) {
      m++;
    } else if (2 * L <= nn) {
      const T = C.slice();
      const coef = gfDiv(d, b);
      const shB = new Array(m).fill(0).concat(B);
      while (C.length < shB.length) C.push(0);
      for (let i = 0; i < shB.length; i++) C[i] ^= gfMul(coef, shB[i]);
      L = nn + 1 - L;
      B = T;
      b = d;
      m = 1;
    } else {
      const coef = gfDiv(d, b);
      const shB = new Array(m).fill(0).concat(B);
      while (C.length < shB.length) C.push(0);
      for (let i = 0; i < shB.length; i++) C[i] ^= gfMul(coef, shB[i]);
      m++;
    }
  }

  // Trim trailing zeros
  while (C.length > 1 && C[C.length - 1] === 0) C.pop();
  const numErrors = L;
  if (numErrors * 2 > nsym) {
    return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
  }

  // Error locator polynomial — reverse for Chien search
  const errLocH = C.slice().reverse();

  // Chien search for error positions
  const errPos = [];
  for (let j = 0; j < n; j++) {
    if (polyEval(new Uint8Array(errLocH), gfPow(2, 255 - j)) === 0) {
      errPos.push(n - 1 - j);
    }
  }
  if (errPos.length !== numErrors) {
    return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
  }

  // Error evaluator: omega = (S * C) mod x^nsym, reversed
  const omFull = new Array(S.length + C.length - 1).fill(0);
  for (let i = 0; i < S.length; i++)
    for (let j = 0; j < C.length; j++)
      omFull[i + j] ^= gfMul(S[i], C[j]);
  const omH = omFull.slice(0, nsym).reverse();

  // Formal derivative of C (odd-indexed coefficients)
  const dLow = [];
  for (let k = 1; k < C.length; k += 2) {
    while (dLow.length < k) dLow.push(0);
    dLow[k - 1] = C[k];
  }
  if (dLow.length === 0) dLow.push(0);
  const dH = dLow.slice().reverse();

  // Forney algorithm
  for (const pos of errPos) {
    const Xi = gfPow(2, n - 1 - pos);
    const XiInv = gfInv(Xi);
    const omVal = polyEval(new Uint8Array(omH), XiInv);
    const dVal = polyEval(new Uint8Array(dH), XiInv);
    if (dVal === 0) return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
    r[pos] ^= gfMul(Xi, gfDiv(omVal, dVal));
  }

  // Verify syndromes are zero
  for (let i = 0; i < nsym; i++) {
    if (polyEval(r, gfPow(2, i)) !== 0) {
      return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
    }
  }

  return { ok: true, data: r.slice(0, n - nsym), corrected: errPos.length };
}

// --------------------------------------------------------------------------
// RS decode with erasures — errors + known-bad positions
// Erasures cost 1 parity symbol each (vs 2 for errors).
// Capacity: 2*errors + erasures ≤ nsym
// --------------------------------------------------------------------------

/**
 * RS decode with erasure support.
 *
 * Erasure positions are byte indices in the block known to be unreliable.
 * The decoder treats them as "known wrong" — each erasure costs 1 parity symbol
 * instead of 2 for a blind error. With nsym=32: up to 32 pure erasures,
 * or 16 pure errors, or any mix where 2*errors + erasures ≤ 32.
 *
 * Algorithm:
 *   1. Compute syndromes
 *   2. Build erasure locator from known positions
 *   3. Compute Forney syndromes (recursive multiply S(x)·Λ_e(x))
 *   4. Run BM on Forney syndromes → error-only locator
 *   5. Full locator = erasure × error locators
 *   6. Chien search + Forney algorithm for magnitudes
 *
 * @param {Uint8Array} received - block to decode
 * @param {number} nsym - parity symbols
 * @param {number[]} erasurePositions - byte indices declared as erasures
 * @returns {{ ok, data, corrected }}
 */
function rsDecodeWithErasures(received, nsym, erasurePositions) {
  const n = received.length;
  const r = new Uint8Array(received);
  erasurePositions = erasurePositions || [];
  const v = erasurePositions.length;

  if (v > nsym) {
    return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
  }

  // Step 1: Syndromes
  const S = new Array(nsym);
  let hasErr = false;
  for (let i = 0; i < nsym; i++) {
    S[i] = polyEval(r, gfPow(2, i));
    if (S[i] !== 0) hasErr = true;
  }
  if (!hasErr) {
    return { ok: true, data: r.slice(0, n - nsym), corrected: 0 };
  }

  // If only erasures and no additional capacity, skip BM
  if (v === 0) {
    // No erasures — fall back to standard decode
    return rsDecode(received, nsym);
  }

  // Step 2: Build erasure locator polynomial Λ_e(x) = ∏(1 + X_j·x)
  // where X_j = α^(n-1-pos_j), in big-endian representation
  let sigmaE = new Uint8Array([1]);
  const erasureXi = [];
  for (const pos of erasurePositions) {
    const Xi = gfPow(2, n - 1 - pos);
    erasureXi.push(Xi);
    sigmaE = polyMul(sigmaE, new Uint8Array([Xi, 1]));
  }

  // Step 3: Compute Forney syndromes via recursive update
  // For each erasure locator X_i: S[k] ← S[k] ⊕ X_i·S[k-1] (k from high to low)
  // After v erasures, fS[v..nsym-1] are the Forney syndromes for BM.
  const fS = S.slice();
  for (const Xi of erasureXi) {
    for (let k = nsym - 1; k >= 1; k--) {
      fS[k] ^= gfMul(Xi, fS[k - 1]);
    }
  }

  // Step 4: BM on Forney syndromes to find error-only locator
  const numForney = nsym - v;
  let C = [1], B = [1], L = 0, m = 1, b = 1;

  if (numForney > 0) {
    for (let nn = 0; nn < numForney; nn++) {
      let d = fS[nn + v];
      for (let i = 1; i <= L; i++) {
        if (i < C.length && nn - i >= 0) d ^= gfMul(C[i], fS[nn + v - i]);
      }
      if (d === 0) {
        m++;
      } else if (2 * L <= nn) {
        const T = C.slice();
        const coef = gfDiv(d, b);
        const shB = new Array(m).fill(0).concat(B);
        while (C.length < shB.length) C.push(0);
        for (let i = 0; i < shB.length; i++) C[i] ^= gfMul(coef, shB[i]);
        L = nn + 1 - L;
        B = T;
        b = d;
        m = 1;
      } else {
        const coef = gfDiv(d, b);
        const shB = new Array(m).fill(0).concat(B);
        while (C.length < shB.length) C.push(0);
        for (let i = 0; i < shB.length; i++) C[i] ^= gfMul(coef, shB[i]);
        m++;
      }
    }
  }

  while (C.length > 1 && C[C.length - 1] === 0) C.pop();
  const numErrors = L;

  // Capacity check: 2*errors + erasures ≤ nsym
  if (2 * numErrors + v > nsym) {
    return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
  }

  // Step 5: Find error positions via Chien search on error-only locator
  const errLocH = C.slice().reverse();
  const errPos = [];
  const erasureSet = new Set(erasurePositions);
  for (let j = 0; j < n; j++) {
    if (polyEval(new Uint8Array(errLocH), gfPow(2, 255 - j)) === 0) {
      const pos = n - 1 - j;
      if (!erasureSet.has(pos)) {
        errPos.push(pos);
      }
    }
  }
  if (errPos.length !== numErrors) {
    return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
  }

  // Step 6: Full locator = Λ_e · Λ_err (ascending convention)
  // sigmaE is big-endian from polyMul; convert to ascending to match C
  const sigmaE_asc = Array.from(sigmaE).reverse();
  // Ascending convolution
  const fullC = new Array(sigmaE_asc.length + C.length - 1).fill(0);
  for (let i = 0; i < sigmaE_asc.length; i++)
    for (let j = 0; j < C.length; j++)
      fullC[i + j] ^= gfMul(sigmaE_asc[i], C[j]);

  // All correction positions
  const allPos = [...erasurePositions, ...errPos];

  // Step 7: Error evaluator ω(x) = S(x) · σ(x) mod x^nsym
  const omFull = new Array(S.length + fullC.length - 1).fill(0);
  for (let i = 0; i < S.length; i++)
    for (let j = 0; j < fullC.length; j++)
      omFull[i + j] ^= gfMul(S[i], fullC[j]);
  const omH = omFull.slice(0, nsym).reverse();

  // Formal derivative of full locator (odd-indexed coefficients)
  const dLow = [];
  for (let k = 1; k < fullC.length; k += 2) {
    while (dLow.length < k) dLow.push(0);
    dLow[k - 1] = fullC[k];
  }
  if (dLow.length === 0) dLow.push(0);
  const dH = dLow.slice().reverse();

  // Step 8: Forney algorithm for all positions (erasures + errors)
  for (const pos of allPos) {
    const Xi = gfPow(2, n - 1 - pos);
    const XiInv = gfInv(Xi);
    const omVal = polyEval(new Uint8Array(omH), XiInv);
    const dVal = polyEval(new Uint8Array(dH), XiInv);
    if (dVal === 0) return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
    r[pos] ^= gfMul(Xi, gfDiv(omVal, dVal));
  }

  // Verify syndromes are zero
  for (let i = 0; i < nsym; i++) {
    if (polyEval(r, gfPow(2, i)) !== 0) {
      return { ok: false, data: r.slice(0, n - nsym), corrected: -1 };
    }
  }

  return { ok: true, data: r.slice(0, n - nsym), corrected: allPos.length };
}

// --------------------------------------------------------------------------
// Spatial interleaver — pseudo-random byte permutation
// Decorrelates spatially clustered errors across RS blocks.
// Uses deterministic Fisher-Yates with seeded LCG.
// --------------------------------------------------------------------------
const _interleaveCache = new Map();

function generateInterleaveTable(size) {
  if (_interleaveCache.has(size)) return _interleaveCache.get(size);
  const fwd = new Uint32Array(size);
  for (let i = 0; i < size; i++) fwd[i] = i;
  let state = (0x41555258 ^ size) >>> 0; // seed = "AURX" XOR size
  for (let i = size - 1; i > 0; i--) {
    state = ((state * 1664525 + 1013904223) & 0xFFFFFFFF) >>> 0;
    const j = state % (i + 1);
    const tmp = fwd[i]; fwd[i] = fwd[j]; fwd[j] = tmp;
  }
  const inv = new Uint32Array(size);
  for (let i = 0; i < size; i++) inv[fwd[i]] = i;
  const result = { fwd, inv };
  _interleaveCache.set(size, result);
  return result;
}

function interleaveFrame(frame, size) {
  const { fwd } = generateInterleaveTable(size);
  const out = new Uint8Array(frame.length);
  for (let i = 0; i < size && i < frame.length; i++) out[fwd[i]] = frame[i];
  for (let i = size; i < frame.length; i++) out[i] = frame[i];
  return out;
}

function deinterleaveFrame(frame, size) {
  const { inv } = generateInterleaveTable(size);
  const out = new Uint8Array(frame.length);
  for (let i = 0; i < size && i < frame.length; i++) out[inv[i]] = frame[i];
  for (let i = size; i < frame.length; i++) out[i] = frame[i];
  return out;
}

// --------------------------------------------------------------------------
// Chase-II soft-decision RS decoding
// Tries 2^K candidate codewords by flipping K least-reliable symbols.
// --------------------------------------------------------------------------

/**
 * Chase-II soft-decision RS decoding with optional erasure support.
 *
 * @param {Uint8Array} received - block to decode (length = blockSize)
 * @param {number} nsym - parity symbols
 * @param {Float32Array|null} reliability - per-symbol confidence (higher = more reliable)
 * @param {Uint8Array|null} altValues - per-symbol alternative byte values
 * @param {number} [K] - positions to trial-flip (default 4)
 * @param {number[]} [erasurePositions] - byte indices declared as erasures
 * @returns {object} { ok, data, corrected }
 */
function chaseRsDecode(received, nsym, reliability, altValues, K, erasurePositions) {
  K = K || 4;
  erasurePositions = erasurePositions || [];

  // Try erasure-aware decode first
  const stdResult = erasurePositions.length > 0
    ? rsDecodeWithErasures(received, nsym, erasurePositions)
    : rsDecode(received, nsym);
  if (stdResult.ok) return stdResult;
  if (!reliability || !altValues) return stdResult;

  const n = received.length;
  const indices = new Array(n);
  for (let i = 0; i < n; i++) indices[i] = i;
  indices.sort((a, b) => reliability[a] - reliability[b]);
  const weakest = indices.slice(0, Math.min(K, n));
  const numTrials = 1 << weakest.length;

  let bestResult = stdResult;
  let bestCorrected = Infinity;

  for (let mask = 1; mask < numTrials; mask++) {
    const trial = new Uint8Array(received);
    for (let bit = 0; bit < weakest.length; bit++) {
      if (mask & (1 << bit)) trial[weakest[bit]] = altValues[weakest[bit]];
    }
    const result = erasurePositions.length > 0
      ? rsDecodeWithErasures(trial, nsym, erasurePositions)
      : rsDecode(trial, nsym);
    if (result.ok && result.corrected < bestCorrected) {
      bestResult = result;
      bestCorrected = result.corrected;
      if (bestCorrected === 0) break;
    }
  }
  return bestResult;
}

// --------------------------------------------------------------------------
// HD RS encode/decode (multi-block interleaved + spatial interleaving)
// --------------------------------------------------------------------------
/**
 * HD RS encode with configurable parity.
 *
 * @param {Uint8Array} data - payload data
 * @param {number} rawBytes - total raw byte capacity of the module grid
 * @param {object} [opts]
 * @param {number} [opts.nsym=32] - parity symbols per block (32 = standard t=16, 64 = high-redundancy t=32)
 * @returns {object} { frame, numBlocks, nsym, blockSize, blockK, frameSize }
 */
function hdRsEncode(data, rawBytes, opts) {
  opts = opts || {};
  const nsym = opts.nsym || 32;
  const blockSize = 255;
  const numBlocks = Math.max(1, Math.floor(rawBytes / blockSize));
  const frameSize = numBlocks * blockSize;
  const frame = new Uint8Array(frameSize);
  const blockK = blockSize - nsym;

  for (let b = 0; b < numBlocks; b++) {
    const blockData = new Uint8Array(blockK);
    for (let i = 0; i < blockK; i++) {
      const srcIdx = i * numBlocks + b;
      blockData[i] = srcIdx < data.length ? data[srcIdx] : 0;
    }
    const encoded = rsEncode(blockData, nsym);
    for (let i = 0; i < blockSize; i++) {
      frame[i * numBlocks + b] = encoded[i];
    }
  }

  // Spatial interleaving: scatter frame bytes pseudo-randomly
  const interleaved = interleaveFrame(frame, frameSize);
  return { frame: interleaved, numBlocks, nsym, blockSize, blockK, frameSize };
}

/**
 * HD RS decode with configurable parity.
 *
 * @param {Uint8Array} frame - interleaved RS frame
 * @param {number} rawBytes - total raw byte capacity
 * @param {object} [opts]
 * @param {number} [opts.nsym=32] - parity symbols per block (must match encode)
 * @param {Float32Array} [opts.byteReliability] - per-byte confidence for Chase-II
 * @param {Uint8Array} [opts.byteAltValues] - per-byte alternative values for Chase-II
 * @param {number} [opts.chaseK=4] - Chase-II trial positions
 * @returns {object} { data, totalCorrected, failedBlocks, numBlocks, blockResults }
 */
function hdRsDecode(frame, rawBytes, opts) {
  opts = opts || {};
  const nsym = opts.nsym || 32;
  const blockSize = 255;
  const numBlocks = Math.max(1, Math.floor(rawBytes / blockSize));
  const frameSize = numBlocks * blockSize;
  const blockK = blockSize - nsym;
  const dataCapacity = blockK * numBlocks;
  const data = new Uint8Array(dataCapacity);
  let totalCorrected = 0;
  let failedBlocks = 0;
  const blockResults = [];

  // Spatial de-interleaving: undo pseudo-random scatter
  const deinterleaved = deinterleaveFrame(frame, frameSize);

  // Also de-interleave reliability, altValues, and erasure positions if provided
  let deintReliability = null, deintAltValues = null;
  const { inv } = generateInterleaveTable(frameSize);
  if (opts.byteReliability && opts.byteAltValues) {
    deintReliability = new Float32Array(frameSize);
    deintAltValues = new Uint8Array(frameSize);
    for (let i = 0; i < frameSize && i < opts.byteReliability.length; i++) {
      deintReliability[inv[i]] = opts.byteReliability[i];
      deintAltValues[inv[i]] = opts.byteAltValues[i];
    }
  }

  // De-interleave erasure positions: map from interleaved frame indices to
  // de-interleaved frame indices, then to per-block positions.
  // erasurePositions are indices in the interleaved frame; inv[] maps them
  // to de-interleaved positions. Then deint_pos = i * numBlocks + b means
  // block b, position i within that block.
  const blockErasures = new Array(numBlocks);
  for (let b = 0; b < numBlocks; b++) blockErasures[b] = [];

  if (opts.erasurePositions && opts.erasurePositions.length > 0) {
    for (const ep of opts.erasurePositions) {
      if (ep >= frameSize) continue;
      const deintPos = inv[ep]; // position in de-interleaved frame
      const b = deintPos % numBlocks;
      const i = Math.floor(deintPos / numBlocks);
      if (i < blockSize) {
        blockErasures[b].push(i);
      }
    }
  }

  for (let b = 0; b < numBlocks; b++) {
    const block = new Uint8Array(blockSize);
    for (let i = 0; i < blockSize; i++) {
      const srcIdx = i * numBlocks + b;
      block[i] = srcIdx < deinterleaved.length ? deinterleaved[srcIdx] : 0;
    }

    let dec;
    const blockEr = blockErasures[b];
    if (deintReliability) {
      // Extract per-block reliability and alt values
      const blockRel = new Float32Array(blockSize);
      const blockAlt = new Uint8Array(blockSize);
      for (let i = 0; i < blockSize; i++) {
        const srcIdx = i * numBlocks + b;
        blockRel[i] = srcIdx < deintReliability.length ? deintReliability[srcIdx] : 1.0;
        blockAlt[i] = srcIdx < deintAltValues.length ? deintAltValues[srcIdx] : 0;
      }
      dec = chaseRsDecode(block, nsym, blockRel, blockAlt, opts.chaseK || 4, blockEr);
    } else if (blockEr.length > 0) {
      dec = rsDecodeWithErasures(block, nsym, blockEr);
    } else {
      dec = rsDecode(block, nsym);
    }

    blockResults.push({
      ok: dec.ok,
      corrected: dec.ok ? dec.corrected : -1,
      blockData: dec.ok ? dec.data : null,  // per-block decoded data for feedback
    });
    if (!dec.ok) {
      failedBlocks++;
      // Write uncorrected data for partial decode (better than zeros)
      for (let i = 0; i < blockK; i++) {
        data[i * numBlocks + b] = block[i];
      }
      continue;
    }
    totalCorrected += dec.corrected;
    for (let i = 0; i < blockK; i++) {
      data[i * numBlocks + b] = dec.data[i];
    }
  }

  // Multi-strategy block recovery for failed blocks:
  // 1. Per-block erasure escalation: auto-declare the N least-reliable bytes as
  //    erasures for increasing N. Each erasure costs 1 parity symbol (vs 2 for
  //    errors), so marking unreliable bytes as erasures frees correction capacity.
  // 2. Chase-K depth escalation: retry with K=6 (64 trials), K=8 (256 trials).
  // 3. Cross-strategy: combine auto-erasure with deeper Chase.
  if (failedBlocks > 0 && deintReliability) {
    // Pre-extract per-block data once for reuse
    const blockDataCache = new Array(numBlocks);
    for (let b = 0; b < numBlocks; b++) {
      if (blockResults[b].ok) continue;
      const block = new Uint8Array(blockSize);
      const blockRel = new Float32Array(blockSize);
      const blockAlt = new Uint8Array(blockSize);
      for (let i = 0; i < blockSize; i++) {
        const srcIdx = i * numBlocks + b;
        block[i] = srcIdx < deinterleaved.length ? deinterleaved[srcIdx] : 0;
        blockRel[i] = srcIdx < deintReliability.length ? deintReliability[srcIdx] : 1.0;
        blockAlt[i] = srcIdx < deintAltValues.length ? deintAltValues[srcIdx] : 0;
      }
      blockDataCache[b] = { block, blockRel, blockAlt };
    }

    // Strategy matrix: [erasure count fractions] × [Chase-K depths]
    // Keep Chase-K ≤ 6 when combined with erasures to bound runtime.
    // K=8 alone (eFrac=0) is the deepest single-strategy attempt.
    const erasureFractions = [0, 0.25, 0.50]; // fraction of nsym to declare as erasures
    const chaseKs = [6, 8];

    for (const eFrac of erasureFractions) {
      for (const deepK of chaseKs) {
        if (failedBlocks === 0) break;
        // Skip K=8 when combined with erasures — too expensive for marginal gain
        if (eFrac > 0 && deepK > 6) continue;

        for (let b = 0; b < numBlocks; b++) {
          if (blockResults[b].ok) continue;
          const { block, blockRel, blockAlt } = blockDataCache[b];

          // Build per-block auto-erasure: sort by reliability, take worst N
          let blockEr;
          if (eFrac > 0) {
            const maxErase = Math.floor(nsym * eFrac);
            const indices = new Array(blockSize);
            for (let i = 0; i < blockSize; i++) indices[i] = i;
            indices.sort((a, bb) => blockRel[a] - blockRel[bb]);
            blockEr = indices.slice(0, maxErase);
          } else {
            blockEr = blockErasures[b]; // Use original global erasures
          }

          const dec = chaseRsDecode(block, nsym, blockRel, blockAlt, deepK, blockEr);
          if (dec.ok) {
            blockResults[b] = {
              ok: true,
              corrected: dec.corrected,
              blockData: dec.data,
            };
            totalCorrected += dec.corrected;
            failedBlocks--;
            for (let i = 0; i < blockK; i++) {
              data[i * numBlocks + b] = dec.data[i];
            }
          }
        }
      }
      if (failedBlocks === 0) break;
    }
  }

  if (failedBlocks > 0) {
    return { data: null, partialData: data, totalCorrected, failedBlocks, numBlocks, blockResults, blockK, frameSize };
  }
  return { data, partialData: data, totalCorrected, failedBlocks: 0, numBlocks, blockResults, blockK, frameSize };
}

module.exports = {
  gfExp, gfLog, gfMul, gfDiv, gfPow, gfInv,
  polyMul, polyEval, generatorPoly,
  rsEncode, rsDecode, rsDecodeWithErasures, chaseRsDecode,
  generateInterleaveTable, interleaveFrame, deinterleaveFrame,
  hdRsEncode, hdRsDecode,
};
