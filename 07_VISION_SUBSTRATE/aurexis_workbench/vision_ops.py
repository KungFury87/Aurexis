"""Vision operators - extends the Workbench operator registry
with the primitives needed to express vision predicates in the
surface DSL.

Registered when this module is imported. Importing it once at
process start (e.g. via aurexis_workbench.starter or via the
vision CLI) makes every operator below available to predicates
in vocabulary files.

Each operator is type-checked against the Workbench substrate.
"""
from __future__ import annotations

import numpy as np

from . import operators as ops


# ---------- Bayer mosaic decomposition ----------

def _bayer_R(image):
    a = np.asarray(image, dtype=np.float64)
    return a[0::2, 0::2]

def _bayer_Gr(image):
    a = np.asarray(image, dtype=np.float64)
    return a[0::2, 1::2]

def _bayer_Gb(image):
    a = np.asarray(image, dtype=np.float64)
    return a[1::2, 0::2]

def _bayer_B(image):
    a = np.asarray(image, dtype=np.float64)
    return a[1::2, 1::2]


def _green_imbalance(image):
    a = np.asarray(image, dtype=np.float64)
    gr = a[0::2, 1::2].mean()
    gb = a[1::2, 0::2].mean()
    return float(abs(gr - gb) / (abs(gr) + abs(gb) + 1e-9))


def _channel_spread_norm(image):
    a = np.asarray(image, dtype=np.float64)
    means = [a[0::2, 0::2].mean(), a[0::2, 1::2].mean(),
              a[1::2, 0::2].mean(), a[1::2, 1::2].mean()]
    overall = float(np.mean(means))
    spread = float(max(means) - min(means))
    return spread / (abs(overall) + 1e-9)


# ---------- Frequency-domain operators ----------

def _fft_mag(image):
    a = np.asarray(image, dtype=np.float64)
    wy = np.hanning(a.shape[0])[:, None]
    wx = np.hanning(a.shape[1])[None, :]
    windowed = (a - a.mean()) * (wy * wx)
    f = np.fft.fftshift(np.fft.fft2(windowed))
    return np.abs(f)


def _fft_peak_to_floor(image, ignore_dc_radius=3):
    m = _fft_mag(image).copy()
    cy, cx = m.shape[0] // 2, m.shape[1] // 2
    yy, xx = np.indices(m.shape)
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    m[r < float(ignore_dc_radius)] = 0.0
    peak = float(m.max())
    positive = m[m > 0]
    if positive.size == 0:
        return 0.0
    floor = float(np.median(positive)) + 1e-9
    return peak / floor


def _fft_peak_radius(image, ignore_dc_radius=3):
    m = _fft_mag(image).copy()
    cy, cx = m.shape[0] // 2, m.shape[1] // 2
    yy, xx = np.indices(m.shape)
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    m[r < float(ignore_dc_radius)] = 0.0
    idx = int(np.argmax(m))
    py, px = np.unravel_index(idx, m.shape)
    return float(np.sqrt((py - cy) ** 2 + (px - cx) ** 2))


def _block_avg_2x2(image):
    a = np.asarray(image, dtype=np.float64)
    H, W = a.shape
    H2 = (H // 2) * 2; W2 = (W // 2) * 2
    sub = a[:H2, :W2]
    return (sub[0::2, 0::2] + sub[0::2, 1::2]
             + sub[1::2, 0::2] + sub[1::2, 1::2]) * 0.25


# ---------- Structure tensor ----------

def _gradients(image):
    a = np.asarray(image, dtype=np.float64)
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    gx[:, 1:-1] = (a[:, 2:] - a[:, :-2]) / 2.0
    gy[1:-1, :] = (a[2:, :] - a[:-2, :]) / 2.0
    return gx, gy


def _structure_tensor_coherence(image):
    gx, gy = _gradients(image)
    Jxx = float((gx * gx).sum())
    Jyy = float((gy * gy).sum())
    Jxy = float((gx * gy).sum())
    trace = Jxx + Jyy
    det = Jxx * Jyy - Jxy * Jxy
    disc = max(0.0, (trace * 0.5) ** 2 - det)
    sqrt_disc = float(np.sqrt(disc))
    l1 = trace * 0.5 + sqrt_disc
    l2 = trace * 0.5 - sqrt_disc
    return float((l1 - l2) / (l1 + l2 + 1e-12))


def _max_coherence_patch_coh(image, patch_size):
    a = np.asarray(image, dtype=np.float64)
    ps = int(min(patch_size, a.shape[0], a.shape[1]))
    if a.shape[0] == ps and a.shape[1] == ps:
        return _structure_tensor_coherence(a)
    gx, gy = _gradients(a)
    g_energy = gx * gx + gy * gy
    stride = max(1, ps // 4)
    H, W = a.shape
    best = -1.0
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for y in range(0, H - ps + 1, stride):
            for x in range(0, W - ps + 1, stride):
                if float(g_energy[y:y + ps, x:x + ps].sum()) < 1e-4:
                    continue
                coh = _structure_tensor_coherence(a[y:y + ps, x:x + ps])
                if coh > best:
                    best = coh
    if best < 0:
        return 0.0
    return float(best)


# ---------- Temporal operators (image_stack) ----------

def _stack_array(stack):
    s = np.asarray(stack, dtype=np.float64)
    if s.ndim != 3:
        raise ValueError(f"image_stack must be 3D, got {s.shape}")
    return s


def _temporal_diff(stack):
    """Mean abs(diff) / mean abs(signal) across adjacent pairs."""
    s = _stack_array(stack)
    if s.shape[0] < 2:
        return 0.0
    ratios = []
    for k in range(s.shape[0] - 1):
        a = s[k]; b = s[k + 1]
        sig = (np.abs(a) + np.abs(b)).mean() * 0.5 + 1e-9
        ratios.append(float(np.abs(b - a).mean()) / sig)
    return float(np.mean(ratios))


def _temporal_diff_coherence(stack):
    """Mean FFT peak-to-floor of frame-pair diffs (motion vs noise gate)."""
    s = _stack_array(stack)
    if s.shape[0] < 2:
        return 0.0
    cohs = []
    for k in range(s.shape[0] - 1):
        d = s[k + 1] - s[k]
        cohs.append(_fft_peak_to_floor(d))
    return float(np.mean(cohs))


def _temporal_uniform_ratio(stack):
    """|mean(diff)| / mean(|diff|) - drift vs structured-motion gate."""
    s = _stack_array(stack)
    if s.shape[0] < 2:
        return 0.0
    ratios = []
    for k in range(s.shape[0] - 1):
        d = s[k + 1] - s[k]
        denom = float(np.abs(d).mean()) + 1e-12
        ratios.append(float(abs(d.mean())) / denom)
    return float(np.mean(ratios))


# ---------- Rotated-pair (polarization analogue) ----------

def _rotated_pair_anisotropy(image_a, image_b):
    a = float(np.asarray(image_a, dtype=np.float64).mean())
    b = float(np.asarray(image_b, dtype=np.float64).mean())
    return float((a - b) / (a + b + 1e-9))


# ---------- Scalar arithmetic ----------

def _abs_s(x): return float(abs(float(x)))
def _div_s(a, b): return float(a) / (float(b) + 1e-12)
def _mul_s(a, b): return float(a) * float(b)
def _sub_s(a, b): return float(a) - float(b)
def _add_s(a, b): return float(a) + float(b)



# ---------- Operators added in vocabulary v0.2 ----------

def _gradient_energy(image):
    """Total squared-gradient energy normalised by area. Distinguishes
    a textured scene from a uniform field."""
    gx, gy = _gradients(image)
    a = np.asarray(image, dtype=np.float64)
    return float(((gx * gx + gy * gy).sum()) / max(a.size, 1))


def _row_autocorr_peak(image, row_y):
    """Peak of (non-trivial) autocorrelation along a single row.
    A scalar in [0,1]-ish: high = repetitive horizontal pattern."""
    a = np.asarray(image, dtype=np.float64)
    y = int(row_y) % a.shape[0]
    row = a[y] - a[y].mean()
    if row.std() < 1e-9:
        return 0.0
    n = row.size
    ac = np.correlate(row, row, mode="full")[n - 1:]
    if ac[0] <= 0:
        return 0.0
    nontrivial = ac[max(4, n // 32):n // 2]
    if nontrivial.size == 0:
        return 0.0
    return float(nontrivial.max() / ac[0])


def _high_frequency_residual(image):
    """Energy in high spatial frequencies relative to total. High =
    sharp / detailed; low = blurred / uniform / out-of-focus."""
    m = _fft_mag(image)
    cy, cx = m.shape[0] // 2, m.shape[1] // 2
    yy, xx = np.indices(m.shape)
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    r_max = float(r.max())
    high_band = m * (r > 0.5 * r_max)
    return float(high_band.sum()) / float(m.sum() + 1e-9)


def _center_gradient_concentration(image):
    """Fraction of total gradient energy concentrated in the centre
    50 percent (by both axes). A "centred subject" measure."""
    gx, gy = _gradients(image)
    e = gx * gx + gy * gy
    h, w = e.shape
    cy0, cy1 = h // 4, 3 * h // 4
    cx0, cx1 = w // 4, 3 * w // 4
    total = float(e.sum()) + 1e-9
    centre = float(e[cy0:cy1, cx0:cx1].sum())
    return centre / total


def _is_uniform_field(image, threshold=1e-4):
    """Boolean-as-scalar: 1.0 if gradient energy < threshold, else 0.0.
    Used as a building block; the logic predicate is in vocab."""
    return 1.0 if _gradient_energy(image) < float(threshold) else 0.0



# ---------- Operators added in vocabulary v0.3 ----------

def _directional_gradient_energy(image, axis_label):
    """Energy in horizontal-vs-vertical gradients (label = 'horizontal'
    or 'vertical'). Distinguishes scenes dominated by horizontal edges
    (horizon, building floors) from those dominated by vertical edges
    (trees, columns, doorways)."""
    gx, gy = _gradients(image)
    label = str(axis_label).lower()
    if label == "horizontal":
        # gradients along x detect VERTICAL edges; rows of constant -> horizontal lines
        # we want energy of edges that ARE horizontal (i.e. gy is large at horizontal edges)
        return float((gy * gy).sum() / max(np.asarray(image).size, 1))
    if label == "vertical":
        return float((gx * gx).sum() / max(np.asarray(image).size, 1))
    raise ValueError("axis_label must be 'horizontal' or 'vertical'")


def _edge_density(image, k_threshold):
    """Fraction of pixels whose gradient magnitude exceeds
    mean + k * std. A complexity / detail metric."""
    gx, gy = _gradients(image)
    mag = np.sqrt(gx * gx + gy * gy)
    thr = float(mag.mean() + float(k_threshold) * mag.std())
    return float((mag > thr).sum() / max(mag.size, 1))


def _dynamic_range(image):
    """Std / (mean + eps). Scale-free contrast measure."""
    a = np.asarray(image, dtype=np.float64)
    return float(a.std() / (abs(a.mean()) + 1e-9))



# ---------- Operators added in vocabulary v0.4: concept scoring ----------

def _clamp_unit(value, ref):
    """Map value/ref to [0, 1]. NaN-safe."""
    if value != value:  # NaN
        return 0.0
    if ref == 0:
        return 0.0
    r = float(value) / float(ref)
    if r < 0.0:
        return 0.0
    if r > 1.0:
        return 1.0
    return r


def _mirror_corr_inline(image, axis):
    """NaN-safe mirror correlation (avoids cross-module dependency)."""
    a = np.asarray(image, dtype=np.float64)
    if a.std() < 1e-9:
        return 0.0
    if str(axis) == "vertical":
        m = a[:, ::-1]
    elif str(axis) == "horizontal":
        m = a[::-1, :]
    else:
        return 0.0
    av = a.flatten(); mv = m.flatten()
    if mv.std() < 1e-9:
        return 0.0
    c = float(np.corrcoef(av, mv)[0, 1])
    return c if c == c else 0.0


def _face_likeness_score(image, patch_size):
    """[0,1] score: ALL three indicators must fire to get high score.
    min() is the semantic of 'all components present', avoiding the
    saturation problem where one strong component (typically mirror
    correlation, near-1.0 on uniform-ish images) drives the mean."""
    mv = max(0.0, _mirror_corr_inline(image, "vertical"))
    centre = _center_gradient_concentration(image)
    patch_coh = _max_coherence_patch_coh(image, patch_size)
    return min(_clamp_unit(mv, 0.5),
                _clamp_unit(centre, 0.4),
                _clamp_unit(patch_coh, 0.45))


def _text_likeness_score(image, row_y):
    """[0,1] score: ALL three indicators must fire (min)."""
    autocorr = _row_autocorr_peak(image, row_y)
    hfr = _high_frequency_residual(image)
    edens = _edge_density(image, 1.0)
    return min(_clamp_unit(autocorr, 0.30),
                _clamp_unit(hfr, 0.15),
                _clamp_unit(edens, 0.10))


def _screen_likeness_score(image, row_y):
    """[0,1] score: ALL three indicators must fire (min)."""
    hfr = _high_frequency_residual(image)
    autocorr = _row_autocorr_peak(image, row_y)
    dynr = _dynamic_range(image)
    return min(_clamp_unit(hfr, 0.30),
                _clamp_unit(autocorr, 0.50),
                _clamp_unit(dynr, 0.60))


def _horizon_likeness_score(image):
    """[0,1] score: horizontal edges dominate vertical edges. A
    horizon scene has strong horizontal-line content and weak
    vertical structure. Mirror correlation is NOT a useful indicator
    because sky and ground differ - they are anti-correlated, not
    correlated. So this is a single-component score on the h/v
    edge ratio."""
    h_edges = _directional_gradient_energy(image, "horizontal")
    v_edges = _directional_gradient_energy(image, "vertical")
    h_dom = (h_edges / (v_edges + 1e-9)) - 1.0  # 0 = balanced; 1 = 2x; etc.
    return _clamp_unit(max(0.0, h_dom), 1.0)


def _max_s(a, b):
    return float(max(float(a), float(b)))



# ---------- Color operators (vocabulary v0.5) ----------
# These take a color_image (3-D ndarray HxWx3 in [0,1]) and return scalar
# measurements of channel means, saturation, palette properties.

def _ensure_color(img):
    a = np.asarray(img, dtype=np.float64)
    if a.ndim == 2:
        # grayscale -> stack to 3-channel
        a = np.stack([a, a, a], axis=-1)
    if a.ndim != 3 or a.shape[2] < 3:
        raise ValueError(f"color_image needs 3 channels, got shape {a.shape}")
    return a[..., :3]


def _rgb_channel_mean(color_image, channel_label):
    a = _ensure_color(color_image)
    label = str(channel_label).lower()
    if label == "r":   return float(a[..., 0].mean())
    if label == "g":   return float(a[..., 1].mean())
    if label == "b":   return float(a[..., 2].mean())
    raise ValueError("channel must be 'r', 'g', or 'b'")


def _rgb_saturation_mean(color_image):
    """Mean HSV saturation. 1.0 = fully saturated colors; 0.0 = grey."""
    a = _ensure_color(color_image)
    cmax = a.max(axis=-1)
    cmin = a.min(axis=-1)
    sat = np.where(cmax > 1e-9, (cmax - cmin) / (cmax + 1e-9), 0.0)
    return float(sat.mean())


def _rgb_value_mean(color_image):
    """Mean HSV value (= max RGB channel)."""
    a = _ensure_color(color_image)
    return float(a.max(axis=-1).mean())


def _rgb_warmth_score(color_image):
    """[0,1] proxy for warm-vs-cool: (R + 0.5*G - B + 1) / 2.5 clipped.
    Sunset / fire / orange = high. Sky / ocean / forest = low."""
    a = _ensure_color(color_image)
    r = a[..., 0].mean(); g = a[..., 1].mean(); b = a[..., 2].mean()
    raw = (r + 0.5 * g - b + 1.0) / 2.5
    return max(0.0, min(1.0, raw))


def _rgb_coolness_score(color_image):
    """[0,1] proxy for cool-dominance. Inverse of warmth, but with a
    blue/green floor that makes shaded scenes vs sunset distinct."""
    a = _ensure_color(color_image)
    r = a[..., 0].mean(); g = a[..., 1].mean(); b = a[..., 2].mean()
    raw = (b + 0.5 * g - r + 1.0) / 2.5
    return max(0.0, min(1.0, raw))


def _rgb_palette_diversity(color_image):
    """How spread out the color distribution is across pixels.
    Computed as the std of (R,G,B) magnitudes across pixels.
    A monochrome scene -> low; a vibrant varied scene -> high."""
    a = _ensure_color(color_image)
    flat = a.reshape(-1, 3)
    # std of each channel across pixels, averaged
    return float(flat.std(axis=0).mean())


def _rgb_monochrome_score(color_image):
    """[0,1] score: 1.0 if R == G == B everywhere; 0.0 if highly chromatic.
    Direct measure of greyscale-ness. Mean of |max - min| across pixels,
    inverted and clamped."""
    a = _ensure_color(color_image)
    chroma = a.max(axis=-1) - a.min(axis=-1)
    mean_chroma = float(chroma.mean())
    # high mean_chroma -> low monochrome score
    return max(0.0, 1.0 - 4.0 * mean_chroma)


def _rgb_dominant_channel_excess(color_image):
    """How much the dominant channel exceeds the mean of the other two.
    A red-dominated scene gives high positive excess; a balanced scene
    gives near zero. Used as a discriminator for has_red/green/blue_dominant."""
    a = _ensure_color(color_image)
    r = a[..., 0].mean(); g = a[..., 1].mean(); b = a[..., 2].mean()
    means = [r, g, b]
    top = max(means)
    others = sum(means) - top
    return float(top - others / 2.0)


def register_all() -> None:
    """Register all vision operators into the Workbench registry.
    Safe to call multiple times - re-registration is a no-op overwrite."""
    R = ops.register
    # Bayer
    R("bayer_R",  ("image",), "image", _bayer_R, "RGGB R sub-channel.")
    R("bayer_Gr", ("image",), "image", _bayer_Gr, "RGGB Gr sub-channel.")
    R("bayer_Gb", ("image",), "image", _bayer_Gb, "RGGB Gb sub-channel.")
    R("bayer_B",  ("image",), "image", _bayer_B, "RGGB B sub-channel.")
    R("green_imbalance", ("image",), "scalar", _green_imbalance,
       "|Gr-Gb|/(|Gr|+|Gb|) - non-RGB spectral signature.")
    R("channel_spread_norm", ("image",), "scalar", _channel_spread_norm,
       "(max-min Bayer channel mean) / overall mean.")
    # Spectrum
    R("fft_peak_to_floor", ("image",), "scalar", _fft_peak_to_floor,
       "FFT peak magnitude / median magnitude (peakedness).")
    R("fft_peak_radius", ("image",), "scalar", _fft_peak_radius,
       "Pixel-cycle radius of strongest non-DC FFT peak.")
    R("block_avg_2x2", ("image",), "image", _block_avg_2x2,
       "2x2 block-averaged 'demosaic-equivalent' downsample.")
    # Structure tensor
    R("structure_tensor_coherence", ("image",), "scalar",
       _structure_tensor_coherence,
       "Whole-image structure-tensor coherence in [0,1].")
    R("max_coherence_patch_coh", ("image", "int"), "scalar",
       _max_coherence_patch_coh,
       "Highest structure-tensor coherence over candidate patches.")
    # Temporal (image_stack)
    R("temporal_diff", ("image_stack",), "scalar", _temporal_diff,
       "Mean |diff| / mean |signal| across burst pairs.")
    R("temporal_diff_coherence", ("image_stack",), "scalar",
       _temporal_diff_coherence,
       "Mean FFT peak-to-floor of burst diff fields.")
    R("temporal_uniform_ratio", ("image_stack",), "scalar",
       _temporal_uniform_ratio,
       "|mean(diff)| / mean(|diff|) - 1.0 = uniform shift.")
    # Rotated pair
    R("rotated_pair_anisotropy", ("image", "image"), "scalar",
       _rotated_pair_anisotropy,
       "(I0 - I90) / (I0 + I90) for axis-pair captures.")
    # Scalar arithmetic
    R("abs_s", ("scalar",), "scalar", _abs_s, "Absolute value.")
    R("div_s", ("scalar", "scalar"), "scalar", _div_s, "Scalar divide.")
    R("mul_s", ("scalar", "scalar"), "scalar", _mul_s, "Scalar multiply.")
    R("sub_s", ("scalar", "scalar"), "scalar", _sub_s, "Scalar subtract.")
    R("add_s", ("scalar", "scalar"), "scalar", _add_s, "Scalar add.")
    # Vocabulary v0.2 operators
    R("gradient_energy", ("image",), "scalar", _gradient_energy,
       "Mean squared gradient energy per pixel.")
    R("row_autocorr_peak", ("image", "int"), "scalar", _row_autocorr_peak,
       "Peak non-trivial autocorrelation along a row (repetition signal).")
    R("high_frequency_residual", ("image",), "scalar", _high_frequency_residual,
       "Fraction of FFT magnitude in the upper-half spatial-frequency band.")
    R("center_gradient_concentration", ("image",), "scalar",
       _center_gradient_concentration,
       "Fraction of gradient energy in the centre 50 percent of the frame.")
    # Vocabulary v0.3 operators
    R("directional_gradient_energy", ("image", "label"), "scalar",
       _directional_gradient_energy,
       "Gradient energy in horizontal- vs vertical-edge direction.")
    R("edge_density", ("image", "scalar"), "scalar", _edge_density,
       "Fraction of pixels with gradient magnitude > mean + k*std.")
    R("dynamic_range", ("image",), "scalar", _dynamic_range,
       "Scale-free contrast: std / (|mean| + eps).")
    # Vocabulary v0.4 operators (scoring + max)
    R("face_likeness_score", ("image", "int"), "scalar",
       _face_likeness_score,
       "Continuous [0,1] face-like geometric signature score.")
    R("text_likeness_score", ("image", "int"), "scalar",
       _text_likeness_score,
       "Continuous [0,1] text-block-like signature score.")
    R("screen_likeness_score", ("image", "int"), "scalar",
       _screen_likeness_score,
       "Continuous [0,1] pixel-grid / display signature score.")
    R("horizon_likeness_score", ("image",), "scalar",
       _horizon_likeness_score,
       "Continuous [0,1] landscape-with-horizon signature score.")
    R("max_s", ("scalar", "scalar"), "scalar", _max_s, "Scalar max.")
    # Vocabulary v0.5 operators (color)
    R("rgb_channel_mean", ("color_image", "label"), "scalar",
       _rgb_channel_mean,
       "Mean of R, G, or B channel.")
    R("rgb_saturation_mean", ("color_image",), "scalar",
       _rgb_saturation_mean,
       "Mean HSV saturation. 0=grey, 1=fully saturated.")
    R("rgb_value_mean", ("color_image",), "scalar",
       _rgb_value_mean,
       "Mean HSV value (max channel per pixel).")
    R("rgb_warmth_score", ("color_image",), "scalar",
       _rgb_warmth_score,
       "[0,1] warm-palette proxy.")
    R("rgb_coolness_score", ("color_image",), "scalar",
       _rgb_coolness_score,
       "[0,1] cool-palette proxy.")
    R("rgb_palette_diversity", ("color_image",), "scalar",
       _rgb_palette_diversity,
       "Mean per-channel std across pixels (color spread).")
    R("rgb_monochrome_score", ("color_image",), "scalar",
       _rgb_monochrome_score,
       "[0,1] greyscale-ness (1=R=G=B).")
    R("rgb_dominant_channel_excess", ("color_image",), "scalar",
       _rgb_dominant_channel_excess,
       "Top channel mean minus average of others.")
