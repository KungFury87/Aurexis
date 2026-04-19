# Aurexis Core — Deep Cross-Domain Research Reference

**Date:** 2026-04-18
**Scope:** Neglected, cross-domain, and historically underexploited ideas that could materially benefit Aurexis Core as a deterministic visual computing engine.
**Method:** Systematic search across coding theory, metrology, invariants, structured light, algebraic topology, HDC/VSA, old corporate R&D, screen-camera communication, and pre-deep-learning vision. Filtered through Aurexis-relevance criteria. Real sources only.

---

## 1. Executive Thesis

The strongest neglected knowledge for Aurexis falls into three clusters:

**Cluster A — Channel coding from telecom.** Aurexis's screen/print-to-camera pipeline IS a communication channel. The coding theory, interleaving, equalization, and soft-decision decoding techniques from telecommunications directly apply but are almost never used in barcode/visual-code systems. The single highest-impact change is pseudo-random spatial interleaving to break spatially correlated errors. The second is Chase-type soft-decision RS decoding using color classification confidence.

**Cluster B — Deterministic calibration from metrology and fiducial systems.** AprilTag, STag, and ChromaTag have solved many of Aurexis's detection problems (adaptive thresholding, quad detection, subpixel localization, color pre-filtering). The industrial metrology literature (Steger, Forstner) provides subpixel techniques that would directly improve finder localization and homography quality. Projective invariants (cross-ratios) from classical geometry provide validation and refinement constraints that are being left on the table.

**Cluster C — Spatial consistency from sheaf theory and grid MRFs.** The multi-frame fusion problem maps exactly to cellular sheaf theory (Robinson 2017, Hansen & Ghrist 2019). The sheaf Laplacian provides a principled, fast, and structurally aware denoising framework. Belief propagation on the artifact grid MRF unifies spatial consistency, structural constraints, and RS parity into one inference framework. HDC/VSA provides a fast approximation for evidence accumulation.

---

## 2. Aurexis Context Synthesis

**Current architecture:** 7 standalone JS modules — finder detection (1:1:3:1:1 ratio scan, clustering, triangle selection), format estimation (try-all-configs timing), homography (4-point DLT), module sampling (area average, nearest-color classification), RS codec (GF(2^8), 255-byte blocks, 32 parity, multi-block interleaved), AHDX header codec, and synthetic renderer.

**Current strengths:** Full encode-render-warp-decode roundtrip proven (74/74 tests green). Clean image: 0 RS corrections. Mild warp: 0 RS corrections. Explicit BR orient detection working at score 1.00. Auto-format detection working.

**Current limits:**
- Hard warp (aggressive perspective) causes 13/16 RS block failures
- Global Otsu thresholding — fails under uneven lighting
- Naive RGB nearest-color classification — no perceptual color space, no camera calibration
- No spatial interleaving — spatially correlated errors overwhelm individual RS blocks
- Hard-decision RS decoding — discards classification confidence information
- 4-point homography from finder centers only — no refinement from timing/alignment points
- No in-situ color calibration from reference patches

**Likely near-term seams where external ideas help most:**
1. Spatial interleaving (breaks error correlation — biggest bang for buck)
2. Soft-decision RS decoding (uses confidence info already available)
3. Adaptive thresholding (handles real lighting)
4. CIELab color classification with reference-patch calibration (handles real cameras)
5. Subpixel finder localization + homography refinement (improves geometric precision)

---

## 3. Ranked Opportunity Map

### PRESENT-SCOPE (usable now on commodity hardware)

| # | Technique | Source Domain | Impact | Effort |
|---|-----------|--------------|--------|--------|
| 1 | QPP pseudo-random spatial interleaver | Telecom (3GPP turbo codes) | Very High | Low |
| 2 | Chase-II soft-decision RS decoding | Channel coding (Chase 1972) | High | Low-Medium |
| 3 | CIELab nearest-color classification | Color science | High | Low |
| 4 | Sauvola adaptive thresholding (Shafait integral-image) | Document imaging | High | Low |
| 5 | Reference-patch Von Kries color calibration | Color science + SCC | High | Low-Medium |
| 6 | Chromaticity-plane classification | COBRA (SCC research) | High | Low |
| 7 | Normalized DLT for homography | Photogrammetry (Hartley 1997) | Medium-High | Trivial |
| 8 | Subpixel finder center (Forstner / saddle-point) | Industrial metrology | Medium-High | Low |
| 9 | LSD line segment detection for timing strips | Image processing (von Gioi 2010) | Medium | Low |
| 10 | Cross-ratio validation of timing transitions | Projective geometry | Medium | Low |
| 11 | Contour-hierarchy finder detection (TopoTag concept) | Fiducial systems (Yu 2020) | Medium | Medium |
| 12 | Homography refinement via LM on all correspondences | Photogrammetry (Hartley & Zisserman) | Medium | Medium |
| 13 | Registered multi-frame pixel averaging | SCC / temporal codes | Medium | Low |
| 14 | Morphological opening/closing after binarization | Mathematical morphology | Low-Medium | Low |
| 15 | Flusser-Suk affine moment invariants for finder validation | Pattern recognition (1993) | Low-Medium | Low |

### MID-SCOPE (moderate engineering/research effort)

| # | Technique | Source Domain | Impact | Effort |
|---|-----------|--------------|--------|--------|
| 16 | HDC/VSA cleanup memory for module fusion | Hyperdimensional computing (Kanerva) | High | Medium |
| 17 | Cellular sheaf diffusion on artifact grid | Algebraic topology (Hansen & Ghrist) | High | Medium |
| 18 | Sheaf consistency radius for frame quality | Sensor fusion (Robinson 2017) | Medium-High | Medium |
| 19 | De Bruijn position encoding in timing | Structured light | Medium-High | Medium |
| 20 | Loopy BP on grid MRF (unifies spatial + ECC) | Graphical models | High | Medium-High |
| 21 | Color palette optimization for camera-space separation | Telecom constellation design + Bagherinia 2011 | Medium | Medium |
| 22 | RaptorQ outer code for erasure recovery | Fountain codes (RFC 6330) | High | Medium |
| 23 | Differential color encoding | Xerox PARC DataGlyphs | Medium | Medium |
| 24 | Guruswami-Sudan list decoding | Algebraic coding theory (1999) | Medium | High |

### FUTURE-SCOPE (valuable but blocked by complexity/format change)

| # | Technique | Source Domain | Notes |
|---|-----------|--------------|-------|
| 25 | LDPC replacement for RS | Channel coding | Better soft-decision native; requires format change |
| 26 | Koetter-Vardy algebraic soft-decision | Coding theory (2003) | Optimal but extreme implementation complexity |
| 27 | Trellis-coded modulation for color sequences | Telecom (Ungerboeck 1982) | Coding gain without rate loss; complex decoding |
| 28 | Temporal multi-frame encoding | SCC (HiLight, LightAnchors) | Requires cooperative display |
| 29 | Luminance/chrominance layered coding | SCC (Hao et al.) | Graceful degradation; format change |
| 30 | Circular/elliptical finder patterns | Fiducial systems (STag) | Better localization; fundamental redesign |

---

## 4. Candidate Veins (28 detailed)

### Vein 1: Pseudo-Random Spatial Interleaving (QPP)

**Source domain:** 3GPP turbo codes, digital broadcasting
**Why overlooked:** Barcode libraries universally use simple block interleaving or none at all. The telecom interleaving literature is in a different community.
**Aurexis problem it solves:** Spatially correlated classification errors (from perspective warp, blur, shadow, glare) concentrate in specific RS blocks, exceeding per-block correction capacity even when the total error count is low.
**Translation:** Define a quadratic permutation polynomial (QPP) π(i) = (a₁·i + a₂·i²) mod M mapping encoded byte positions to spatial grid positions. Adjacent spatial positions map to widely separated RS blocks. A localized 10×10 module error patch spreads across all 16 RS blocks with at most 1-2 errors each.
**Implementation:** One permutation table, applied at encode (after RS) and inverted at decode (before RS). ~20 lines of code.
**Evidence quality:** Proven in production systems (3GPP LTE, DVB-T2). Mathematical analysis well-established.
**Risk of dead-end:** Near zero. This is established engineering.
**Best sources:**
- Sun & Takeshita, "Interleavers for turbo codes using permutation polynomials," IEEE Trans. IT, 2005
- Lin & Costello, *Error Control Coding*, 2nd ed., Prentice Hall, 2004, Ch. 14
- Data Matrix (ISO/IEC 16022) diagonal interleaving as simpler alternative

### Vein 2: Chase-II Soft-Decision RS Decoding

**Source domain:** Channel coding (Chase 1972)
**Why overlooked:** Every barcode library uses hard-decision decoding. Soft-decision for visual codes is mentioned in exactly one paper (Xu & Hislop 2017, QR soft-input).
**Aurexis problem:** RS wastes correction capacity on uncertain modules that happened to classify correctly, while spending nothing on high-confidence modules.
**Translation:** When classifying each module, record the confidence margin (distance-to-nearest / distance-to-second-nearest). For RS decoding, rank all symbols by reliability. For the K least reliable (K=3-5), generate 2^K candidate codewords by flipping to second-best classification. Run standard RS decode on each. Keep the one that succeeds with fewest corrections.
**Implementation:** K=4 gives 16 candidates per RS block. With 16 blocks, that's 256 RS decode attempts — fast given RS is O(n²).
**Evidence quality:** Chase 1972 is a foundational paper with 4000+ citations. Xu & Hislop 2017 validated it specifically for barcode decoding.
**Risk of dead-end:** Near zero.
**Best sources:**
- Chase, "A class of algorithms for decoding block codes with channel measurement information," IEEE Trans. IT, 1972
- Xu & Hislop, "Soft-input decoding of QR barcodes," Electronics Letters, 2017

### Vein 3: CIELab Color Classification

**Source domain:** Color science, perceptual color spaces
**Why overlooked:** Most barcode libraries are monochrome. Colored barcode research (JAB Code, HCCB) uses Lab but the technique hasn't propagated to general implementations.
**Aurexis problem:** RGB Euclidean distance doesn't correlate with perceptual color difference. Camera white balance shifts RGB unpredictably. Blue channel has more noise due to Bayer pattern.
**Translation:** Convert sampled RGB to CIELab (via sRGB linearization → XYZ → Lab). Classify by nearest Lab Euclidean distance. Delta E of 1.0 ≈ just-noticeable difference, so classification thresholds are perceptually meaningful.
**Implementation:** ~20 floating-point operations per pixel for the conversion. Lookup table possible for speed.
**Evidence quality:** CIELab is an international standard (CIELAB 1976). Well-proven in color science.
**Best sources:**
- CIE Publication 15:2004 (Colorimetry)
- Sharma, Wu & Dalal, "The CIEDE2000 Color-Difference Formula," Color Research & Application, 2005

### Vein 4: Reference-Patch Color Calibration

**Source domain:** Screen-camera communication (PixNet, COBRA, JAB Code), color science
**Why overlooked:** Aurexis doesn't currently embed explicit color reference patches.
**Aurexis problem:** Camera white balance and ambient lighting shift perceived colors.
**Translation:** Embed known-color reference cells at regular intervals throughout the artifact grid (not just the border). At decode: measure observed colors at reference positions, fit a 3×3 affine matrix mapping observed → expected RGB, apply correction to all data cells.
**Implementation:** Von Kries diagonal model (3 scale factors) is minimum viable. Full 3×3 affine (9 parameters, least-squares from reference patches) is better.
**Evidence quality:** Used by JAB Code (ISO standard), COBRA, CamCode, HCCB. Proven in production.
**Best sources:**
- JAB Code ISO/IEC 23634:2022
- CamCode (Microsoft Research, 2016)
- Hao et al., "COBRA: Color Barcode Streaming," ACM MobiSys, 2012

### Vein 5: Sauvola Adaptive Thresholding

**Source domain:** Document image binarization
**Why overlooked:** Aurexis uses global Otsu because it's simpler and sufficient for synthetic images. Real camera images will need local adaptation.
**Aurexis problem:** Global Otsu fails under uneven lighting (shadow across artifact, vignetting, specular highlight).
**Translation:** Replace global Otsu with Sauvola: T(x,y) = mean(x,y) * (1 + k * (stdev(x,y)/R - 1)). Use Shafait integral-image optimization for O(1) per pixel regardless of window size.
**Implementation:** Two passes (build integral images of I and I², then compute per-pixel thresholds). ~30 lines.
**Evidence quality:** Sauvola (2000) has 3000+ citations. Shafait optimization (2008) is the standard implementation.
**Reference library:** Doxa (github.com/brandonmpetty/Doxa) — CC0 license, 14+ algorithms, SIMD optimized.
**Best sources:**
- Sauvola & Pietikinen, "Adaptive document image binarization," Pattern Recognition, 2000
- Shafait, Keysers & Breuel, "Efficient implementation of local adaptive thresholding," SPIE 2008
- Doxa: https://github.com/brandonmpetty/Doxa

### Vein 6: Normalized DLT for Homography

**Source domain:** Photogrammetry, multiple view geometry
**Why overlooked:** Trivial to implement but easy to forget. The unnormalized 4-point solve works fine on synthetic images but degrades on real images with large coordinate values.
**Aurexis problem:** Homography numerical conditioning when artifact is small or off-center in a large image.
**Translation:** Before solving the DLT system, normalize source and destination points: translate to center at origin, scale so average distance from origin = √2. ~20 lines. Cost: negligible.
**Evidence quality:** Hartley 1997 is the definitive reference. ~6000 citations.
**Best sources:**
- Hartley, "In defense of the eight-point algorithm," IEEE TPAMI, 1997
- Hartley & Zisserman, *Multiple View Geometry*, Cambridge, 2003, Algorithm 4.2

### Vein 7: Subpixel Finder Localization (Forstner / Saddle-Point)

**Source domain:** Industrial metrology, camera calibration
**Why overlooked:** Barcode libraries use pixel-level detection. The metrology community's subpixel methods are in different journals.
**Aurexis problem:** Finder center localization accuracy directly determines homography quality. 0.5px error at finders ≈ 1-2 module offset at grid edges for large grids.
**Translation:** After detecting finder region, apply Forstner operator (weighted least-squares intersection of gradient lines) or saddle-point fitting (biquadratic surface fit at corner). Achieves 0.05-0.1 pixel accuracy.
**Implementation:** Forstner: compute 2×2 gradient matrix in local window, solve for intersection. Saddle-point: fit ax²+bxy+cy²+dx+ey+f to 5×5 window, solve for extremum.
**Evidence quality:** Forstner (1987) is foundational in photogrammetry. Saddle-point used by CALTag, ArUco, and camera calibration pipelines.
**Best sources:**
- Forstner & Gulch, "A fast operator for detection and precise location," ISPRS 1987
- ArUco cornerSubPix: Garrido-Jurado et al., Pattern Recognition, 2014
- Steger, *Machine Vision Algorithms and Applications*, Wiley-VCH, 2008/2018

### Vein 8: Cross-Ratio Validation of Timing Strips

**Source domain:** Classical projective geometry (19th century, von Staudt)
**Why overlooked:** Projective invariants are textbook material but never used in barcode decoders.
**Aurexis problem:** Timing strip validation currently samples individual points and checks B/W alternation. This is fragile under perspective because module centers shift.
**Translation:** The cross-ratio of 4 collinear points is projectively invariant. For equally spaced timing transitions at positions 0,1,2,3, the cross-ratio is always 4/3. Detect timing transitions, compute cross-ratios of consecutive groups of 4, compare to 4/3. Rejects false detections; over-determined system allows least-squares refinement.
**Implementation:** ~15 lines per timing strip direction.
**Evidence quality:** Cross-ratio invariance is a theorem, not an approximation. 150+ years old.
**Best sources:**
- Hartley & Zisserman, *Multiple View Geometry*, Cambridge, 2003, Ch. 2
- Pi-Tag (Bergamasco et al. 2013) uses cross-ratios for fiducial identification

### Vein 9: Contour-Hierarchy Finder Detection (TopoTag Concept)

**Source domain:** Fiducial marker systems (TopoTag, Yu et al. 2020)
**Why overlooked:** QR decoders standardized on 1:1:3:1:1 ratio scanning in the 1990s and never revisited.
**Aurexis problem:** Ratio scanning is inherently 1D — it fails when perspective distorts the ratio along the scan direction, and it generates many false positives on text/textures.
**Translation:** The finder pattern is a topologically nested structure (ring containing dot). Detect by: (1) adaptive threshold → binary image, (2) compute contour hierarchy (connected component tree), (3) find nodes at depth ≥ 3 with appropriate area ratios. Topological containment is invariant under any continuous deformation.
**Implementation:** If using OpenCV: `findContours` with `RETR_TREE` gives the hierarchy directly. In pure JS: extract connected components, build parent-child tree from containment.
**Evidence quality:** TopoTag (2020) demonstrated robustness advantages. The topology is provably invariant.
**Best sources:**
- Yu, Hu & Dai, "TopoTag: A robust and scalable topological fiducial marker system," IEEE TVCG, 2020

### Vein 10: HDC/VSA Cleanup Memory for Module Fusion

**Source domain:** Hyperdimensional computing (Kanerva 2009)
**Why overlooked:** HDC is known in the neuromorphic computing community, not in visual coding.
**Aurexis problem:** Multi-frame fusion currently uses arithmetic mean + hard vote. No principled confidence weighting. No noise-tolerant symbolic cleanup.
**Translation:** Assign random 10,000-bit vectors to each module class. Encode each observation as XOR(position_vec, class_vec) × confidence. Bundle (add) across frames. Clean up by finding nearest codebook vector. Cosine similarity to winner = natural confidence metric for RS erasure hints.
**Implementation:** Binary Spatter Codes: all operations are bitwise XOR and popcount. Microsecond-scale for entire grid.
**Evidence quality:** Kanerva 2009, Kleyko et al. 2023 survey (ACM Computing Surveys). Proven for noisy classification cleanup.
**Best sources:**
- Kanerva, "Hyperdimensional Computing: An Introduction," Cognitive Computation, 2009
- Kleyko et al., "A Survey on Hyperdimensional Computing," ACM Computing Surveys, 2023
- Neubert & Schubert, "Hyperdimensional Computing as a Framework for Systematic Aggregation of Image Descriptors," CVPR 2021

### Vein 11: Cellular Sheaf Diffusion on Artifact Grid

**Source domain:** Algebraic topology (Hansen & Ghrist 2019)
**Why overlooked:** Sheaf theory is considered extremely abstract. The sensor fusion community (Robinson 2017) knows about it but the barcode/visual-code community does not.
**Aurexis problem:** RS decoding treats each block independently with no spatial reasoning about WHERE errors likely are. Structural constraints (timing must alternate, finder must match bitmap) are checked but not propagated.
**Translation:** Model the artifact grid as a cellular sheaf: vertex stalks = confidence vectors over classes, edge restriction maps encode structural constraints (timing alternation, finder bitmap, neighbor consistency). The sheaf Laplacian L_F is a sparse block matrix. Running 3-5 steps of sheaf heat diffusion (x_{t+1} = x_t - α·L_F·x_t) smooths inconsistencies while respecting structural constraints.
**Implementation:** L_F is sparse (grid graph, bounded degree). Each diffusion step = sparse matrix-vector multiply. For 128×128 grid with 4 classes: ~65K multiply-adds per step. Trivial on modern hardware.
**Evidence quality:** Hansen & Ghrist 2019 (spectral theory proven). Robinson 2017 (sensor fusion demonstrated). Neural Sheaf Diffusion (NeurIPS 2022). The mapping to Aurexis is speculative but structurally exact.
**Best sources:**
- Hansen & Ghrist, "Toward a Spectral Theory of Cellular Sheaves," JACT, 2019 (https://arxiv.org/abs/1808.01513)
- Robinson, "Sheaves are the canonical data structure for sensor integration," Information Fusion, 2017
- Hansen, "A gentle introduction to sheaves on graphs" (https://www.jakobhansen.org/publications/gentleintroduction.pdf)

### Vein 12: De Bruijn Position Encoding

**Source domain:** Structured light for 3D scanning (Pagès et al. 2004)
**Why overlooked:** Structured light is a different field. De Bruijn sequences are well-known in combinatorics but not applied to barcode timing patterns.
**Aurexis problem:** Timing patterns require seeing the edge of the pattern to determine absolute position. Under occlusion or crop, position is lost.
**Translation:** A De Bruijn sequence of order K over alphabet A has the property that every subsequence of length K is unique. Embed a 2D De Bruijn pattern in the timing/background layer. Any visible K×K patch uniquely determines absolute grid position. This makes the code partially readable even when heavily occluded.
**Implementation:** Well-established construction algorithms for De Bruijn sequences. 2D extension uses product constructions.
**Evidence quality:** Proven in structured light. Pagès et al. 2004 survey covers implementations.
**Best sources:**
- Pagès, Salvi & Matabosch, "Overview of Coded Structured Light Techniques," Pattern Recognition, 2004

### Vein 13: Sheaf Consistency Radius for Frame Quality

**Source domain:** Topological sensor fusion (Robinson 2017)
**Why overlooked:** Same as Vein 11 — different communities.
**Aurexis problem:** No principled metric for frame quality or per-module inconsistency detection in multi-frame fusion.
**Translation:** The consistency radius measures how self-consistent a collection of sensor readings is. For Aurexis: compute consistency radius across frames; high = clean capture, low = problematic. The consistency filtration reveals which frames and modules are responsible for inconsistency — exactly the erasure hints RS needs.
**Implementation:** Quadratic program on the sheaf Laplacian. Sparse and fast for grid graphs.
**Best sources:**
- Robinson, "Sheaves are the canonical data structure for sensor integration," Information Fusion, 2017

### Vein 14: RaptorQ Fountain Code (Outer Code)

**Source domain:** Digital broadcasting, IETF (RFC 6330)
**Why overlooked:** Fountain codes are for packet erasure channels (internet streaming). The connection to "some modules are unreadable" is not obvious.
**Aurexis problem:** When entire regions of the artifact are unreadable (glare spot, finger, occlusion), those modules are erasures, not errors. RS handles errors but wastes correction capacity on erasures.
**Translation:** Use RaptorQ as outer code (handles erasures) + RS as inner code (handles classification errors). Two-layer approach standard in DVB-T2. Any set of readable encoding symbols equal to source symbols + ~1% overhead recovers full data.
**Implementation:** Rust crate `raptorq` (github.com/cberner/raptorq, MIT/Apache). Encoding format change required.
**Evidence quality:** RFC 6330 is an IETF standard. RaptorQ is proven in production broadcast systems.
**Best sources:**
- RFC 6330 (https://www.rfc-editor.org/rfc/rfc6330)
- Shokrollahi, "Raptor codes," IEEE Trans. IT, 2006
- raptorq: https://github.com/cberner/raptorq

### Vein 15: Screen-Camera Channel Pilot-Cell Estimation

**Source domain:** PixNet (MIT, 2010), telecom equalization
**Why overlooked:** PixNet is in the mobile systems community, not the barcode community.
**Aurexis problem:** Spatially varying illumination and lens vignetting cause per-region color shift.
**Translation:** Embed known-color pilot cells at regular intervals throughout the grid (not just border). At decode: measure distortion at each pilot, interpolate a spatially varying color transfer function, apply inverse to all data cells. This is exactly what telecom equalizers do with training sequences.
**Implementation:** Scatter pilot cells every N rows/columns. Bilinear interpolation of correction factors between pilots.
**Best sources:**
- Perli et al., "PixNet: Interference-Free Wireless Links Using LCD-Camera Pairs," ACM MobiCom, 2010

### Vein 16: Loopy BP on Grid MRF

**Source domain:** Graphical models, computer vision (decades of literature)
**Why overlooked:** MRF inference is associated with "soft" vision tasks (segmentation, denoising), not with structured code decoding.
**Aurexis problem:** Need to unify spatial consistency, structural constraints, and RS parity into one framework instead of treating them sequentially.
**Translation:** Model the artifact as a factor graph: one variable node per module (discrete label), one factor per RS parity check, one factor per structural constraint (timing, finder), one factor per spatial adjacency. Run max-product BP. The result IS the MAP estimate of the correct module assignment given all available information.
**Implementation:** Well-studied. Libraries: libDAI (C++), or direct implementation on the grid graph.
**Best sources:**
- Sudderth et al., "Signal and Image Processing with Belief Propagation," IEEE SPM, 2008

### Vein 17: Guruswami-Sudan List Decoding

**Source domain:** Algebraic coding theory (1999)
**Why overlooked:** Complex to implement. Few production implementations outside academia.
**Aurexis problem:** RS(255,223) hard-decision corrects 16 errors per block. Under warp, some blocks exceed this.
**Translation:** Hard-decision list decoder corrects up to ~22 errors (Johnson bound). 37% more correction capacity with same parity. Can be combined with Chase-type soft approaches.
**Implementation:** Sage (Python) includes an implementation. Moderate complexity for standalone.
**Evidence quality:** Guruswami & Sudan 1999 is a landmark paper. Mathematically proven bounds.
**Best sources:**
- Guruswami & Sudan, "Improved decoding of Reed-Solomon and algebraic-geometry codes," IEEE Trans. IT, 1999

### Vein 18: Differential Color Encoding

**Source domain:** Xerox PARC DataGlyphs (Hecht 1994)
**Why overlooked:** DataGlyphs are for print-scan, a different community.
**Aurexis problem:** Absolute color values shift with lighting and white balance.
**Translation:** Encode data as color difference between adjacent cells, not absolute color. This cancels slowly varying illumination. Cost: need periodic anchor cells to reset the differential chain and prevent error propagation.
**Implementation:** Straightforward encoding change. Anchor cells every N positions.
**Best sources:**
- Hecht, "Embedded Data Glyph Technology for Hardcopy Digital Documents," SPIE, 1994
- Bloomberg & Hecht, "Robust Data Embedding for Document Images," 2001

### Vein 19: JAB Code Color Calibration

**Source domain:** Fraunhofer SIT, ISO/IEC 23634:2022
**Why overlooked:** JAB Code is niche. Most developers haven't heard of it.
**Aurexis relevance:** JAB Code is the closest existing system to Aurexis. Its color calibration, LDPC ECC, and multi-symbol docking are directly relevant.
**Repo:** https://github.com/jabcode/jabcode (988 stars, C, LGPL 2.1 — study approach, do NOT copy code)
**What to study:** Color calibration from finder pattern known colors. LDPC for soft-decision native. Multi-symbol linking.

### Vein 20: libcimbar (Color-Icon-Matrix Barcode)

**Source domain:** Screen-camera data transfer
**Repo:** https://github.com/sz3/libcimbar (6,000 stars, C++, MPL-2.0, actively maintained)
**What it is:** Color grid barcode achieving 850 kbit/s throughput. Uses RS + fountain codes (wirehair) + zstd compression.
**Why relevant:** Proves color grid barcodes work at high throughput. Fountain code integration for lossy channel. Study their approach.

### Vein 21: Chromaticity-Plane Classification

**Source domain:** COBRA color barcode research
**Why overlooked:** Simple technique buried in an SCC paper.
**Aurexis problem:** Brightness variation shifts RGB values.
**Translation:** Project colors onto chromaticity plane: r = R/(R+G+B), g = G/(R+G+B). Classification in (r,g) space is invariant to brightness changes. For 4-8 color palettes, this works well.
**Implementation:** 3 divisions per pixel. Trivial.

### Vein 22: Homography Refinement via Levenberg-Marquardt

**Source domain:** Photogrammetry (Hartley & Zisserman "Gold Standard" algorithm)
**Why overlooked:** Linear DLT is "good enough" for synthetic images.
**Aurexis problem:** 4-point DLT gives an algebraic approximation. Under noise, the geometric error (reprojection) is not minimized.
**Translation:** After linear DLT, refine the 8-DOF homography by minimizing symmetric transfer error over all correspondences (finders + timing transitions + alignment patterns) using Levenberg-Marquardt. Typically reduces error 30-50% over linear-only.
**Implementation:** LM on 8 parameters with analytic Jacobian. Standard numerical optimization.

### Vein 23: Constellation Design for Color Palette

**Source domain:** Telecom QAM design, Bagherinia & Manduchi (2011)
**Why overlooked:** Color palette selection is usually ad hoc (red, blue, green, white "because they look different").
**Aurexis problem:** Optimal palette depends on camera noise characteristics, not human perception.
**Translation:** Choose palette colors to maximize minimum distance in the OBSERVED color space (after camera capture), not the designed color space. Account for camera Bayer pattern (blue channel is noisier), ISP white balance range, and ambient lighting variation. This is a sphere-packing problem in distorted 3D space.
**Implementation:** One-time offline optimization from a dataset of camera captures of test charts.
**Best sources:**
- Bagherinia & Manduchi, "A Theory of Color Barcodes," ICCV Workshops, 2011

### Vein 24: AprilTag-Style Quad Detection

**Source domain:** Robotics (Olson 2011, DARPA-funded)
**Why overlooked:** Different community (robotics vs. barcode).
**Aurexis relevance:** AprilTag's detection pipeline (adaptive threshold → union-find CCA → gradient clustering → quad fitting) is state-of-the-art for fiducial robustness. The adaptive threshold uses block-based local mean (integral image trick).
**What to study:** Detection pipeline architecture. Clean-room reimplement per IP framework.
**Repo:** https://github.com/AprilRobotics/apriltag (2.2k stars, C, BSD — study only)
**Best sources:**
- Olson, "AprilTag: A robust and flexible visual fiducial system," ICRA 2011
- Wang & Olson, "AprilTag 2: Efficient and robust fiducial detection," IROS 2016

### Vein 25: ChromaTag Color Pre-Filtering

**Source domain:** Fiducial markers (DeGol et al. 2017)
**Why overlooked:** Color fiducials are niche.
**Aurexis relevance:** ChromaTag classifies by RELATIVE color differences between adjacent regions (illumination-invariant to first order), not absolute values. Also uses known finder colors for in-situ calibration.
**Repo:** https://github.com/CogChameleon/ChromaTag (C++, ICCV 2017)

### Vein 26: Mahalanobis Distance Classification

**Source domain:** Statistical pattern recognition
**Why overlooked:** Nearest-RGB is simpler and "works" on synthetic images.
**Aurexis problem:** Camera color distributions are ellipsoidal, not spherical. RGB Euclidean distance misweights axes.
**Translation:** For each palette color, pre-compute covariance matrix from sample captures. Classify by minimum Mahalanobis distance: d_M = sqrt((x-μ)ᵀ Σ⁻¹ (x-μ)). Naturally handles elongated color distributions from white balance variation.
**Implementation:** Pre-compute 4 (or 8 or 16) 3×3 inverse covariance matrices. One matrix-vector multiply per classification.

### Vein 27: Phase Unwrapping for Periodic Timing Patterns

**Source domain:** Structured light profilometry
**Why overlooked:** Phase unwrapping is associated with 3D scanning, not barcode detection.
**Aurexis problem:** Timing patterns repeat periodically. Under occlusion, you can detect the local period but not which period you're in.
**Translation:** Embed two timing patterns with coprime periods (e.g., 7 and 11). Chinese Remainder Theorem uniquely determines position up to 77 cells. This is exactly multi-frequency phase unwrapping.
**Implementation:** Two timing tracks with different periodicities. CRT reconstruction.

### Vein 28: Moiré Filtering for Screen Display

**Source domain:** ScreenCodes (SCC research, Tung & Shin 2016)
**Why overlooked:** Moiré is treated as an unsolvable nuisance rather than a predictable interference pattern.
**Aurexis problem:** When artifacts are displayed on LCD screens and photographed, moiré interference degrades the image.
**Translation:** The moiré pattern has predictable spatial frequencies based on LCD pixel pitch vs. camera sampling rate. Apply notch filtering in the frequency domain before geometric recovery.
**Implementation:** FFT → identify moiré peaks → notch filter → IFFT. Standard signal processing.

---

## 5. Top 5 Highest-Leverage Directions

### Direction 1: QPP Pseudo-Random Interleaver

**Mechanism:** Quadratic permutation polynomial maps encoded byte positions to spatial grid positions, decorrelating spatial error clusters across RS blocks.
**Strongest sources:** Sun & Takeshita 2005 (IEEE Trans. IT), Lin & Costello 2004 (textbook)
**Aurexis branch:** RS codec / encoding format
**Scope:** Present — no format version break needed if interleaver spec is part of config
**First experiment:** Encode a 128×128-4c artifact with QPP interleaving. Render, apply hard warp, decode. Compare RS block failure rate to current (non-interleaved). Expect: 0 block failures where current shows 13/16.
**Falsification:** If spatially clustered errors still concentrate in the same RS blocks after interleaving, the interleaver's period or structure doesn't match the grid topology. Fix: try different QPP coefficients or switch to pure pseudo-random.
**Success looks like:** The hard-warp test (currently 13/16 RS failures) drops to 0 failures.
**Improves:** Error correction capacity (transport reliability)

### Direction 2: Chase-II Soft-Decision RS + Confidence Pipeline

**Mechanism:** Use color classification confidence margins as reliability information. Chase decoder flips least-reliable symbols and tries multiple RS decode candidates.
**Strongest sources:** Chase 1972, Xu & Hislop 2017
**Aurexis branch:** RS decoder, sampler (add confidence output)
**Scope:** Present — decoder upgrade only, no encoding change
**First experiment:** Modify `classifyModuleRgb` to also return confidence (ratio of 1st to 2nd nearest distance). Implement Chase-II with K=4. Test on warped images where standard RS fails.
**Falsification:** If classification errors are not concentrated in low-confidence modules (i.e., confidence doesn't predict errors), Chase decoding provides no gain. Test by correlating confidence with actual classification correctness.
**Success looks like:** 1-3 dB coding gain — decode succeeds on images where hard RS fails by 1-2 errors per block.
**Improves:** Observation quality, transport reliability

### Direction 3: CIELab + Reference-Patch Color Calibration

**Mechanism:** Perceptual color space + in-situ calibration from embedded known-color patches.
**Strongest sources:** CIE 1976 (Lab standard), JAB Code ISO/IEC 23634, COBRA MobiSys 2012
**Aurexis branch:** Sampler (color classification), encoding format (add reference patches)
**Scope:** Present — CIELab classification is a drop-in change; reference patches require format spec addition
**First experiment:** Switch classification to Lab space on existing synthetic tests. Measure misclassification rate vs. RGB under simulated white balance shift (multiply R channel by 0.8, B channel by 1.2).
**Falsification:** If Lab classification shows no improvement over RGB under simulated illuminant shift, the color palette may already be well-separated in RGB (possible for 4-color). Test with 8-color and 16-color palettes where improvement should be larger.
**Success looks like:** Misclassification rate under illuminant shift drops by 50%+ for 8-color palette.
**Improves:** Observation quality

### Direction 4: Sauvola Adaptive Thresholding + Contour-Hierarchy Finder Detection

**Mechanism:** Local adaptive binarization handles uneven lighting. Topological containment (nested components) detects finder patterns invariantly.
**Strongest sources:** Sauvola 2000, Shafait 2008, TopoTag (Yu 2020), AprilTag (Olson 2011)
**Aurexis branch:** Finder detection pipeline
**Scope:** Present
**First experiment:** Replace global Otsu with Sauvola (Shafait implementation). Add contour-hierarchy search for nested regions as alternative finder detection path alongside existing ratio scan. Test on images with simulated gradient illumination.
**Falsification:** If the artifact has sufficient contrast that Otsu still works and ratio scanning still finds finders under gradient illumination, the gain is marginal. Test with progressively worse illumination gradients.
**Success looks like:** Finder detection succeeds on images where current pipeline returns null due to threshold failure.
**Improves:** Observation quality, detection robustness

### Direction 5: Cellular Sheaf Consistency for Multi-Frame Fusion

**Mechanism:** Model multi-frame observations as a cellular sheaf on the artifact grid. Sheaf Laplacian diffusion enforces structural constraints while cleaning up noisy classifications. Consistency radius measures frame quality. Consistency filtration localizes problematic modules for RS erasure hints.
**Strongest sources:** Robinson 2017, Hansen & Ghrist 2019
**Aurexis branch:** Frame fusion accumulator
**Scope:** Mid-scope (present math, moderate implementation)
**First experiment:** Build the sheaf Laplacian for a 128×128 grid with timing strip restriction maps. Apply 5 steps of sheaf diffusion to a noisy classification. Measure classification accuracy before and after diffusion.
**Falsification:** If timing strip constraints don't propagate useful information to neighboring data modules (because the graph distance is too large), sheaf diffusion adds computation without benefit. Test by measuring module accuracy improvement vs. distance from timing strip.
**Success looks like:** Classification errors near timing strips drop significantly; sheaf consistency radius correlates with decode success/failure across frames.
**Improves:** Coherence, observation quality, diagnostic capability

---

## 6. Abandoned / Neglected Code and Repo Scan

| Repo | URL | Stars | Lang | License | Status | What's Reusable |
|------|-----|-------|------|---------|--------|-----------------|
| libcimbar | github.com/sz3/libcimbar | 6,000 | C++ | MPL-2.0 | Active (Jan 2026) | Color grid encode/decode, fountain codes, pipeline architecture |
| AprilTag | github.com/AprilRobotics/apriltag | 2,200 | C | BSD | Active (Aug 2025) | Quad detection, adaptive threshold, fiducial pipeline |
| JAB Code | github.com/jabcode/jabcode | 988 | C | LGPL 2.1 | Maintenance | Color calibration, LDPC, multi-symbol |
| quirc | github.com/dlbeer/quirc | 988 | C | ISC | Maintained | Minimal QR decoder, perspective correction |
| raptorq | github.com/cberner/raptorq | — | Rust | MIT/Apache | Active | RFC 6330 fountain code implementation |
| ED_Lib | github.com/CihanTopal/ED_Lib | 475 | C++ | MIT | Maintained | EDLines, EDCircles — fast line/circle detection |
| STag | github.com/ManfredStoiber/stag | 222 | C | MIT | Active fork | Ellipse-based homography refinement |
| ChromaTag | github.com/CogChameleon/ChromaTag | — | C++ | — | Academic | Color-based fiducial detection |
| Doxa | github.com/brandonmpetty/Doxa | 190 | C++ | CC0 | Active (Feb 2026) | 14+ binarization algorithms, SIMD, benchmarking |
| libcorrect | github.com/quiet/libcorrect | — | C | BSD-3 | Maintained | RS + convolutional codes, soft-decision Viterbi |
| schifra | github.com/ArashPartow/schifra | — | C++ | Custom | Maintained | RS library with interleaving support |
| BoofCV | github.com/lessthanoptimal/BoofCV | ~1,000 | Java | Apache | Active | QR detector with subpixel corners |
| libdmtx | github.com/dmtx/libdmtx | — | C | BSD | Maintained | Data Matrix decoder, edge-walking detection |
| LSD | github.com/centreborelli/lsd | — | C | AGPL | Maintained | Line Segment Detector, subpixel accuracy |
| voaidesr/QR | github.com/voaidesr/QR | — | Python | — | Educational | From-scratch QR pipeline reference |

**IP Note (per MEMORY.md):** All repos listed here are for STUDY ONLY. Clean-room reimplementation required for any technique adopted into Aurexis. Document the source of each idea in changelog. No code copying.

---

## 7. Old Institutional Knowledge Scan

### Xerox PARC — DataGlyphs (1994-2001)
Hecht and Bloomberg at PARC solved the print-scan channel robustness problem with three key insights: (1) self-clocking cell design (every glyph has a detectable edge, eliminating separate timing), (2) differential encoding (information in relative differences, not absolutes), (3) oversized marks to survive ink spread modeled as morphological dilation. These directly apply to Aurexis's camera channel.

### Microsoft Research — HCCB / Microsoft Tag (2007-2015)
Used triangular modules (different spatial-frequency properties than squares, less susceptible to grid-aligned color bleeding under bilinear interpolation) and per-capture affine color correction from embedded reference colors. Key learning: triangular modules reduce the exact boundary-bleeding problem Aurexis had before the sampling radius fix.

### Bell Labs — OFDM, Equalization, Constellation Design (1960s-1990s)
The screen-to-camera pipeline IS a communication channel. Training sequences → channel estimation → equalization maps directly to reference patches → color correction → classification. Constellation design (maximize minimum distance under noise) maps directly to palette optimization. Interleaving (break burst errors) maps directly to spatial interleaving.

### DARPA / Robotics — AprilTag (2011-present)
Originally funded through robotics programs. Solved the robust fiducial detection problem with adaptive thresholding + gradient-based quad detection. The key insight: detect shapes (quads) not patterns (ratios). This is more robust because shapes are 2D features while ratios are 1D.

### Fraunhofer SIT — JAB Code (2018-2022, ISO standardized)
The only ISO-standardized color 2D barcode. Key institutional knowledge: LDPC codes outperform RS for the camera color channel because they natively handle soft information. Color calibration from known finder colors is essential for production use. 8 colors is the practical maximum for phone cameras under real lighting.

### CIE (International Commission on Illumination) — Color Science Standards
CIELab (1976) remains the standard perceptual color space. The key knowledge: Euclidean distance in Lab space approximates perceptual color difference. RGB distance does not. This is well-known in color science but consistently ignored in barcode implementations.

---

## 8. Cross-Domain Synthesis

The deepest cross-domain transfers found:

1. **Telecom equalization → Aurexis color calibration.** The training-sequence → channel-estimation → equalization pipeline from wireline/wireless communications maps exactly to reference-patch → color-transfer-estimation → correction in Aurexis. Both solve the same problem: recovering a transmitted signal through a noisy, distorting channel.

2. **Structured light De Bruijn sequences → Aurexis timing/position encoding.** The single-shot structured light community solved the "absolute position from local context" problem 20 years ago. Their De Bruijn approach eliminates the need for global finder pattern visibility.

3. **Cellular sheaf theory → Aurexis multi-frame fusion.** Robinson's 2017 framework for sensor integration maps structurally exactly to multi-frame artifact decode. Stalks = classification vectors. Restriction maps = structural constraints. Global sections = consistent decode. Consistency radius = frame quality metric.

4. **3GPP QPP interleavers → Aurexis spatial error decorrelation.** The turbo code community's interleaver designs solve the exact same problem: burst errors in a 1D stream mapped from a 2D channel. The QPP interleaver's algebraic structure ensures optimal spread.

5. **DataGlyph self-clocking → Aurexis cell design.** Xerox's insight that every data element should also contribute to timing recovery eliminates the capacity overhead of dedicated timing strips.

---

## 9. What NOT to Chase

**Generic "use a bigger vision model" for detection.** Aurexis's value proposition is deterministic, law-governed processing. Adding a CNN/transformer for finder detection or module classification would improve accuracy on benchmarks but destroy the deterministic guarantee and add opaque failure modes.

**Persistent homology / TDA for finder detection.** Intellectually beautiful, computationally expensive, marginal benefit for high-contrast printed artifacts. Standard adaptive thresholding + contour hierarchy is faster and sufficient. Reserve TDA for heavily degraded artifact research.

**Category-theoretic architecture (operads, ologs).** Provides correct vocabulary but zero algorithms. Worth studying as Aurexis matures, but investing in formal category theory before the evidence loop works on real captures would be premature abstraction.

**Exotic optics (computational photography, light field cameras, coded apertures).** Not present-scope per project charter. Current bottleneck is not the camera — it's the software pipeline.

**Full LDPC replacement for RS.** High implementation complexity, requires encoding format change, and the gain over RS + Chase decoding is moderate (~1 dB). Do RS + Chase + interleaving first; if that's not enough, then consider LDPC.

**Koetter-Vardy algebraic soft-decision.** Theoretically optimal but implementation complexity is extreme. Chase-II gets 60-70% of the gain for 10% of the effort.

**Turbo codes for static artifacts.** Turbo codes are designed for streaming channels. For single-frame static decode, the latency of iterative decoding is wasted. LDPC is a better choice if you need modern codes.

---

## 10. Actionable Research Backlog

### Immediate Reading List
1. Chase 1972 — soft-decision decoding (2 pages, foundational)
2. Hartley 1997 — normalized DLT (~15 pages, critical for homography)
3. Sauvola 2000 + Shafait 2008 — adaptive thresholding
4. Xu & Hislop 2017 — soft-input QR decoding (validates Chase for barcodes)
5. Hansen, "A gentle introduction to sheaves on graphs" (accessible entry point to sheaf theory)
6. Olson, AprilTag 2011 (detection pipeline architecture)

### Prototype Candidates (build and test)
1. ~~QPP interleaver~~ **DONE** (2026-04-18) — Fisher-Yates pseudo-random permutation with deterministic seed. 150-byte burst test: corrected across all 16 blocks. Hard warp: no improvement (error rate exceeds aggregate RS capacity).
2. ~~CIELab classification~~ **DONE** (2026-04-18) — sRGB→XYZ→Lab pipeline + confidence output. WB-shift test: correctly classifies shifted colors.
3. ~~Chase-II decoder~~ **DONE** (2026-04-18) — K=4, 16 candidates per block. Recovers blocks with 17 errors (beyond hard t=16 limit) when reliability info provided.
4. Sauvola thresholding — implement Shafait version, test on synthetic gradient illumination (days)
5. Subpixel finder refinement (Forstner or saddle-point) — implement, measure corner accuracy (days)

### Experiment Sequence (fastest signal first)
1. **QPP interleaver** — biggest expected impact, lowest risk, fastest to validate
2. **CIELab classification** — trivial to implement, immediate A/B test possible
3. **Chase-II soft-decision** — moderate effort, clear measurable improvement
4. **Reference-patch calibration** — requires format spec addition but standard technique
5. **Sauvola + contour-hierarchy detection** — prepares for real camera images
6. **Subpixel finder + normalized DLT + LM refinement** — stack of geometric precision improvements
7. **HDC cleanup memory** — replace consensus voting with principled approach
8. **Sheaf Laplacian diffusion** — add spatial reasoning to multi-frame fusion
9. **De Bruijn timing patterns** — future occlusion robustness
10. **RaptorQ outer code** — future erasure resilience

### Ideas to Test First for Fastest Signal
- **QPP interleaver:** If the hard-warp test goes from 13/16 failures to 0, that's a definitive signal.
- **CIELab classification:** If misclassification rate drops measurably under simulated illuminant shift, that validates the perceptual color space approach.
- **Chase-II:** If it decodes images that hard RS can't, that proves soft information matters for this channel.

---

---

## 11. Deep Dive Addendum (2026-04-18): JAB Code, libcimbar, Constellation Design

### JAB Code (ISO/IEC 23634) — Key Engineering Details

**Color calibration:** 4 palettes embedded near corners. Decodes by normalizing both module RGB and palette RGB by `rgb/rgb_max` (unit-chromaticity), then minimum squared Euclidean distance in normalized space. For 8-color: up to 64 reference samples from finder cores + metadata positions. This is simpler than Von Kries or affine 3×3 — just chromaticity matching with per-zone nearest-palette interpolation. **Implication for Aurexis:** JAB's approach is a spatial Voronoi-style correction, not a global model. We could do better with a 3×3 affine fit from embedded reference patches, but JAB proves that even simple normalization works in production.

**LDPC configuration:** Gallager-construction regular LDPC. 11 ECC levels mapping to (wc,wr) pairs with rates 0.14-0.63. Default: level 3 = rate 0.55. Three decoder modes: hard-decision bit-flipping, iterative log-likelihood (sum-product with tanh LLR), belief propagation. Soft input initialized as `2*enc/variance`. Max 25 iterations. **Implication for Aurexis:** JAB proves LDPC works for camera color codes, but at considerable implementation cost. Our RS + Chase-II + interleaver stack is simpler and may approach similar performance for V1.

**Multi-symbol docking:** Up to 61 symbols in spiral arrangement. 14-module cross area between host and slave carries palette and metadata. Alignment extrapolated from host's patterns offset by 7× module size. **Implication for Aurexis:** Multi-symbol is future-scope but the cross-area metadata approach is clean.

**Color palette:** 4-color = black, cyan, yellow, magenta. 8-color = RGB cube corners. NOT perceptually optimized — uniform RGB cube subdivisions. **Implication for Aurexis:** JAB didn't optimize palettes. This is a clear opportunity for Aurexis to gain an edge via camera-capture-optimized palettes.

**Detection:** 5-layer cross finder (n:1:1:1:m), adaptive local thresholding (32×32 blocks), per-channel R/G/B scanning, 3×3 pixel module sampling.

### libcimbar — Architecture for High-Throughput Screen-Camera Transfer

**ECC:** Two-layer: RS(155,125) inner (30 parity, t=15 per block) via libcorrect + Wirehair fountain code outer. Wirehair (not RaptorQ) is bundled. Fountain metadata: 6 bytes per ~744-byte chunk. **Implication for Aurexis:** The RS parameters are weaker than ours (t=15 vs t=16) but the fountain code layer provides full erasure recovery across frames. The Wirehair library is MIT-compatible and handles partial frame loss gracefully.

**Interleaving:** Block interleave with 2 partitions, stride = ecc_block_size = 155. Deterministic, not pseudo-random. **Implication for Aurexis:** Our Fisher-Yates pseudo-random interleaver provides better scatter than libcimbar's block interleave, but their approach proves that even simple interleaving significantly improves burst resilience.

**Color encoding:** 4 colors: green, cyan, yellow, magenta. NO perceptual color space. Decode uses relative-color differencing `(R-G, G-B, B-R)` with squared Euclidean distance — provides illumination invariance. Optional Bradford/Moore-Penrose color correction matrix. 8-color was deprecated due to inconsistency. **Implication for Aurexis:** The `(R-G, G-B, B-R)` differencing trick is worth evaluating — it's simpler than full CIELab and provides first-order illumination invariance.

**Frame fusion:** NO pixel-level fusion. Each frame decoded independently, fountain code accumulates chunks. Corrupt frames simply discarded. **Implication for Aurexis:** For video decode, fountain codes make per-frame fusion unnecessary. Each frame is an independent attempt, and the outer code handles the combining. This is architecturally much simpler than sheaf-based pixel fusion.

**Detection:** 3 finder patterns (QR-style), 4th corner triangulated. Priority-queue flood-fill decode order: high-confidence cells first, drift propagation to neighbors. **Implication for Aurexis:** The flood-fill decode order is clever — it reduces cascading drift errors. Worth investigating for our sampling pipeline.

**Throughput:** 12,400 tiles × 6 bits = 9.3 KB/frame raw. Camera-limited to ~15 fps = ~112 KB/s practical. Shakycam frame detection discards transitional frames.

### Color Constellation Design — Key Findings

**Bagherinia & Manduchi 2011:** Modeled camera capture as affine transform A·c + b. Optimal palette maximizes minimum pairwise distance after unknown affine distortion. For 4 colors: regular tetrahedron inscribed in RGB cube (near black, red, green, blue) outperforms naive choices by 2-4× in error rate across 20 phones.

**Blue channel weakness:** Bayer CFA allocates 1/4 pixels to blue (vs 1/2 green). Blue SNR is 3-6 dB worse. Palettes relying on blue-channel separation (cyan vs white) are fragile. **Implication for Aurexis:** Our current 4-color palette [white, red, blue, green] relies on blue. A palette avoiding blue-channel dependency would be more robust on real cameras.

**Optimal palette structure:** For 4 colors: 2 luminance levels × 2 chrominances beats pure chrominance. For 8 colors: 2-3 luminance levels × 3-4 chrominances. COBRA empirically showed 2-lum × 4-chrom beats 8-chrominance by ~25% in error rate. **Implication for Aurexis:** Consider restructuring palettes around luminance-chrominance separation. This is independent of CIELab and stacks with it.

**Calibration interaction:** Palette colors CAN be used as calibration patches (efficient). Minimum 3 non-collinear calibration colors needed for affine model. 4+ patches with least-squares is standard.

---

## References (consolidated, alphabetical)

- Bagherinia & Manduchi, "A Theory of Color Barcodes," ICCV Workshops, 2011
- Barath et al., "MAGSAC++, a fast, reliable and accurate robust estimator," CVPR, 2020
- Bergamasco et al., "Pi-Tag: fast image-space marker design based on projective invariants," MVA, 2013
- Bergamasco et al., "RUNE-Tag: A high accuracy fiducial marker with strong occlusion resilience," CVPR, 2011
- Bloomberg & Hecht, "Robust Data Embedding for Document Images," 2001
- Bradley & Roth, "Adaptive Thresholding using the Integral Image," J. Graphics Tools, 2007
- Candes & Tao, "Decoding by Linear Programming," IEEE Trans. IT, 2005
- Chase, "A class of algorithms for decoding block codes," IEEE Trans. IT, 1972
- DeGol et al., "ChromaTag: A colored marker and fast detection algorithm," ICCV, 2017
- Flusser & Suk, "Pattern recognition by affine moment invariants," Pattern Recognition, 1993
- Flusser & Suk, "Projective moment invariants," IEEE TPAMI, 2004
- Forstner & Gulch, "A fast operator for detection and precise location," ISPRS, 1987
- Garrido-Jurado et al., "Automatic generation and detection of fiducial markers," Pattern Recognition, 2014
- Grompone von Gioi et al., "LSD: A Fast Line Segment Detector," IEEE TPAMI, 2010
- Guruswami & Sudan, "Improved decoding of Reed-Solomon codes," IEEE Trans. IT, 1999
- Hansen & Ghrist, "Toward a Spectral Theory of Cellular Sheaves," JACT, 2019
- Hao et al., "COBRA: Color Barcode Streaming," ACM MobiSys, 2012
- Hartley, "In defense of the eight-point algorithm," IEEE TPAMI, 1997
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, Cambridge, 2003
- Hecht, "Embedded Data Glyph Technology," SPIE, 1994
- Hu, "Visual pattern recognition by moment invariants," IRE Trans. IT, 1962
- Kanerva, "Hyperdimensional Computing: An Introduction," Cognitive Computation, 2009
- Kleyko et al., "A Survey on Hyperdimensional Computing," ACM Computing Surveys, 2023
- Koetter & Vardy, "Algebraic soft-decision decoding of Reed-Solomon codes," IEEE Trans. IT, 2003
- Liebowitz & Zisserman, "Metric rectification for perspective images of planes," CVPR, 1998
- Lin & Costello, *Error Control Coding*, 2nd ed., Prentice Hall, 2004
- Olson, "AprilTag: A robust and flexible visual fiducial system," ICRA, 2011
- Pagès et al., "Overview of Coded Structured Light Techniques," Pattern Recognition, 2004
- Panteleev & Kalachev, "Maximally Extendable Sheaf Codes," arXiv:2403.03651, 2024
- Perli et al., "PixNet: Interference-Free Wireless Links Using LCD-Camera Pairs," MobiCom, 2010
- RFC 6330, "RaptorQ Forward Error Correction Scheme," IETF, 2011
- Robinson, "Sheaves are the canonical data structure for sensor integration," Information Fusion, 2017
- Sauvola & Pietikinen, "Adaptive document image binarization," Pattern Recognition, 2000
- Shafait et al., "Efficient implementation of local adaptive thresholding," SPIE, 2008
- Shokrollahi, "Raptor codes," IEEE Trans. IT, 2006
- Steger, "An unbiased detector of curvilinear structures," IEEE TPAMI, 1998
- Sudderth et al., "Signal and Image Processing with Belief Propagation," IEEE SPM, 2008
- Sun & Takeshita, "Interleavers for turbo codes using permutation polynomials," IEEE Trans. IT, 2005
- Tardif, "Non-iterative approach for fast and accurate vanishing point detection," ICCV, 2009
- Wang & Olson, "AprilTag 2: Efficient and robust fiducial detection," IROS, 2016
- Xu & Hislop, "Soft-input decoding of QR barcodes," Electronics Letters, 2017
- Yu et al., "TopoTag: A robust and scalable topological fiducial marker system," IEEE TVCG, 2020
