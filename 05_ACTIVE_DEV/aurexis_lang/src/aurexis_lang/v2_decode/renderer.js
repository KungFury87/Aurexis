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

function drawAlignmentAt(img, x, y, modPx) {
  // 3×3 alignment pattern: white ring with dark center (high-contrast target)
  const AP = format.ALIGNMENT_PATTERN;
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      const dark = AP[r][c];
      const color = dark ? [0, 0, 0] : [255, 255, 255];
      fillRect(img, Math.floor(x + c * modPx), Math.floor(y + r * modPx),
               Math.ceil(modPx), Math.ceil(modPx), color[0], color[1], color[2]);
    }
  }
}

function drawSymbolFrame(img, layout, gs) {
  const { canvasPx, qzPx, modPx, totalMod, dataOriginPx } = layout;

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

  // Alignment patterns in the data grid
  if (gs) {
    const alignInfo = format.computeAlignmentPatternPositions(gs);
    for (const { r, c } of alignInfo.centers) {
      const ax = dataOriginPx + (c - 1) * modPx; // center is at (r,c), pattern starts 1 left/up
      const ay = dataOriginPx + (r - 1) * modPx;
      drawAlignmentAt(img, ax, ay, modPx);
    }
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
/**
 * Render module data into a full artifact image.
 * Data modules are mapped to grid positions via the alignment mapping —
 * alignment pattern positions are skipped (drawn by drawSymbolFrame).
 *
 * @param {Uint8Array} modules - data module values (length = dataModules, not grid*grid)
 * @param {object} config - HD config
 * @param {object} alignMapping - from format.buildAlignmentMapping
 * @returns {{ data: Uint8Array, width: number, height: number }}
 */
function renderArtifact(modules, config, alignMapping) {
  const layout = format.computeSymbolLayout(config.grid, config.canvasPx);
  const img = createRGBA(config.canvasPx, config.canvasPx);

  // Draw structural frame (finders, timing, alignment patterns)
  drawSymbolFrame(img, layout, config.grid);

  // Draw data modules at mapped grid positions
  const palette = sampler.hdGetPalette(config.colors);
  const modPx = layout.modPx;
  const dataOrigin = layout.dataOriginPx;

  for (let di = 0; di < modules.length && di < alignMapping.dataToGrid.length; di++) {
    const { r, c } = alignMapping.dataToGrid[di];
    const colorIdx = modules[di] % palette.length;
    const col = palette[colorIdx];
    fillRect(img,
      Math.floor(dataOrigin + c * modPx), Math.floor(dataOrigin + r * modPx),
      Math.ceil(modPx), Math.ceil(modPx), col[0], col[1], col[2]);
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
 * @param {number} [opts.nsym] - RS parity symbols per block (32=standard, 64=high-redundancy)
 * @returns {{ img, config, configName, modules, rsInfo, layout, header, stats }}
 */
function encodeAndRender(payload, filename, opts = {}) {
  const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();

  // ── Input validation ──────────────────────────────────────────
  if (payload === null || payload === undefined) {
    throw new Error("Payload is required (string or Uint8Array)");
  }
  if (typeof filename !== "string" || filename.length === 0) {
    throw new Error("Filename is required (non-empty string)");
  }
  if (filename.length > 255) {
    throw new Error(`Filename too long: ${filename.length} bytes (max 255)`);
  }

  const configName = opts.configName || "128x128-4c";
  const config = format.HD_CONFIGS[configName];
  if (!config) {
    const validNames = Object.keys(format.HD_CONFIGS).join(", ");
    throw new Error(`Unknown config: ${configName}. Valid configs: ${validNames}`);
  }

  let compFlag = opts.compFlag !== undefined ? opts.compFlag : codec.COMPRESS_FLAG_NONE;
  const VALID_COMP_FLAGS = [
    codec.COMPRESS_FLAG_NONE, codec.COMPRESS_FLAG_DEFLATE,
    codec.COMPRESS_FLAG_DELTA_DEFLATE, codec.COMPRESS_FLAG_BYTEPLANE_DEFLATE,
    "auto",
  ];
  if (!VALID_COMP_FLAGS.includes(compFlag)) {
    throw new Error(`Invalid compFlag: ${compFlag}. Must be 0x00 (none), 0x01 (deflate), 0x10 (delta-deflate), 0x20 (byteplane-deflate), or "auto"`);
  }
  const nsym = opts.nsym || 32;
  if (nsym < 2 || nsym > 64 || nsym % 2 !== 0) {
    throw new Error(`Invalid nsym: ${nsym}. Must be even integer 2-64`);
  }

  // Convert string payload
  let payloadBytes;
  if (typeof payload === "string") {
    payloadBytes = new TextEncoder().encode(payload);
  } else if (payload instanceof Uint8Array || Buffer.isBuffer(payload)) {
    payloadBytes = new Uint8Array(payload);
  } else {
    throw new Error("Payload must be a string, Uint8Array, or Buffer");
  }

  if (payloadBytes.length === 0) {
    throw new Error("Payload must not be empty");
  }

  // Compress payload
  const zlib = require("zlib");
  let compressedPayload = payloadBytes;

  if (compFlag === "auto") {
    // Try all compression methods, pick the smallest
    const candidates = [
      { flag: codec.COMPRESS_FLAG_NONE, data: payloadBytes },
      { flag: codec.COMPRESS_FLAG_DEFLATE,
        data: new Uint8Array(zlib.deflateSync(Buffer.from(payloadBytes))) },
    ];
    // Delta-deflate and byteplane-deflate may throw on very small payloads
    try {
      candidates.push({
        flag: codec.COMPRESS_FLAG_DELTA_DEFLATE,
        data: new Uint8Array(zlib.deflateSync(Buffer.from(codec.deltaEncode(payloadBytes)))),
      });
    } catch (_) { /* skip if delta encoding fails */ }
    try {
      candidates.push({
        flag: codec.COMPRESS_FLAG_BYTEPLANE_DEFLATE,
        data: new Uint8Array(zlib.deflateSync(Buffer.from(codec.bytePlaneEncode(payloadBytes)))),
      });
    } catch (_) { /* skip if byteplane encoding fails */ }

    candidates.sort((a, b) => a.data.length - b.data.length);
    compFlag = candidates[0].flag;
    compressedPayload = candidates[0].data;
  } else if (compFlag === codec.COMPRESS_FLAG_DEFLATE) {
    compressedPayload = new Uint8Array(zlib.deflateSync(Buffer.from(payloadBytes)));
  } else if (compFlag === codec.COMPRESS_FLAG_DELTA_DEFLATE) {
    compressedPayload = new Uint8Array(zlib.deflateSync(Buffer.from(codec.deltaEncode(payloadBytes))));
  } else if (compFlag === codec.COMPRESS_FLAG_BYTEPLANE_DEFLATE) {
    compressedPayload = new Uint8Array(zlib.deflateSync(Buffer.from(codec.bytePlaneEncode(payloadBytes))));
  }

  // Build AHDX header
  const fnameBytes = new TextEncoder().encode(filename);
  // Compute real SHA-256 of original (uncompressed) payload
  const crypto = require("crypto");
  const sha256 = new Uint8Array(crypto.createHash("sha256").update(payloadBytes).digest());

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
  const cap = format.hdCalcCapacity(config, { nsym });
  if (fullData.length > cap.dataBytes) {
    throw new Error(`Payload too large: ${fullData.length} > ${cap.dataBytes} data bytes for ${configName} (nsym=${nsym})`);
  }

  const rsResult = gfRs.hdRsEncode(fullData, cap.rawBytes, { nsym });

  // Unpack RS frame into data module color indices (skipping alignment positions)
  const dataModuleCount = cap.dataModules;
  const modules = sampler.hdUnpackModules(rsResult.frame, dataModuleCount, config.bpm);

  // Build alignment mapping for grid placement
  const alignMapping = format.buildAlignmentMapping(config.grid, cap.alignInfo.mask);

  // Render
  const layout = format.computeSymbolLayout(config.grid, config.canvasPx);
  const img = renderArtifact(modules, config, alignMapping);

  const COMP_METHOD_NAMES = {
    [codec.COMPRESS_FLAG_NONE]: "none",
    [codec.COMPRESS_FLAG_DEFLATE]: "deflate",
    [codec.COMPRESS_FLAG_DELTA_DEFLATE]: "delta-deflate",
    [codec.COMPRESS_FLAG_BYTEPLANE_DEFLATE]: "byteplane-deflate",
  };

  const t1 = typeof performance !== "undefined" ? performance.now() : Date.now();

  return {
    img,
    config,
    configName,
    modules,       // data modules only (excludes alignment positions)
    alignMapping,  // mapping between data indices and grid positions
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
    stats: {
      compressionMethod: COMP_METHOD_NAMES[compFlag] || "unknown",
      compressionRatio: payloadBytes.length > 0
        ? +(compressedPayload.length / payloadBytes.length).toFixed(4)
        : 1,
      originalBytes: payloadBytes.length,
      compressedBytes: compressedPayload.length,
      headerBytes: 48 + new TextEncoder().encode(filename).length,
      totalEncodedBytes: fullData.length,
      rsCapacityBytes: cap.dataBytes,
      capacityUsed: +(fullData.length / cap.dataBytes).toFixed(4),
      encodingTimeMs: +(t1 - t0).toFixed(2),
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
// Brightness gradient simulation (uneven lighting)
// --------------------------------------------------------------------------

/**
 * Apply a linear brightness gradient across an image.
 * Simulates uneven lighting — one side brighter, other darker.
 *
 * @param {object} img - { data, width, height }
 * @param {number} brightScale - brightness multiplier at the bright side (e.g., 1.5)
 * @param {number} darkScale - brightness multiplier at the dark side (e.g., 0.5)
 * @param {string} [direction="horizontal"] - gradient direction ("horizontal" or "vertical" or "diagonal")
 * @returns {object} { data, width, height }
 */
function applyBrightnessGradient(img, brightScale, darkScale, direction) {
  direction = direction || "horizontal";
  const { data, width, height } = img;
  const out = createRGBA(width, height);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let t; // 0..1 interpolation factor
      if (direction === "horizontal") {
        t = x / (width - 1);
      } else if (direction === "vertical") {
        t = y / (height - 1);
      } else { // diagonal
        t = (x / (width - 1) + y / (height - 1)) / 2;
      }
      const scale = darkScale + t * (brightScale - darkScale);
      const idx = (y * width + x) * 4;
      out.data[idx] = Math.round(Math.min(255, Math.max(0, data[idx] * scale)));
      out.data[idx + 1] = Math.round(Math.min(255, Math.max(0, data[idx + 1] * scale)));
      out.data[idx + 2] = Math.round(Math.min(255, Math.max(0, data[idx + 2] * scale)));
      out.data[idx + 3] = data[idx + 3];
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

// --------------------------------------------------------------------------
// Gaussian blur (separable convolution)
// --------------------------------------------------------------------------

/**
 * Apply Gaussian blur to an RGBA image.
 * Uses separable 1D convolution for efficiency.
 *
 * @param {object} img - { data, width, height }
 * @param {number} sigma - blur radius in pixels (σ of Gaussian)
 * @returns {object} blurred { data, width, height }
 */
function applyGaussianBlur(img, sigma) {
  const { data, width, height } = img;
  const radius = Math.ceil(sigma * 3);
  const kSize = radius * 2 + 1;

  // Build 1D Gaussian kernel
  const kernel = new Float32Array(kSize);
  let sum = 0;
  for (let i = 0; i < kSize; i++) {
    const x = i - radius;
    kernel[i] = Math.exp(-(x * x) / (2 * sigma * sigma));
    sum += kernel[i];
  }
  for (let i = 0; i < kSize; i++) kernel[i] /= sum;

  const out = createRGBA(width, height);
  const temp = new Float32Array(width * height * 4);

  // Horizontal pass
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let k = 0; k < kSize; k++) {
        const sx = Math.min(width - 1, Math.max(0, x + k - radius));
        const idx = (y * width + sx) * 4;
        r += data[idx] * kernel[k];
        g += data[idx + 1] * kernel[k];
        b += data[idx + 2] * kernel[k];
        a += data[idx + 3] * kernel[k];
      }
      const oi = (y * width + x) * 4;
      temp[oi] = r; temp[oi + 1] = g; temp[oi + 2] = b; temp[oi + 3] = a;
    }
  }

  // Vertical pass
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let k = 0; k < kSize; k++) {
        const sy = Math.min(height - 1, Math.max(0, y + k - radius));
        const idx = (sy * width + x) * 4;
        r += temp[idx] * kernel[k];
        g += temp[idx + 1] * kernel[k];
        b += temp[idx + 2] * kernel[k];
        a += temp[idx + 3] * kernel[k];
      }
      const oi = (y * width + x) * 4;
      out.data[oi] = Math.round(Math.min(255, Math.max(0, r)));
      out.data[oi + 1] = Math.round(Math.min(255, Math.max(0, g)));
      out.data[oi + 2] = Math.round(Math.min(255, Math.max(0, b)));
      out.data[oi + 3] = Math.round(Math.min(255, Math.max(0, a)));
    }
  }

  return out;
}

// --------------------------------------------------------------------------
// JPEG compression simulation (8×8 DCT block quantization)
// --------------------------------------------------------------------------

/**
 * Simulate JPEG compression artifacts by applying 8×8 block DCT quantization.
 * This approximation captures the essential JPEG degradation: block artifacts,
 * ringing near edges, and color precision loss.
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} quality - JPEG quality (1-100, lower = more compression)
 * @returns {object} { data, width, height } degraded image
 */
function simulateJpegCompression(img, quality) {
  const { data, width, height } = img;
  const out = createRGBA(width, height);
  out.data.set(data);

  // Quality factor → quantization divisor (approximation of JPEG Q tables)
  // At quality=100, divisor=1 (no loss). At quality=1, divisor≈50.
  const qf = quality < 50 ? (5000 / quality) : (200 - 2 * quality);
  const divisor = Math.max(1, Math.round(qf / 100 * 8));

  // Process each 8×8 block per color channel
  for (let by = 0; by < height; by += 8) {
    for (let bx = 0; bx < width; bx += 8) {
      for (let ch = 0; ch < 3; ch++) {
        // Extract 8×8 block
        const block = new Float64Array(64);
        for (let r = 0; r < 8; r++) {
          for (let c = 0; c < 8; c++) {
            const y = by + r, x = bx + c;
            if (y < height && x < width) {
              block[r * 8 + c] = out.data[(y * width + x) * 4 + ch];
            }
          }
        }

        // Forward DCT (simplified — uses mean-subtraction quantization)
        // Full 2D DCT is expensive; approximate with block-mean + residual quantization
        let sum = 0;
        for (let i = 0; i < 64; i++) sum += block[i];
        const mean = sum / 64;

        // Quantize residuals
        for (let i = 0; i < 64; i++) {
          const residual = block[i] - mean;
          block[i] = mean + Math.round(residual / divisor) * divisor;
        }

        // Write back
        for (let r = 0; r < 8; r++) {
          for (let c = 0; c < 8; c++) {
            const y = by + r, x = bx + c;
            if (y < height && x < width) {
              out.data[(y * width + x) * 4 + ch] = Math.min(255, Math.max(0, Math.round(block[r * 8 + c])));
            }
          }
        }
      }
    }
  }

  return out;
}

// --------------------------------------------------------------------------
// Image downscale (area-averaging)
// --------------------------------------------------------------------------

/**
 * Downscale an image by an integer factor using area averaging.
 * Simulates low-resolution capture of a high-resolution artifact.
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} factor - integer downscale factor (2 = half size, 4 = quarter)
 * @returns {object} { data, width, height } downscaled image
 */
function downscaleImage(img, factor) {
  factor = Math.max(1, Math.round(factor));
  const newW = Math.floor(img.width / factor);
  const newH = Math.floor(img.height / factor);
  const out = createRGBA(newW, newH);
  const area = factor * factor;

  for (let ny = 0; ny < newH; ny++) {
    for (let nx = 0; nx < newW; nx++) {
      let r = 0, g = 0, b = 0;
      for (let dy = 0; dy < factor; dy++) {
        for (let dx = 0; dx < factor; dx++) {
          const sx = nx * factor + dx;
          const sy = ny * factor + dy;
          const idx = (sy * img.width + sx) * 4;
          r += img.data[idx];
          g += img.data[idx + 1];
          b += img.data[idx + 2];
        }
      }
      const oi = (ny * newW + nx) * 4;
      out.data[oi] = Math.round(r / area);
      out.data[oi + 1] = Math.round(g / area);
      out.data[oi + 2] = Math.round(b / area);
      out.data[oi + 3] = 255;
    }
  }
  return out;
}

// --------------------------------------------------------------------------
// Barrel/pincushion distortion simulation (Brown-Conrady model)
// --------------------------------------------------------------------------

/**
 * Apply radial barrel or pincushion distortion to an image.
 * Uses Brown-Conrady model: r_distorted = r * (1 + k1*r² + k2*r⁴)
 *
 * k1 > 0 → barrel distortion (edges bow outward — typical for wide-angle phone cameras)
 * k1 < 0 → pincushion distortion (edges bow inward — typical for telephoto)
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} k1 - primary radial distortion coefficient (typical range: -0.5 to 0.5)
 * @param {number} [k2=0] - secondary radial distortion coefficient
 * @returns {object} { data, width, height } distorted image
 */
function applyBarrelDistortion(img, k1, k2) {
  k2 = k2 || 0;
  const { data, width, height } = img;
  const out = createRGBA(width, height);

  // Center of distortion = image center
  const cx = width / 2, cy = height / 2;
  // Normalize radius so that max(r) at corners ≈ 1
  const maxR = Math.sqrt(cx * cx + cy * cy);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      // Normalized coords from center
      const dx = (x - cx) / maxR;
      const dy = (y - cy) / maxR;
      const r2 = dx * dx + dy * dy;
      const r4 = r2 * r2;

      // Undistort: find source position
      const scale = 1 + k1 * r2 + k2 * r4;
      const sx = cx + dx * scale * maxR;
      const sy = cy + dy * scale * maxR;

      if (sx < 0 || sy < 0 || sx >= width - 1 || sy >= height - 1) {
        const oi = (y * width + x) * 4;
        out.data[oi] = 200; out.data[oi + 1] = 200;
        out.data[oi + 2] = 200; out.data[oi + 3] = 255;
        continue;
      }

      // Bilinear interpolation
      const ix = Math.floor(sx), iy = Math.floor(sy);
      const fx = sx - ix, fy = sy - iy;
      const i00 = (iy * width + ix) * 4;
      const i10 = i00 + 4;
      const i01 = i00 + width * 4;
      const i11 = i01 + 4;

      const oi = (y * width + x) * 4;
      for (let ch = 0; ch < 3; ch++) {
        const v = (1 - fx) * (1 - fy) * data[i00 + ch]
                + fx * (1 - fy) * data[i10 + ch]
                + (1 - fx) * fy * data[i01 + ch]
                + fx * fy * data[i11 + ch];
        out.data[oi + ch] = Math.round(Math.min(255, Math.max(0, v)));
      }
      out.data[oi + 3] = 255;
    }
  }
  return out;
}

// --------------------------------------------------------------------------
// Lateral chromatic aberration simulation
// --------------------------------------------------------------------------

/**
 * Simulate lateral chromatic aberration (CA).
 * Each RGB channel gets a slightly different radial magnification.
 * Red shifts outward, blue shifts inward relative to green (typical for phone lenses).
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} caStrength - CA strength in pixels at image corners (typical: 0.5-5)
 * @returns {object} { data, width, height } image with CA applied
 */
function applyChromaticAberration(img, caStrength) {
  const { data, width, height } = img;
  const out = createRGBA(width, height);
  const cx = width / 2, cy = height / 2;
  const maxR = Math.sqrt(cx * cx + cy * cy);

  // Per-channel radial scale: green=1 (reference), red=1+δ, blue=1-δ
  // δ chosen so that at corners (r=maxR), the shift = caStrength pixels
  // shift = r * scale - r = r * δ → at r=maxR: shift = maxR * δ = caStrength → δ = caStrength/maxR
  const delta = caStrength / maxR;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const dx = x - cx, dy = y - cy;
      const oi = (y * width + x) * 4;

      // Sample each channel from a slightly different position
      // Lateral CA: constant magnification scale per channel (proportional to r automatically)
      for (let ch = 0; ch < 3; ch++) {
        let scale;
        if (ch === 0) scale = 1 + delta;           // Red: shifted outward
        else if (ch === 1) scale = 1;              // Green: reference
        else scale = 1 - delta;                    // Blue: shifted inward

        const sx = cx + dx * scale;
        const sy = cy + dy * scale;

        if (sx < 0 || sy < 0 || sx >= width - 1 || sy >= height - 1) {
          out.data[oi + ch] = data[oi + ch]; // fallback
          continue;
        }

        // Bilinear interpolation for sub-pixel sampling
        const ix = Math.floor(sx), iy = Math.floor(sy);
        const fx = sx - ix, fy = sy - iy;
        const i00 = (iy * width + ix) * 4 + ch;
        const i10 = i00 + 4;
        const i01 = i00 + width * 4;
        const i11 = i01 + 4;
        const v = (1 - fx) * (1 - fy) * data[i00]
                + fx * (1 - fy) * data[i10]
                + (1 - fx) * fy * data[i01]
                + fx * fy * data[i11];
        out.data[oi + ch] = Math.round(Math.min(255, Math.max(0, v)));
      }
      out.data[oi + 3] = 255;
    }
  }
  return out;
}

// --------------------------------------------------------------------------
// Vignetting simulation (radial brightness falloff)
// --------------------------------------------------------------------------

/**
 * Simulate lens vignetting — brightness falls off radially from center to corners.
 * Uses cos⁴ law approximation (natural vignetting model).
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} strength - vignetting strength (0 = none, 0.5 = moderate, 1.0 = heavy)
 * @returns {object} { data, width, height } vignetted image
 */
function applyVignetting(img, strength) {
  const { data, width, height } = img;
  const out = createRGBA(width, height);
  const cx = width / 2, cy = height / 2;
  const maxR = Math.sqrt(cx * cx + cy * cy);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const dx = (x - cx) / maxR;
      const dy = (y - cy) / maxR;
      const r2 = dx * dx + dy * dy;
      // cos⁴ model: brightness = (1 - strength * r²)²
      const falloff = Math.max(0, 1 - strength * r2);
      const scale = falloff * falloff;
      const idx = (y * width + x) * 4;
      out.data[idx] = Math.round(Math.min(255, Math.max(0, data[idx] * scale)));
      out.data[idx + 1] = Math.round(Math.min(255, Math.max(0, data[idx + 1] * scale)));
      out.data[idx + 2] = Math.round(Math.min(255, Math.max(0, data[idx + 2] * scale)));
      out.data[idx + 3] = data[idx + 3];
    }
  }
  return out;
}

/**
 * Get the data capacity for a config.
 * @param {string} configName - e.g. "128x128-4c"
 * @param {object} [opts] - { nsym: 32 }
 * @returns {{ dataBytes, rawBytes, dataModules, usablePayloadBytes }} capacity info
 */
function getCapacity(configName, opts = {}) {
  const config = format.HD_CONFIGS[configName];
  if (!config) {
    const validNames = Object.keys(format.HD_CONFIGS).join(", ");
    throw new Error(`Unknown config: ${configName}. Valid configs: ${validNames}`);
  }
  const nsym = opts.nsym || 32;
  const cap = format.hdCalcCapacity(config, { nsym });
  // Header overhead: 48 bytes + filename
  const headerOverhead = 48; // minimum (0-byte filename)
  return {
    ...cap,
    usablePayloadBytes: cap.dataBytes - headerOverhead,
    headerOverhead,
  };
}

/**
 * Check capacity utilization and generate warnings for a given payload + config.
 * Call before encoding to verify payload fits, or after encoding to analyze headroom.
 *
 * @param {string|Uint8Array} payload - payload to check
 * @param {string} filename - filename string
 * @param {object} [opts] - { configName, nsym, compFlag }
 * @returns {{ fits: boolean, utilization: number, remainingBytes: number, warnings: string[], details: object }}
 */
function checkCapacityWarnings(payload, filename, opts = {}) {
  const configName = opts.configName || "128x128-4c";
  const nsym = opts.nsym || 32;
  const cap = getCapacity(configName, { nsym });

  const payloadBytes = typeof payload === "string"
    ? new TextEncoder().encode(payload)
    : payload;
  const filenameBytes = new TextEncoder().encode(filename || "");
  const headerOverhead = 48 + filenameBytes.length;
  const totalNeeded = headerOverhead + payloadBytes.length;

  const utilization = cap.dataBytes > 0 ? totalNeeded / cap.dataBytes : 1;
  const remainingBytes = cap.dataBytes - totalNeeded;
  const fits = remainingBytes >= 0;

  const warnings = [];
  const details = {
    payloadSize: payloadBytes.length,
    headerSize: headerOverhead,
    totalNeeded,
    dataCapacity: cap.dataBytes,
    usablePayload: cap.usablePayloadBytes,
    utilization: Math.round(utilization * 10000) / 100,
    remainingBytes,
    configName,
    nsym,
  };

  if (!fits) {
    warnings.push(`OVERFLOW: payload needs ${totalNeeded} bytes but config ${configName} only has ${cap.dataBytes} (${-remainingBytes} bytes over)`);
  } else if (utilization > 0.95) {
    warnings.push(`CRITICAL: ${details.utilization}% capacity used — only ${remainingBytes} bytes remaining`);
  } else if (utilization > 0.80) {
    warnings.push(`WARNING: ${details.utilization}% capacity used — ${remainingBytes} bytes remaining`);
  }

  if (nsym < 32) {
    warnings.push(`LOW_REDUNDANCY: nsym=${nsym} provides minimal error correction`);
  }

  // Suggest upgrade if utilization > 70%
  if (utilization > 0.70 && fits) {
    const configs = Object.keys(format.HD_CONFIGS);
    const currentIdx = configs.indexOf(configName);
    if (currentIdx >= 0) {
      // Find next larger config with same color count
      const currentColors = format.HD_CONFIGS[configName].bpm;
      for (let i = currentIdx + 1; i < configs.length; i++) {
        if (format.HD_CONFIGS[configs[i]].bpm === currentColors) {
          const nextCap = getCapacity(configs[i], { nsym });
          const nextUtil = totalNeeded / nextCap.dataBytes;
          if (nextUtil < 0.70) {
            details.suggestedUpgrade = configs[i];
            details.upgradeUtilization = Math.round(nextUtil * 10000) / 100;
            break;
          }
        }
      }
    }
  }

  return { fits, utilization: details.utilization, remainingBytes, warnings, details };
}

/**
 * Place an image on a larger canvas with background padding.
 * Simulates real-world captures where the artifact doesn't fill the frame.
 *
 * @param {object} img - { data, width, height } RGBA source image
 * @param {number} padTop - pixels of padding above
 * @param {number} padRight - pixels of padding to the right
 * @param {number} padBottom - pixels of padding below
 * @param {number} padLeft - pixels of padding to the left
 * @param {number[]} [bgColor] - [r,g,b] background color (default: [200, 200, 200])
 * @returns {object} { data, width, height } padded RGBA image
 */
function padImage(img, padTop, padRight, padBottom, padLeft, bgColor) {
  bgColor = bgColor || [200, 200, 200];
  const newW = img.width + padLeft + padRight;
  const newH = img.height + padTop + padBottom;
  const out = createRGBA(newW, newH);
  // Fill background
  for (let i = 0; i < out.data.length; i += 4) {
    out.data[i] = bgColor[0];
    out.data[i + 1] = bgColor[1];
    out.data[i + 2] = bgColor[2];
    out.data[i + 3] = 255;
  }
  // Copy source image
  for (let y = 0; y < img.height; y++) {
    for (let x = 0; x < img.width; x++) {
      const si = (y * img.width + x) * 4;
      const di = ((y + padTop) * newW + (x + padLeft)) * 4;
      out.data[di] = img.data[si];
      out.data[di + 1] = img.data[si + 1];
      out.data[di + 2] = img.data[si + 2];
      out.data[di + 3] = img.data[si + 3];
    }
  }
  return out;
}

/**
 * Apply directional motion blur to simulate camera shake.
 * Uses a 1D box kernel along the specified angle.
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} length - blur kernel length in pixels (3-50 typical)
 * @param {number} [angleDeg=0] - blur direction in degrees (0=horizontal, 90=vertical)
 * @returns {object} { data, width, height } blurred RGBA image
 */
function applyMotionBlur(img, length, angleDeg) {
  angleDeg = angleDeg || 0;
  const rad = angleDeg * Math.PI / 180;
  const dx = Math.cos(rad);
  const dy = Math.sin(rad);
  const halfLen = Math.floor(length / 2);
  const { width, height } = img;
  const out = createRGBA(width, height);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0, count = 0;
      for (let k = -halfLen; k <= halfLen; k++) {
        const sx = Math.round(x + k * dx);
        const sy = Math.round(y + k * dy);
        if (sx >= 0 && sx < width && sy >= 0 && sy < height) {
          const si = (sy * width + sx) * 4;
          r += img.data[si];
          g += img.data[si + 1];
          b += img.data[si + 2];
          count++;
        }
      }
      const di = (y * width + x) * 4;
      out.data[di] = Math.round(r / count);
      out.data[di + 1] = Math.round(g / count);
      out.data[di + 2] = Math.round(b / count);
      out.data[di + 3] = 255;
    }
  }
  return out;
}

/**
 * Apply a shadow/occlusion band across the image.
 * Simulates a finger, shadow, or object partially covering the artifact.
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {string} [type="horizontal"] - "horizontal", "vertical", or "diagonal"
 * @param {number} [position=0.5] - relative position (0-1) of the band center
 * @param {number} [widthFrac=0.1] - band width as fraction of image dimension
 * @param {number} [darkness=0.15] - how dark the shadow is (0=black, 1=transparent)
 * @returns {object} { data, width, height } image with shadow
 */
function applyShadowOcclusion(img, type, position, widthFrac, darkness) {
  type = type || "horizontal";
  position = position !== undefined ? position : 0.5;
  widthFrac = widthFrac !== undefined ? widthFrac : 0.1;
  darkness = darkness !== undefined ? darkness : 0.15;

  const { width, height } = img;
  const out = createRGBA(width, height);
  out.data.set(img.data);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let t; // normalized distance from band center (0=center, 1=edge)
      if (type === "horizontal") {
        const cy = position * height;
        const halfW = (widthFrac * height) / 2;
        const dist = Math.abs(y - cy);
        t = dist < halfW ? dist / halfW : 1;
      } else if (type === "vertical") {
        const cx = position * width;
        const halfW = (widthFrac * width) / 2;
        const dist = Math.abs(x - cx);
        t = dist < halfW ? dist / halfW : 1;
      } else { // diagonal
        const nx = x / width, ny = y / height;
        const dist = Math.abs(nx + ny - 2 * position) / Math.SQRT2;
        const halfW = widthFrac / 2;
        t = dist < halfW ? dist / halfW : 1;
      }

      if (t < 1) {
        // Smooth shadow: cosine falloff from center
        const shadowStr = (1 - darkness) * (0.5 + 0.5 * Math.cos(Math.PI * t));
        const mult = 1 - shadowStr;
        const idx = (y * width + x) * 4;
        out.data[idx] = Math.round(out.data[idx] * mult);
        out.data[idx + 1] = Math.round(out.data[idx + 1] * mult);
        out.data[idx + 2] = Math.round(out.data[idx + 2] * mult);
      }
    }
  }
  return out;
}

/**
 * Apply color temperature shift to simulate warm/cool lighting.
 * Warm shifts boost red/yellow, reduce blue. Cool does the opposite.
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} temperature - shift amount (-1 to 1, negative=cool/blue, positive=warm/yellow)
 * @returns {object} { data, width, height } color-shifted image
 */
function applyColorTemperatureShift(img, temperature) {
  const out = createRGBA(img.width, img.height);
  // Red/blue channel multipliers based on temperature
  const rMult = 1 + temperature * 0.25;   // warm → more red
  const gMult = 1 + temperature * 0.05;   // green barely affected
  const bMult = 1 - temperature * 0.25;   // warm → less blue

  for (let i = 0; i < img.data.length; i += 4) {
    out.data[i] = Math.min(255, Math.max(0, Math.round(img.data[i] * rMult)));
    out.data[i + 1] = Math.min(255, Math.max(0, Math.round(img.data[i + 1] * gMult)));
    out.data[i + 2] = Math.min(255, Math.max(0, Math.round(img.data[i + 2] * bMult)));
    out.data[i + 3] = img.data[i + 3];
  }
  return out;
}

/**
 * Apply aspect ratio distortion by scaling width or height.
 * Simulates non-square pixel display or camera capture mismatch.
 *
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} scaleX - horizontal scale factor (1.0=no change, 1.1=10% wider)
 * @param {number} scaleY - vertical scale factor (1.0=no change, 0.9=10% shorter)
 * @returns {object} { data, width, height } distorted RGBA image
 */
function applyAspectDistortion(img, scaleX, scaleY) {
  const newW = Math.round(img.width * scaleX);
  const newH = Math.round(img.height * scaleY);
  const out = createRGBA(newW, newH);

  for (let y = 0; y < newH; y++) {
    const sy = y / scaleY;
    const sy0 = Math.floor(sy);
    const sy1 = Math.min(img.height - 1, sy0 + 1);
    const fy = sy - sy0;
    for (let x = 0; x < newW; x++) {
      const sx = x / scaleX;
      const sx0 = Math.floor(sx);
      const sx1 = Math.min(img.width - 1, sx0 + 1);
      const fx = sx - sx0;

      // Bilinear interpolation
      const i00 = (sy0 * img.width + sx0) * 4;
      const i10 = (sy0 * img.width + sx1) * 4;
      const i01 = (sy1 * img.width + sx0) * 4;
      const i11 = (sy1 * img.width + sx1) * 4;
      const di = (y * newW + x) * 4;

      for (let c = 0; c < 3; c++) {
        const top = img.data[i00 + c] * (1 - fx) + img.data[i10 + c] * fx;
        const bot = img.data[i01 + c] * (1 - fx) + img.data[i11 + c] * fx;
        out.data[di + c] = Math.round(top * (1 - fy) + bot * fy);
      }
      out.data[di + 3] = 255;
    }
  }
  return out;
}

/**
 * Adjust image saturation. <1 desaturates toward grayscale, >1 over-saturates.
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} factor - saturation multiplier (0=grayscale, 1=unchanged, 2=double)
 * @returns {object} { data, width, height }
 */
function applySaturationShift(img, factor) {
  const out = createRGBA(img.width, img.height);
  for (let i = 0; i < img.data.length; i += 4) {
    const r = img.data[i], g = img.data[i + 1], b = img.data[i + 2];
    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
    out.data[i]     = Math.min(255, Math.max(0, Math.round(lum + (r - lum) * factor)));
    out.data[i + 1] = Math.min(255, Math.max(0, Math.round(lum + (g - lum) * factor)));
    out.data[i + 2] = Math.min(255, Math.max(0, Math.round(lum + (b - lum) * factor)));
    out.data[i + 3] = img.data[i + 3];
  }
  return out;
}

/**
 * Adjust image contrast. <1 reduces contrast, >1 increases.
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} factor - contrast multiplier (0.5=low, 1=unchanged, 2=high)
 * @returns {object} { data, width, height }
 */
function applyContrastShift(img, factor) {
  const out = createRGBA(img.width, img.height);
  for (let i = 0; i < img.data.length; i += 4) {
    out.data[i]     = Math.min(255, Math.max(0, Math.round(128 + (img.data[i] - 128) * factor)));
    out.data[i + 1] = Math.min(255, Math.max(0, Math.round(128 + (img.data[i + 1] - 128) * factor)));
    out.data[i + 2] = Math.min(255, Math.max(0, Math.round(128 + (img.data[i + 2] - 128) * factor)));
    out.data[i + 3] = img.data[i + 3];
  }
  return out;
}

/**
 * Apply gamma correction to simulate over/underexposure.
 * gamma < 1 brightens (overexposure), gamma > 1 darkens (underexposure).
 * @param {object} img - { data, width, height } RGBA image
 * @param {number} gamma - gamma value (0.5=bright, 1=unchanged, 2=dark)
 * @returns {object} { data, width, height }
 */
function applyGammaShift(img, gamma) {
  // Build LUT for speed
  const lut = new Uint8Array(256);
  for (let i = 0; i < 256; i++) {
    lut[i] = Math.min(255, Math.max(0, Math.round(255 * Math.pow(i / 255, gamma))));
  }
  const out = createRGBA(img.width, img.height);
  for (let i = 0; i < img.data.length; i += 4) {
    out.data[i]     = lut[img.data[i]];
    out.data[i + 1] = lut[img.data[i + 1]];
    out.data[i + 2] = lut[img.data[i + 2]];
    out.data[i + 3] = img.data[i + 3];
  }
  return out;
}

/**
 * Batch-encode multiple payloads in a single call.
 * Shares config lookup overhead and returns array of results.
 *
 * @param {Array<{payload: string|Uint8Array, filename: string, opts?: object}>} items
 * @param {object} [sharedOpts] — default opts applied to all items (per-item opts override)
 * @returns {Array<{ok: boolean, result?: object, error?: string, index: number}>}
 */
function encodeBatch(items, sharedOpts = {}) {
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error("items must be a non-empty array of {payload, filename}");
  }
  const results = [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (!item || item.payload === undefined || item.payload === null || !item.filename) {
      results.push({ ok: false, error: "missing payload or filename", index: i });
      continue;
    }
    const mergedOpts = Object.assign({}, sharedOpts, item.opts || {});
    try {
      const r = encodeAndRender(item.payload, item.filename, mergedOpts);
      results.push({ ok: true, result: r, index: i });
    } catch (e) {
      results.push({ ok: false, error: e.message, index: i });
    }
  }
  return results;
}

// =========================================================================
// NBR #79: Payload chunking API — split oversized payloads across multiple
// artifacts with sequence metadata for reassembly.
// =========================================================================

function chunkPayload(payload, opts = {}) {
  const configName = opts.configName || "128x128-4c";
  const nsym = opts.nsym || 32;
  const filename = opts.filename || "chunk";
  const cap = getCapacity(configName, { nsym });

  const payloadBytes = typeof payload === "string"
    ? new TextEncoder().encode(payload)
    : payload;

  // Reserve space for chunk header: 16 bytes (chunkIndex u16, totalChunks u16, seqId u32, payloadLen u32, reserved u32)
  const chunkHeaderSize = 16;
  const maxChunkData = cap.usablePayloadBytes - chunkHeaderSize - filename.length - 10;

  if (maxChunkData <= 0) {
    throw new Error(`Config ${configName} too small for chunked encoding — no room after header`);
  }

  if (payloadBytes.length <= cap.usablePayloadBytes) {
    // Fits in a single artifact — no chunking needed
    return {
      chunked: false,
      totalChunks: 1,
      chunks: [{ index: 0, data: payloadBytes, filename }],
      seqId: 0,
      configName,
    };
  }

  const totalChunks = Math.ceil(payloadBytes.length / maxChunkData);
  const seqId = (Date.now() & 0xFFFFFFFF) >>> 0; // simple sequence ID
  const chunks = [];

  for (let i = 0; i < totalChunks; i++) {
    const start = i * maxChunkData;
    const end = Math.min(start + maxChunkData, payloadBytes.length);
    const chunkData = payloadBytes.slice(start, end);

    // Build chunk header
    const header = new Uint8Array(chunkHeaderSize);
    const dv = new DataView(header.buffer);
    dv.setUint16(0, i, true);           // chunkIndex
    dv.setUint16(2, totalChunks, true);  // totalChunks
    dv.setUint32(4, seqId, true);        // seqId
    dv.setUint32(8, payloadBytes.length, true); // total payload length
    dv.setUint32(12, chunkData.length, true);   // this chunk's data length

    // Combine header + data
    const combined = new Uint8Array(chunkHeaderSize + chunkData.length);
    combined.set(header, 0);
    combined.set(chunkData, chunkHeaderSize);

    chunks.push({
      index: i,
      data: combined,
      filename: `${filename}.chunk${i}of${totalChunks}`,
      header: { chunkIndex: i, totalChunks, seqId, totalLength: payloadBytes.length, chunkLength: chunkData.length },
    });
  }

  return {
    chunked: true,
    totalChunks,
    chunks,
    seqId,
    configName,
    maxChunkData,
    totalPayloadSize: payloadBytes.length,
  };
}

function reassembleChunks(chunkPayloads) {
  if (!chunkPayloads || chunkPayloads.length === 0) {
    throw new Error("No chunks to reassemble");
  }

  const chunkHeaderSize = 16;
  const parsed = chunkPayloads.map(cp => {
    const raw = cp instanceof Uint8Array ? cp : new Uint8Array(cp);
    if (raw.length < chunkHeaderSize) throw new Error("Chunk too small for header");
    const dv = new DataView(raw.buffer, raw.byteOffset, chunkHeaderSize);
    return {
      chunkIndex: dv.getUint16(0, true),
      totalChunks: dv.getUint16(2, true),
      seqId: dv.getUint32(4, true),
      totalLength: dv.getUint32(8, true),
      chunkLength: dv.getUint32(12, true),
      data: raw.slice(chunkHeaderSize),
    };
  });

  // Sort by chunk index
  parsed.sort((a, b) => a.chunkIndex - b.chunkIndex);

  const totalLength = parsed[0].totalLength;
  const totalChunks = parsed[0].totalChunks;

  if (parsed.length !== totalChunks) {
    throw new Error(`Missing chunks: got ${parsed.length} of ${totalChunks}`);
  }

  // Verify all same seqId
  const seqId = parsed[0].seqId;
  for (const p of parsed) {
    if (p.seqId !== seqId) throw new Error(`Mismatched seqId: ${p.seqId} vs ${seqId}`);
  }

  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const p of parsed) {
    result.set(p.data, offset);
    offset += p.data.length;
  }

  return { payload: result, seqId, totalChunks, totalLength };
}

module.exports = {
  FINDER_BITMAP, ORIENT_BITMAP,
  createRGBA, fillRect,
  drawFinderAt, drawOrientAt, drawSymbolFrame,
  renderArtifact,
  encodeAndRender,
  encodeBatch,
  getCapacity,
  checkCapacityWarnings,
  chunkPayload,
  reassembleChunks,
  perspectiveWarp,
  addGaussianNoise,
  applyGaussianBlur,
  applyBrightnessGradient,
  simulateJpegCompression,
  downscaleImage,
  applyBarrelDistortion,
  applyChromaticAberration,
  applyVignetting,
  padImage,
  applyMotionBlur,
  applyShadowOcclusion,
  applyAspectDistortion,
  applyColorTemperatureShift,
  applySaturationShift,
  applyContrastShift,
  applyGammaShift,
  toPPM,
};
