/**
 * Aurexis Core V2 — Synthetic Artifact Renderer
 *
 * Renders HD artifacts as raw RGBA pixel buffers. No DOM, no Canvas API.
 * Exact match to aurexis_ed_unified.html layout: finders, timing, orientation,
 * data modules. Used for synthetic testing of the decode pipeline.
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

const format = require("./format");
const gfRs = require("./gf_rs");
const sampler = require("./sampler");
const codec = require("./codec");

// --------------------------------------------------------------------------
// Finder and orientation bitmaps (exact match to E/D HTML)
// --------------------------------------------------------------------------
const FINDER_BITMAP = [
  [1,1,1,1,1,1,1],
  [1,0,0,0,0,0,1],
  [1,0,1,1,1,0,1],
  [1,0,1,1,1,0,1],
  [1,0,1,1,1,0,1],
  [1,0,0,0,0,0,1],
  [1,1,1,1,1,1,1],
];

const ORIENT_BITMAP = [
  [1,1,1,1,1],
  [1,0,0,0,1],
  [1,0,1,0,1],
  [1,0,0,0,1],
  [1,1,1,1,1],
];

// --------------------------------------------------------------------------
// RGBA pixel buffer helpers
// --------------------------------------------------------------------------

function createRGBA(w, h) {
  return { data: new Uint8Array(w * h * 4), width: w, height: h };
}

function fillRect(img, x0, y0, w, h, r, g, b) {
  const ix = Math.floor(x0), iy = Math.floor(y0);
  const iw = Math.ceil(w), ih = Math.ceil(h);
  for (let dy = 0; dy < ih; dy++) {
    for (let dx = 0; dx < iw; dx++) {
      const px = ix + dx, py = iy + dy;
      if (px < 0 || py < 0 || px >= img.width || py >= img.height) continue;
      const idx = (py * img.width + px) * 4;
      img.data[idx] = r; img.data[idx + 1] = g;
      img.data[idx + 2] = b; img.data[idx + 3] = 255;
    }
  }
}

// --------------------------------------------------------------------------
// Symbol frame drawing (finders + timing + orientation)
// --------------------------------------------------------------------------

function drawFinderAt(img, x, y, modPx) {
  for (let r = 0; r < 7; r++) {
    for (let c = 0; c < 7; c++) {
      const color = FINDER_BITMAP[r][c] ? [0, 0, 0] : [255, 255, 255];
      fillRect(img, Math.floor(x + c * modPx), Math.floor(y + r * modPx),
               Math.ceil(modPx), Math.ceil(modPx), color[0], color[1], color[2]);
    }
  }
}

function drawOrientAt(img, x, y, modPx) {
  for (let r = 0; r < 5; r++) {
    for (let c = 0; c < 5; c++) {
      const color = ORIENT_BITMAP[r][c] ? [0, 0, 0] : [255, 255, 255];
      fillRect(img, Math.floor(x + c * modPx), Math.floor(y + r * modPx),
               Math.ceil(modPx), Math.ceil(modPx), color[0], color[1], color[2]);
    }
  }
}

function drawSymbolFrame(img, layout) {
  const { canvasPx, qzPx, modPx, totalMod } = layout;

  // White background (quiet zone + separators)
  fillRect(img, 0, 0, canvasPx, canvasPx, 255, 255, 255);

  // TL finder
  drawFinderAt(img, qzPx, qzPx, modPx);
  // TR finder
  drawFinderAt(img, qzPx + (totalMod - 7) * modPx, qzPx, modPx);
  // BL finder
  drawFinderAt(img, qzPx, qzPx + (totalMod - 7) * modPx, modPx);
  // BR orientation (5x5 centered in the 7-module zone at bottom-right)
  drawOrientAt(img, qzPx + (totalMod - 6) * modPx, qzPx + (totalMod - 6) * modPx, modPx);

  // Horizontal timing strip: row 6, cols 7 to totalMod-8
  for (let c = 7; c < totalMod - 7; c++) {
    const dark = (c % 2 === 0);
    const color = dark ? 0 : 255;
    fillRect(img,
      Math.floor(qzPx + c * modPx), Math.floor(qzPx + 6 * modPx),
      Math.ceil(modPx), Math.ceil(modPx), color, color, color);
  }

  // Vertical timing strip: col 6, rows 7 to totalMod-8
  for (let r = 7; r < totalMod - 7; r++) {
    const dark = (r % 2 === 0);
    const color = dark ? 0 : 255;
    fillRect(img,
      Math.floor(qzPx + 6 * modPx), Math.floor(qzPx + r * modPx),
      Math.ceil(modPx), Math.ceil(modPx), color, color, color);
  }
}

// --------------------------------------------------------------------------
// Render a complete HD artifact to RGBA
// --------------------------------------------------------------------------

/**
 * Render module data into a full artifact image.
 *
 * @param {Uint8Array} modules - grid*grid module values (color indices)
 * @param {object} config - HD config (grid, colors, bpm, canvasPx)
 * @returns {{ data: Uint8Array, width: number, height: number }}
 */
function renderArtifact(modules, config) {
  const layout = format.computeSymbolLayout(config.grid, config.canvasPx);
  const img = createRGBA(config.canvasPx, config.canvasPx);

  // Draw structural frame
  drawSymbolFrame(img, layout);

  // Draw data modules
  const palette = sampler.hdGetPalette(config.colors);
  const modPx = layout.modPx;
  const dataOrigin = layout.dataOriginPx;

  for (let r = 0; r < config.grid; r++) {
    for (let c = 0; c < config.grid; c++) {
      const colorIdx = modules[r * config.grid + c] % palette.length;
      const col = palette[colorIdx];
      fillRect(img,
        Math.floor(dataOrigin + c * modPx), Math.floor(dataOrigin + r * modPx),
        Math.ceil(modPx), Math.ceil(modPx), col[0], col[1], col[2]);
    }
  }

  return img;
}

// --------------------------------------------------------------------------
// Full encode → render pipeline (payload to RGBA image)
// --------------------------------------------------------------------------

/**
 * Encode a payload and render it as an HD artifact image.
 *
 * @param {Uint8Array|Buffer|string} payload - data to encode
 * @param {string} filename - filename for AHDX header
 * @param {object} [opts]
 * @param {string} [opts.configName] - HD config name (default: "128x128-4c")
 * @param {number} [opts.compFlag] - compression flag (default: NONE)
 * @returns {{ img, config, configName, modules, rsInfo, layout, header }}
 */
function encodeAndRender(payload, filename, opts = {}) {
  const configName = opts.configName || "128x128-4c";
  const config = format.HD_CONFIGS[configName];
  if (!config) throw new Error(`Unknown config: ${configName}`);

  const compFlag = opts.compFlag !== undefined ? opts.compFlag : codec.COMPRESS_FLAG_NONE;

  // Convert string payload
  let payloadBytes;
  if (typeof payload === "string") {
    payloadBytes = new TextEncoder().encode(payload);
  } else {
    payloadBytes = new Uint8Array(payload);
  }

  // Optionally compress
  let compressedPayload = payloadBytes;
  if (compFlag === codec.COMPRESS_FLAG_DEFLATE) {
    const zlib = require("zlib");
    compressedPayload = new Uint8Array(zlib.deflateSync(Buffer.from(payloadBytes)));
  } else if (compFlag === codec.COMPRESS_FLAG_DELTA_DEFLATE) {
    const zlib = require("zlib");
    compressedPayload = new Uint8Array(zlib.deflateSync(Buffer.from(codec.deltaEncode(payloadBytes))));
  }

  // Build AHDX header
  const fnameBytes = new TextEncoder().encode(filename);
  const sha256 = new Uint8Array(32); // placeholder hash
  // Simple hash for testing
  for (let i = 0; i < payloadBytes.length && i < 32; i++) {
    sha256[i] = (payloadBytes[i] ^ 0xAB) & 0xFF;
  }

  const headerSize = 48 + fnameBytes.length;
  const fullData = new Uint8Array(headerSize + compressedPayload.length);

  // AHDX magic
  fullData[0] = 0x41; fullData[1] = 0x48; fullData[2] = 0x44; fullData[3] = 0x58;
  fullData[4] = 0x01; // version
  fullData[5] = compFlag;
  const dv = new DataView(fullData.buffer);
  dv.setUint32(6, payloadBytes.length, false);   // origSize
  dv.setUint32(10, compressedPayload.length, false); // compSize
  fullData.set(sha256, 14);
  dv.setUint16(46, fnameBytes.length, false);
  fullData.set(fnameBytes, 48);
  fullData.set(compressedPayload, headerSize);

  // RS encode
  const cap = format.hdCalcCapacity(config);
  if (fullData.length > cap.dataBytes) {
    throw new Error(`Payload too large: ${fullData.length} > ${cap.dataBytes} data bytes for ${configName}`);
  }

  const rsResult = gfRs.hdRsEncode(fullData, cap.rawBytes);

  // Unpack RS frame into module color indices
  const totalModules = config.grid * config.grid;
  const modules = sampler.hdUnpackModules(rsResult.frame, totalModules, config.bpm);

  // Render
  const layout = format.computeSymbolLayout(config.grid, config.canvasPx);
  const img = renderArtifact(modules, config);

  return {
    img,
    config,
    configName,
    modules,
    rsInfo: rsResult,
    layout,
    fullData,
    cap,
    header: {
      magic: "AHDX", ver: 1, compFlag,
      origSize: payloadBytes.length,
      compSize: compressedPayload.length,
      sha256, filename,
      payloadData: compressedPayload,
    },
  };
}

// --------------------------------------------------------------------------
// Perspective warp (forward: canonical → warped image)
// --------------------------------------------------------------------------

/**
 * Apply a perspective warp to an image.
 * Maps source corners to destination corners using bilinear interpolation.
 *
 * @param {object} srcImg - { data, width, height } RGBA source
 * @param {number} dstW - destination width
 * @param {number} dstH - destination height
 * @param {{x:number,y:number}[]} srcCorners - [TL, TR, BL, BR] in source
 * @param {{x:number,y:number}[]} dstCorners - [TL, TR, BL, BR] in destination
 * @param {number[]} [bgColor] - [r,g,b] background color (default: [200,200,200])
 * @returns {object} { data, width, height } warped RGBA image
 */
function perspectiveWarp(srcImg, dstW, dstH, srcCorners, dstCorners, bgColor) {
  bgColor = bgColor || [200, 200, 200];
  const dst = createRGBA(dstW, dstH);

  // Fill with background
  for (let i = 0; i < dst.data.length; i += 4) {
    dst.data[i] = bgColor[0]; dst.data[i + 1] = bgColor[1];
    dst.data[i + 2] = bgColor[2]; dst.data[i + 3] = 255;
  }

  // Compute inverse homography: dst → src
  // We need to go from destination pixels back to source pixels
  const homography = require("./homography");
  const H = homography.computeHomography(dstCorners, srcCorners);
  if (!H) return dst;

  for (let y = 0; y < dstH; y++) {
    for (let x = 0; x < dstW; x++) {
      const sp = homography.applyHomography(H, { x, y });
      const sx = sp.x, sy = sp.y;
      if (sx < 0 || sy < 0 || sx >= srcImg.width - 1 || sy >= srcImg.height - 1) continue;

      // Bilinear interpolation
      const ix = Math.floor(sx), iy = Math.floor(sy);
      const fx = sx - ix, fy = sy - iy;

      const i00 = (iy * srcImg.width + ix) * 4;
      const i10 = i00 + 4;
      const i01 = i00 + srcImg.width * 4;
      const i11 = i01 + 4;

      const didx = (y * dstW + x) * 4;
      for (let ch = 0; ch < 3; ch++) {
        const v = (1 - fx) * (1 - fy) * srcImg.data[i00 + ch]
                + fx * (1 - fy) * srcImg.data[i10 + ch]
                + (1 - fx) * fy * srcImg.data[i01 + ch]
                + fx * fy * srcImg.data[i11 + ch];
        dst.data[didx + ch] = Math.round(Math.min(255, Math.max(0, v)));
      }
      dst.data[didx + 3] = 255;
    }
  }

  return dst;
}

// --------------------------------------------------------------------------
// Noise injection
// --------------------------------------------------------------------------

/**
 * Add Gaussian noise to an image.
 * @param {object} img - { data, width, height }
 * @param {number} sigma - noise standard deviation (0-50 typical)
 * @returns {object} new image with noise added
 */
function addGaussianNoise(img, sigma) {
  const out = createRGBA(img.width, img.height);
  out.data.set(img.data);
  for (let i = 0; i < out.data.length; i += 4) {
    for (let ch = 0; ch < 3; ch++) {
      // Box-Muller transform
      const u1 = Math.random() || 0.001;
      const u2 = Math.random();
      const n = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * sigma;
      out.data[i + ch] = Math.round(Math.min(255, Math.max(0, out.data[i + ch] + n)));
    }
  }
  return out;
}

// --------------------------------------------------------------------------
// PPM export (for visual inspection, no external deps)
// --------------------------------------------------------------------------

/**
 * Export an RGBA image to PPM format (binary P6).
 * @param {object} img - { data, width, height }
 * @returns {Buffer} PPM file contents
 */
function toPPM(img) {
  const header = `P6\n${img.width} ${img.height}\n255\n`;
  const headerBuf = Buffer.from(header, "ascii");
  const pixBuf = Buffer.alloc(img.width * img.height * 3);
  for (let i = 0, j = 0; i < img.data.length; i += 4, j += 3) {
    pixBuf[j] = img.data[i]; pixBuf[j + 1] = img.data[i + 1]; pixBuf[j + 2] = img.data[i + 2];
  }
  return Buffer.concat([headerBuf, pixBuf]);
}

module.exports = {
  FINDER_BITMAP, ORIENT_BITMAP,
  createRGBA, fillRect,
  drawFinderAt, drawOrientAt, drawSymbolFrame,
  renderArtifact,
  encodeAndRender,
  perspectiveWarp,
  addGaussianNoise,
  toPPM,
};
