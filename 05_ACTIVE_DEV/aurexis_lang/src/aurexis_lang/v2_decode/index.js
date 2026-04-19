/**
 * Aurexis Core V2 — Decode Engine
 *
 * Standalone, DOM-free decode module extracted from the E/D client.
 * Testable in Node. No browser APIs required for core decode path.
 *
 * Stages:
 *   1. Finder detection (finder.js)
 *   2. Format selection (format.js)
 *   3. Homography computation (homography.js)
 *   4. Module sampling + color classification (sampler.js)
 *   5. RS decode (gf_rs.js)
 *   6. Payload parsing (codec.js)
 *
 * © 2026 Vincent Anderson — Aurexis Core. All rights reserved.
 */
"use strict";

const gfRs = require("./gf_rs");
const homography = require("./homography");
const format = require("./format");
const finder = require("./finder");
const sampler = require("./sampler");
const codec = require("./codec");

// --------------------------------------------------------------------------
// Full single-frame decode pipeline
// --------------------------------------------------------------------------

/**
 * Decode an HD artifact from a single RGBA image frame.
 *
 * @param {Uint8Array|Uint8ClampedArray} imgData - RGBA pixel data
 * @param {number} W - image width
 * @param {number} H - image height
 * @param {object} [opts] - options
 * @param {object} [opts.bounds] - search bounds { x0, y0, x1, y1 }
 * @param {string} [opts.configName] - force a specific HD config name
 * @param {function} [opts.inflate] - inflate function for decompression
 * @returns {object|null} { filename, payload, sha256, config, rsStats } or null
 */
function decodeFrame(imgData, W, H, opts = {}) {
  // Stage 1: Find finder patterns
  const fids = finder.detectFinders(imgData, W, H, opts.bounds);
  if (!fids) return null;

  // Stage 2: Determine format
  let config, configName;
  if (opts.configName && format.HD_CONFIGS[opts.configName]) {
    config = format.HD_CONFIGS[opts.configName];
    configName = opts.configName;
  } else {
    const fmt = format.estimateFormat(fids, imgData, W, H);
    if (!fmt) return null;
    config = fmt.config;
    configName = fmt.name;
  }

  // Stage 3: Compute homography
  const layout = format.computeSymbolLayout(config.grid, config.canvasPx);
  const canonPts = format.computeCanonicalFinderPoints(layout);
  const sourcePts = [fids.TL, fids.TR, fids.BL, fids.BR];
  const Hmat = homography.computeHomography(canonPts, sourcePts);
  if (!Hmat) return null;

  // Stage 4: Sample modules
  const gs = config.grid;
  const totalModules = gs * gs;
  const palette = sampler.hdGetPalette(config.colors);

  // Compute sampling radius from module scale
  const u0 = homography.applyHomography(Hmat, { x: 0, y: 0 });
  const u1 = homography.applyHomography(Hmat, { x: layout.modPx, y: 0 });
  const moduleScalePx = Math.hypot(u1.x - u0.x, u1.y - u0.y);
  // Conservative radius: stay well inside module interior to avoid boundary
  // bleeding from bilinear interpolation in warped images.
  // moduleScalePx / 6 keeps the sampling area within ~33% of center.
  // Allow radius=0 (single center pixel) for small modules.
  const radius = Math.max(0, Math.floor(moduleScalePx / 6));

  const modules = new Uint8Array(totalModules);
  for (let r = 0; r < gs; r++) {
    for (let c = 0; c < gs; c++) {
      const idx = r * gs + c;
      const cxc = layout.dataOriginPx + c * layout.modPx + (layout.modPx / 2);
      const cyc = layout.dataOriginPx + r * layout.modPx + (layout.modPx / 2);
      const sp = homography.applyHomography(Hmat, { x: cxc, y: cyc });
      const rgb = sampler.sampleAvg(imgData, W, H, sp.x, sp.y, radius);

      if (config.colors <= 4) {
        modules[idx] = sampler.classifyModuleHsv(rgb, palette);
      } else {
        modules[idx] = sampler.classifyModuleRgb(rgb, palette);
      }
    }
  }

  // Stage 5: RS decode
  const cap = format.hdCalcCapacity(config);
  const frame = sampler.hdPackModules(modules, config.bpm);
  const rsResult = gfRs.hdRsDecode(frame, cap.rawBytes);

  if (rsResult.data === null) {
    return {
      decoded: false,
      config: configName,
      fids,
      rsStats: {
        numBlocks: rsResult.numBlocks,
        failedBlocks: rsResult.failedBlocks,
        totalCorrected: rsResult.totalCorrected,
        blockResults: rsResult.blockResults,
      },
    };
  }

  // Stage 6: Parse header
  const header = codec.parseHdHeader(rsResult.data);
  if (!header) {
    return {
      decoded: false,
      config: configName,
      fids,
      rsStats: {
        numBlocks: rsResult.numBlocks,
        failedBlocks: 0,
        totalCorrected: rsResult.totalCorrected,
      },
      error: "AHDX header parse failed",
    };
  }

  // Decompress
  let payload;
  try {
    payload = codec.decompressPayload(header.payloadData, header.compFlag, { inflate: opts.inflate });
  } catch (e) {
    return {
      decoded: false,
      config: configName,
      fids,
      error: "decompression failed: " + e.message,
    };
  }

  return {
    decoded: true,
    filename: header.filename,
    payload,
    sha256: header.sha256,
    config: configName,
    fids,
    rsStats: {
      numBlocks: rsResult.numBlocks,
      failedBlocks: 0,
      totalCorrected: rsResult.totalCorrected,
    },
  };
}

module.exports = {
  // Full pipeline
  decodeFrame,

  // Individual stages (for testing and advanced use)
  gfRs,
  homography,
  format,
  finder,
  sampler,
  codec,
};
