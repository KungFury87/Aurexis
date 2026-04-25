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
 * @param {Uint8Array} received - block to decode (length = blockSize)
 * @param {number} nsym - parity symbols
 * @param {Float32Array|null} reliability - per-symbol confidence (higher = more reliable)
 * @param {Uint8Array|null} altValues - per-symbol alternative byte values
 * @param {number} [K] - positions to trial-flip (default 4)
 * @returns {object} { ok, data, corrected }
 */
function chaseRsDecode(received, nsym, reliability, altValues, K) {
  K = K || 4;
  const stdResult = rsDecode(received, nsym);
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
    const result = rsDecode(trial, nsym);
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
function hdRsEncode(data, rawBytes) {
  const nsym = 32;
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

function hdRsDecode(frame, rawBytes, opts) {
  opts = opts || {};
  const nsym = 32;
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

  // Also de-interleave reliability and altValues if provided (for Chase-II)
  let deintReliability = null, deintAltValues = null;
  if (opts.byteReliability && opts.byteAltValues) {
    deintReliability = new Float32Array(frameSize);
    deintAltValues = new Uint8Array(frameSize);
    const { inv } = generateInterleaveTable(frameSize);
    for (let i = 0; i < frameSize && i < opts.byteReliability.length; i++) {
      deintReliability[inv[i]] = opts.byteReliability[i];
      deintAltValues[inv[i]] = opts.byteAltValues[i];
    }
  }

  for (let b = 0; b < numBlocks; b++) {
    const block = new Uint8Array(blockSize);
    for (let i = 0; i < blockSize; i++) {
      const srcIdx = i * numBlocks + b;
      block[i] = srcIdx < deinterleaved.length ? deinterleaved[srcIdx] : 0;
    }

    let dec;
    if (deintReliability) {
      // Extract per-block reliability and alt values
      const blockRel = new Float32Array(blockSize);
      const blockAlt = new Uint8Array(blockSize);
      for (let i = 0; i < blockSize; i++) {
        const srcIdx = i * numBlocks + b;
        blockRel[i] = srcIdx < deintReliability.length ? deintReliability[srcIdx] : 1.0;
        blockAlt[i] = srcIdx < deintAltValues.length ? deintAltValues[srcIdx] : 0;
      }
      dec = chaseRsDecode(block, nsym, blockRel, blockAlt, opts.chaseK || 4);
    } else {
      dec = rsDecode(block, nsym);
    }

    blockResults.push({ ok: dec.ok, corrected: dec.ok ? dec.corrected : -1 });
    if (!dec.ok) {
      failedBlocks++;
      continue;
    }
    totalCorrected += dec.corrected;
    for (let i = 0; i < blockK; i++) {
      data[i * numBlocks + b] = dec.data[i];
    }
  }
  if (failedBlocks > 0) {
    return { data: null, totalCorrected, failedBlocks, numBlocks, blockResults };
  }
  return { data, totalCorrected, failedBlocks: 0, numBlocks, blockResults };
}

module.exports = {
  gfExp, gfLog, gfMul, gfDiv, gfPow, gfInv,
  polyMul, polyEval, generatorPoly,
  rsEncode, rsDecode, chaseRsDecode,
  generateInterleaveTable, interleaveFrame, deinterleaveFrame,
  hdRsEncode, hdRsDecode,
};
