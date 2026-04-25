/**
 * Aurexis Core V2 — Payload codec (header parsing, compression helpers)
 *
 * Extracted from aurexis_ed_unified.html (v12).
 * Pure JS, no DOM dependencies. Node-compatible.
 *
 * Note: Browser-only compression (DecompressionStream) is NOT included here.
 * For Node use, the caller must provide inflate/deflate functions.
 * For browser use, pass browserInflate as the inflate option.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

// --------------------------------------------------------------------------
// Constants
// --------------------------------------------------------------------------
const COMPRESS_FLAG_NONE              = 0x00;
const COMPRESS_FLAG_DEFLATE           = 0x01;
const COMPRESS_FLAG_DELTA_DEFLATE     = 0x10;
const COMPRESS_FLAG_BYTEPLANE_DEFLATE = 0x20;

// --------------------------------------------------------------------------
// Pre-filters (delta, byte-plane)
// --------------------------------------------------------------------------

function deltaEncode(data) {
  const out = new Uint8Array(data.length);
  out[0] = data[0];
  for (let i = 1; i < data.length; i++) out[i] = (data[i] - data[i - 1]) & 0xFF;
  return out;
}

function deltaDecode(data) {
  const out = new Uint8Array(data.length);
  out[0] = data[0];
  for (let i = 1; i < data.length; i++) out[i] = (out[i - 1] + data[i]) & 0xFF;
  return out;
}

function bytePlaneEncode(data) {
  const len = data.length;
  const out = new Uint8Array(len);
  for (let bit = 0; bit < 8; bit++) {
    const off = bit * Math.ceil(len / 8);
    for (let i = 0; i < len && off + i < len; i++) {
      out[off + i] = (out[off + i] || 0) | (((data[i] >> (7 - bit)) & 1) << (7 - (i & 7)));
    }
  }
  // Simplified: use the original E/D approach
  const planes = new Array(8);
  for (let b = 0; b < 8; b++) planes[b] = new Uint8Array(Math.ceil(len / 8));
  for (let i = 0; i < len; i++) {
    for (let b = 0; b < 8; b++) {
      if (data[i] & (1 << (7 - b))) {
        planes[b][i >> 3] |= (1 << (7 - (i & 7)));
      }
    }
  }
  const result = new Uint8Array(len);
  let pos = 0;
  for (let b = 0; b < 8; b++) {
    result.set(planes[b], pos);
    pos += planes[b].length;
  }
  return result.subarray(0, pos);
}

function bytePlaneDecode(data) {
  const planeSize = data.length / 8;
  const len = Math.floor(planeSize * 8);
  const out = new Uint8Array(len);
  for (let b = 0; b < 8; b++) {
    const off = Math.floor(b * planeSize);
    for (let i = 0; i < len; i++) {
      if (data[off + (i >> 3)] & (1 << (7 - (i & 7)))) {
        out[i] |= (1 << (7 - b));
      }
    }
  }
  return out;
}

// --------------------------------------------------------------------------
// HD Header parsing
// --------------------------------------------------------------------------

/**
 * Parse an AHDX header from decoded data.
 *
 * AHDX header layout:
 *   magic(4) "AHDX" + ver(1) + compFlag(1) + origSize(4) + compSize(4)
 *   + sha256(32) + fnameLen(2) + fname(fnameLen) + payload(compSize)
 *
 * @param {Uint8Array} data - raw decoded data
 * @returns {object|null} parsed header or null if invalid
 */
function parseHdHeader(data) {
  if (data.length < 48) return null;
  const magic = String.fromCharCode(data[0], data[1], data[2], data[3]);
  if (magic !== "AHDX") return null;
  const ver = data[4];
  if (ver !== 0x01) return null;

  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const compFlag = data[5];
  const origSize = view.getUint32(6, false);
  const compSize = view.getUint32(10, false);
  const sha256 = data.slice(14, 46);
  const fnameLen = view.getUint16(46, false);
  const filename = new TextDecoder("utf-8").decode(data.slice(48, 48 + fnameLen));
  const payloadStart = 48 + fnameLen;
  const payloadData = data.slice(payloadStart, payloadStart + compSize);

  return {
    magic, ver, compFlag, origSize, compSize,
    sha256, fnameLen, filename, payloadData, payloadStart,
  };
}

/**
 * Decompress payload based on compression flag.
 * For Node environments, requires zlib. For browser, requires async inflate.
 *
 * @param {Uint8Array} payloadData - compressed payload
 * @param {number} compFlag - compression flag
 * @param {object} [opts] - { inflate: function } — sync or async inflate
 * @returns {Uint8Array|Promise<Uint8Array>} decompressed data
 */
function decompressPayload(payloadData, compFlag, opts = {}) {
  if (compFlag === COMPRESS_FLAG_NONE) return payloadData;

  const inflate = opts.inflate;
  if (!inflate) {
    // Try Node zlib
    try {
      const zlib = require("zlib");
      const inflateSync = (buf) => new Uint8Array(zlib.inflateSync(Buffer.from(buf)));
      if (compFlag === COMPRESS_FLAG_DEFLATE) return inflateSync(payloadData);
      if (compFlag === COMPRESS_FLAG_DELTA_DEFLATE) return deltaDecode(inflateSync(payloadData));
      if (compFlag === COMPRESS_FLAG_BYTEPLANE_DEFLATE) return bytePlaneDecode(inflateSync(payloadData));
    } catch (e) {
      throw new Error("No inflate function available and zlib not found");
    }
  }

  // Use provided inflate function
  const inflated = inflate(payloadData);
  if (inflated && typeof inflated.then === "function") {
    // Async path
    return inflated.then(data => {
      if (compFlag === COMPRESS_FLAG_DEFLATE) return data;
      if (compFlag === COMPRESS_FLAG_DELTA_DEFLATE) return deltaDecode(data);
      if (compFlag === COMPRESS_FLAG_BYTEPLANE_DEFLATE) return bytePlaneDecode(data);
      return data;
    });
  }
  // Sync path
  if (compFlag === COMPRESS_FLAG_DEFLATE) return inflated;
  if (compFlag === COMPRESS_FLAG_DELTA_DEFLATE) return deltaDecode(inflated);
  if (compFlag === COMPRESS_FLAG_BYTEPLANE_DEFLATE) return bytePlaneDecode(inflated);
  return inflated;
}

module.exports = {
  COMPRESS_FLAG_NONE, COMPRESS_FLAG_DEFLATE,
  COMPRESS_FLAG_DELTA_DEFLATE, COMPRESS_FLAG_BYTEPLANE_DEFLATE,
  deltaEncode, deltaDecode,
  bytePlaneEncode, bytePlaneDecode,
  parseHdHeader, decompressPayload,
};
