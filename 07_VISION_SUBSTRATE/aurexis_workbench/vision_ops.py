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



# ---------- HSV / wavelength-perceptual hue operators (vocabulary v0.6) ----------
#
# An RGB phone sensor cannot recover specific monochromatic wavelengths
# (metamerism: multiple spectra produce the same RGB triple). What it
# CAN recover is hue-bucket classification analogous to what human
# vision does: three broad bands -> perceptual hue label.
#
# HSV hue angles map (approximately) to peak wavelength labels:
#   0  / 360 deg   = red           (~625 nm)
#   30 deg         = orange        (~605 nm)
#   60 deg         = yellow        (~575 nm)
#   120 deg        = green         (~525 nm)
#   180 deg        = cyan          (~485 nm)
#   240 deg        = blue          (~445 nm)
#   270 deg        = violet        (~410 nm)
#   300 deg        = magenta       (no single wavelength; 400+700 mix)
#
# These operators classify EACH pixel into a named hue bucket
# absolutely (no relative comparison), gated by saturation+value so
# near-grey and near-black pixels do not contribute. This is the
# wavelength-identification signal a 3-band sensor permits.
#
# For TRUE multispectral identification (recovering specific
# wavelengths a 3-band RGB cannot distinguish), the harness would
# need a multispectral or hyperspectral sensor. That is a hardware
# unlock parallel to raw_bayer / polarization_pair, not a substrate
# extension. Documented in the BLOCKED predicates list.

HUE_BUCKETS = {
    "red":     None,         # special-case: wraps around 360/0
    "orange":  (15.0,  45.0),
    "yellow":  (45.0,  70.0),
    "green":   (70.0,  165.0),
    "cyan":    (165.0, 195.0),
    "blue":    (195.0, 255.0),
    "violet":  (255.0, 285.0),
    "magenta": (285.0, 345.0),
}


def _rgb_to_hsv_arrays(color_image):
    """Vectorised RGB->HSV. Returns (H, S, V) each HxW.
    H in [0, 360); S in [0, 1]; V in [0, 1]."""
    a = _ensure_color(color_image)
    r = a[..., 0]; g = a[..., 1]; b = a[..., 2]
    cmax = a.max(axis=-1)
    cmin = a.min(axis=-1)
    delta = cmax - cmin
    h = np.zeros_like(cmax)
    mask = delta > 1e-9
    rmax = mask & (np.isclose(cmax, r))
    gmax = mask & ~rmax & (np.isclose(cmax, g))
    bmax = mask & ~rmax & ~gmax
    h[rmax] = ((g[rmax] - b[rmax]) / (delta[rmax] + 1e-12)) % 6.0
    h[gmax] = (b[gmax] - r[gmax]) / (delta[gmax] + 1e-12) + 2.0
    h[bmax] = (r[bmax] - g[bmax]) / (delta[bmax] + 1e-12) + 4.0
    h = h * 60.0  # convert to degrees [0, 360)
    s = np.where(cmax > 1e-9, delta / (cmax + 1e-12), 0.0)
    v = cmax
    return h, s, v


def _hue_fraction(color_image, hue_label,
                    sat_min=0.15, val_min=0.10):
    """Fraction of meaningfully-colored pixels (saturation > sat_min
    AND value > val_min) that fall in the named hue bucket.

    'Meaningfully-colored' filter excludes near-grey, near-black, and
    near-white pixels which have undefined hue.

    Returns 0.0 if no pixels are meaningfully colored.
    Returns 1.0 if every meaningfully-colored pixel is in the bucket."""
    h, s, v = _rgb_to_hsv_arrays(color_image)
    valid = (s > float(sat_min)) & (v > float(val_min))
    valid_count = int(valid.sum())
    if valid_count == 0:
        return 0.0
    label = str(hue_label).lower()
    if label == "red":
        in_bucket = (h >= 345.0) | (h < 15.0)
    elif label in HUE_BUCKETS and HUE_BUCKETS[label] is not None:
        lo, hi = HUE_BUCKETS[label]
        in_bucket = (h >= lo) & (h < hi)
    else:
        raise ValueError(f"unknown hue label: {label}")
    return float((valid & in_bucket).sum()) / float(valid_count)


def _meaningfully_colored_fraction(color_image,
                                     sat_min=0.15, val_min=0.10):
    """Fraction of pixels that are NOT near-grey/black/white. Used as
    a gate: if this is below ~0.10, the scene is mostly achromatic."""
    h, s, v = _rgb_to_hsv_arrays(color_image)
    valid = (s > float(sat_min)) & (v > float(val_min))
    return float(valid.sum()) / float(valid.size)


def _hue_diversity_score(color_image,
                            sat_min=0.15, val_min=0.10):
    """[0,1] score for how many DIFFERENT hue buckets fire above 5%.
    1.0 = all 8 hues present at >5%; 0.0 = single hue dominates.
    Polychromatic-vs-monochromatic-but-saturated discriminator."""
    bucket_fractions = []
    for label in ["red", "orange", "yellow", "green",
                   "cyan", "blue", "violet", "magenta"]:
        f = _hue_fraction(color_image, label, sat_min, val_min)
        bucket_fractions.append(f)
    n_present = sum(1 for f in bucket_fractions if f > 0.05)
    return float(n_present) / 8.0



# ---------- Shape primitives via gradient-orientation distribution (v0.7) ----------
#
# Strategy: classify shapes by their gradient orientation distribution.
#   Circle / blob: gradients radiate uniformly (no preferred orientation)
#   Rectangle:    gradients concentrate at 0 deg AND 90 deg
#   Diagonal:     gradients concentrate at 45 deg / 135 deg
#   Curve:        gradients smoothly distributed, no sharp peaks, not uniform

def _gradient_orientation_hist(image, n_bins=18):
    """Magnitude-weighted gradient orientation histogram. Bins span
    [0, pi) since gradients are direction-symmetric. Returns
    normalised ndarray summing to 1.0 (or all zeros if no gradient)."""
    gx, gy = _gradients(image)
    mag = np.sqrt(gx * gx + gy * gy)
    ang = np.arctan2(gy, gx)
    ang_pos = np.mod(ang, np.pi)
    bins = np.linspace(0.0, np.pi, n_bins + 1)
    hist, _ = np.histogram(ang_pos.ravel(), bins=bins,
                              weights=mag.ravel())
    total = float(hist.sum())
    if total < 1e-12:
        return np.zeros(n_bins)
    return hist / total


def _orientation_uniformity(image):
    """[0,1] score: 1.0 = histogram bins all equal (isotropic / circular),
    0.0 = single bin holds all energy (perfectly oriented line)."""
    h = _gradient_orientation_hist(image, n_bins=18)
    if h.sum() < 1e-12:
        return 0.0
    expected = 1.0 / len(h)
    # std measures deviation from uniform; normalize by expected
    deviation = float(np.std(h))
    # 0 deviation = perfect uniform = 1.0; large deviation = 0.0
    return max(0.0, 1.0 - 5.0 * deviation)


def _orientation_mass_at_angle(image, angle_deg, tol_deg=15.0):
    """Fraction of gradient energy within +/- tol_deg of angle_deg
    (mod 180). Used to detect peaks at specific orientations."""
    gx, gy = _gradients(image)
    mag = np.sqrt(gx * gx + gy * gy)
    total = float(mag.sum())
    if total < 1e-12:
        return 0.0
    ang = np.arctan2(gy, gx)
    ang_deg_arr = np.degrees(np.mod(ang, np.pi))
    target = float(angle_deg) % 180.0
    diff = np.minimum(np.abs(ang_deg_arr - target),
                       180.0 - np.abs(ang_deg_arr - target))
    in_band = diff < float(tol_deg)
    return float(mag[in_band].sum()) / total


def _orientation_horizontal_mass(image):
    """Energy of HORIZONTAL LINES in the image. A horizontal line's
    gradient is perpendicular to the line, i.e. at 90 deg. Matches
    the directional_gradient_energy convention from earlier rounds."""
    return _orientation_mass_at_angle(image, 90.0, 15.0)


def _orientation_vertical_mass(image):
    """Energy of VERTICAL LINES (gradient at 0 deg)."""
    return _orientation_mass_at_angle(image, 0.0, 15.0)


def _orientation_diagonal_mass(image):
    """Combined 45 deg + 135 deg mass."""
    return (_orientation_mass_at_angle(image, 45.0, 15.0)
             + _orientation_mass_at_angle(image, 135.0, 15.0))


def _blob_count_thresh(image, k_threshold=1.5):
    """Count connected components in a thresholded binary mask via
    scipy.ndimage.label (fast). Falls back to numpy flood-fill if
    scipy unavailable."""
    a = np.asarray(image, dtype=np.float64)
    if a.std() < 1e-9:
        return 0
    thr = float(a.mean() + float(k_threshold) * a.std())
    binary = a > thr
    if binary.sum() == 0:
        return 0
    try:
        from scipy.ndimage import label as _ndlabel
        _, n = _ndlabel(binary)
        return int(n)
    except ImportError:
        pass
    h, w = binary.shape
    visited = np.zeros_like(binary)
    count = 0
    for y in range(h):
        for x in range(w):
            if binary[y, x] and not visited[y, x]:
                count += 1
                stack = [(y, x)]
                while stack:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= h or cx < 0 or cx >= w:
                        continue
                    if visited[cy, cx] or not binary[cy, cx]:
                        continue
                    visited[cy, cx] = True
                    stack.extend([(cy + 1, cx), (cy - 1, cx),
                                    (cy, cx + 1), (cy, cx - 1)])
    return int(count)



# ---------- Depth cues (vocabulary v0.8) ----------
# Single-image depth signals a human eye uses to perceive 3D from
# a flat photo: linear perspective, atmospheric haze, focus blur,
# corners (occlusion proxy), texture density gradient.

def _perspective_convergence_strength(image):
    """[0, ~1] score: asymmetric diagonal-line distribution between
    left and right halves of the image. A perspective scene with a
    road or hallway has 45-deg lines on one side and 135-deg lines
    on the other; symmetric scenes have balanced diagonals."""
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape
    left = a[:, :w // 2]
    right = a[:, w // 2:]
    left_45  = _orientation_mass_at_angle(left,  45.0, 20.0)
    left_135 = _orientation_mass_at_angle(left,  135.0, 20.0)
    right_45  = _orientation_mass_at_angle(right,  45.0, 20.0)
    right_135 = _orientation_mass_at_angle(right,  135.0, 20.0)
    # In a leftward-converging perspective scene, left half has more
    # 135deg lines (top-right to bottom-left), right has more 45deg.
    # The asymmetry is what we measure.
    asym = abs((left_135 - left_45) - (right_45 - right_135))
    return float(min(1.0, asym))


def _atmospheric_haze_score(color_image):
    """[0,1] score: top of image less saturated AND more blue-tinted
    than bottom. A hazy landscape has this signature - distant hills
    desaturate and shift cyan-blue, foreground stays saturated."""
    a = _ensure_color(color_image)
    h, w, _ = a.shape
    top = a[:h // 3]
    bottom = a[2 * h // 3:]
    # saturation gradient
    top_max = top.max(axis=-1); top_min = top.min(axis=-1)
    bot_max = bottom.max(axis=-1); bot_min = bottom.min(axis=-1)
    top_sat = float(np.where(top_max > 1e-6, (top_max - top_min) / (top_max + 1e-9), 0.0).mean())
    bot_sat = float(np.where(bot_max > 1e-6, (bot_max - bot_min) / (bot_max + 1e-9), 0.0).mean())
    sat_drop = bot_sat - top_sat
    # blue-shift: top has more B relative to R compared to bottom
    top_br_ratio = float(top[..., 2].mean() / (top[..., 0].mean() + 1e-9))
    bot_br_ratio = float(bottom[..., 2].mean() / (bottom[..., 0].mean() + 1e-9))
    blue_shift = top_br_ratio - bot_br_ratio
    # combine: both must be positive for haze
    score = max(0.0, sat_drop) * 2.0 + max(0.0, blue_shift) * 0.5
    return float(min(1.0, score))


def _focus_blur_gradient(image):
    """Center-vs-edges sharpness ratio. A shallow-depth-of-field
    scene has the subject (center) sharp and the surround blurred.
    Returns (center_sharpness - edge_sharpness) / (center + edge).

    Positive = subject sharp + surround blurred (DOF signature).
    Near zero = uniform focus or even sharpness everywhere."""
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape
    if h < 16 or w < 16:
        return 0.0
    gx, gy = _gradients(a)
    mag = np.sqrt(gx * gx + gy * gy)
    cy0, cy1 = h // 4, 3 * h // 4
    cx0, cx1 = w // 4, 3 * w // 4
    centre_mag = float(mag[cy0:cy1, cx0:cx1].mean())
    # edge ring: complement of centre
    full_sum = float(mag.sum())
    centre_sum = float(mag[cy0:cy1, cx0:cx1].sum())
    edge_pixels = mag.size - (cy1 - cy0) * (cx1 - cx0)
    if edge_pixels <= 0:
        return 0.0
    edge_mag = (full_sum - centre_sum) / float(edge_pixels)
    denom = centre_mag + edge_mag + 1e-9
    return float((centre_mag - edge_mag) / denom)


def _corner_count_thresh(image, k_threshold=0.04):
    """Count Harris-style corners. A corner is a pixel where both
    structure-tensor eigenvalues are large (i.e. R = det(M) - k*tr(M)^2
    above threshold). Numpy-only."""
    a = np.asarray(image, dtype=np.float64)
    if a.std() < 1e-9:
        return 0
    gx, gy = _gradients(a)
    # local sums via 3x3 box filter
    Ixx = gx * gx
    Iyy = gy * gy
    Ixy = gx * gy
    def _box3(arr):
        out = arr.copy()
        for k in range(2):
            shifted = arr.copy()
            shifted[1:-1, :] = (arr[:-2, :] + arr[1:-1, :] + arr[2:, :]) / 3.0
            out = (out + shifted) * 0.5
            shifted2 = out.copy()
            shifted2[:, 1:-1] = (out[:, :-2] + out[:, 1:-1] + out[:, 2:]) / 3.0
            out = shifted2
        return out
    sxx = _box3(Ixx); syy = _box3(Iyy); sxy = _box3(Ixy)
    det = sxx * syy - sxy * sxy
    trc = sxx + syy
    R = det - float(k_threshold) * trc * trc
    # threshold at 95th percentile to count strongest corners
    if R.max() < 1e-12:
        return 0
    thr = float(np.percentile(R[R > 0], 95)) if (R > 0).sum() > 0 else 0
    if thr <= 0:
        return 0
    return int((R > thr).sum())


def _texture_density_top_vs_bottom(image):
    """Difference in high-frequency residual between top and bottom
    halves. Positive = top has finer texture (perspective compression
    when viewing a uniform-textured plane like grass or pavement
    receding into the distance)."""
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape
    top = a[:h // 2]
    bot = a[h // 2:]
    top_hf = _high_frequency_residual(top)
    bot_hf = _high_frequency_residual(bot)
    return float(top_hf - bot_hf)



# ---------- Composition primitives (vocabulary v0.9) ----------
# What humans notice about photographic composition: rule-of-thirds
# placement, left-right and top-bottom balance, negative space,
# horizon-line position relative to the frame.

def _thirds_point_window(image, label, half_width_frac=0.10):
    """Return the (image_region, full_image_size) for the named
    thirds intersection point. label is 'tl', 'tr', 'bl', 'br' for
    top-left, top-right, bottom-left, bottom-right intersections
    at the 1/3 and 2/3 lines."""
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape[:2]
    cx_frac = 1.0 / 3.0 if label.lower() in ("tl", "bl") else 2.0 / 3.0
    cy_frac = 1.0 / 3.0 if label.lower() in ("tl", "tr") else 2.0 / 3.0
    cx = int(cx_frac * w); cy = int(cy_frac * h)
    hw = int(half_width_frac * min(h, w))
    y0, y1 = max(0, cy - hw), min(h, cy + hw)
    x0, x1 = max(0, cx - hw), min(w, cx + hw)
    return a[y0:y1, x0:x1], a.size


def _gradient_energy_at_thirds_point(image, label):
    """Fraction of total gradient energy concentrated at the named
    thirds intersection point (1/3 or 2/3 of frame)."""
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2:
        return 0.0
    gx, gy = _gradients(a)
    mag2 = gx * gx + gy * gy
    region, total_size = _thirds_point_window(a, label)
    h, w = a.shape
    cx_frac = 1.0 / 3.0 if str(label).lower() in ("tl", "bl") else 2.0 / 3.0
    cy_frac = 1.0 / 3.0 if str(label).lower() in ("tl", "tr") else 2.0 / 3.0
    cx = int(cx_frac * w); cy = int(cy_frac * h)
    hw = int(0.10 * min(h, w))
    y0, y1 = max(0, cy - hw), min(h, cy + hw)
    x0, x1 = max(0, cx - hw), min(w, cx + hw)
    region_energy = float(mag2[y0:y1, x0:x1].sum())
    total_energy = float(mag2.sum()) + 1e-9
    region_pixels = (y1 - y0) * (x1 - x0)
    total_pixels = mag2.size
    # density-normalized: how much MORE energy than expected from
    # a uniform distribution. >1.0 = concentrated; ~1.0 = uniform.
    expected_fraction = float(region_pixels) / float(total_pixels)
    actual_fraction = region_energy / total_energy
    return float(actual_fraction / (expected_fraction + 1e-9))


def _horizontal_split_balance(image):
    """[0,1] balance score for top-half vs bottom-half gradient energy.
    1.0 = perfectly balanced, 0.0 = all energy on one side."""
    a = np.asarray(image, dtype=np.float64)
    gx, gy = _gradients(a)
    mag = np.sqrt(gx * gx + gy * gy)
    h = a.shape[0]
    top = float(mag[:h // 2].sum())
    bot = float(mag[h // 2:].sum())
    if top + bot < 1e-9:
        return 1.0
    return float(min(top, bot) / max(top, bot))


def _vertical_split_balance(image):
    """[0,1] balance score for left-half vs right-half gradient energy."""
    a = np.asarray(image, dtype=np.float64)
    gx, gy = _gradients(a)
    mag = np.sqrt(gx * gx + gy * gy)
    w = a.shape[1]
    left = float(mag[:, :w // 2].sum())
    right = float(mag[:, w // 2:].sum())
    if left + right < 1e-9:
        return 1.0
    return float(min(left, right) / max(left, right))


def _negative_space_fraction(image, low_gradient_threshold=None):
    """Fraction of pixels whose local gradient magnitude is below a
    threshold (set automatically as 0.5 * mean gradient if not given).
    Large negative space = subject-on-clean-background composition."""
    a = np.asarray(image, dtype=np.float64)
    gx, gy = _gradients(a)
    mag = np.sqrt(gx * gx + gy * gy)
    if low_gradient_threshold is None:
        low_gradient_threshold = 0.5 * float(mag.mean())
    return float((mag < float(low_gradient_threshold)).sum()) / float(mag.size)


def _horizon_position_estimate(image):
    """Estimate the y-coordinate (0-1) of the strongest horizontal-line
    structure in the image. A horizon line is the row with maximum
    horizontal-edge gradient energy. Returns 0.0 if undefined."""
    a = np.asarray(image, dtype=np.float64)
    gx, gy = _gradients(a)
    # gy is the gradient in y direction = strongest at horizontal edges
    row_energy = (gy * gy).sum(axis=1)
    if row_energy.max() < 1e-9:
        return 0.5
    h = a.shape[0]
    peak_row = int(np.argmax(row_energy))
    return float(peak_row) / float(max(h - 1, 1))



# ---------- Motion direction / optical flow (vocabulary v0.10) ----------
# Round 11's has_subframe_motion only detects PRESENCE of motion.
# This round detects DIRECTION via FFT phase correlation between
# adjacent burst frames.

def _phase_corr_shift(a, b):
    """Returns (dy, dx) signed pixel shift such that B is shifted
    by (dy, dx) from A. Uses 2-D FFT cross-correlation with mean
    subtraction. (Standard phase-only correlation R/|R| fails on
    sparse signals like single moving blobs because it treats noise
    frequencies equally; cross-correlation weights by amplitude.)"""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    A = np.fft.fft2(a - a.mean())
    B = np.fft.fft2(b - b.mean())
    R = A * np.conj(B)
    corr = np.fft.ifft2(R).real
    peak = np.unravel_index(int(np.argmax(corr)), corr.shape)
    dy, dx = int(peak[0]), int(peak[1])
    H, W = corr.shape
    if dy > H // 2:
        dy -= H
    if dx > W // 2:
        dx -= W
    return float(dy), float(dx)


def _global_shift_estimate(image_stack, axis_label):
    """Mean signed shift in pixels along the named axis ('x' or 'y'),
    where positive = motion in that direction (right for x, down for y).

    Implementation note: phase correlation peak is at (-shift); we
    negate so the returned sign matches motion direction intuitively."""
    s = _stack_array(image_stack)
    if s.shape[0] < 2:
        return 0.0
    label = str(axis_label).lower()
    shifts_dy = []; shifts_dx = []
    for k in range(s.shape[0] - 1):
        dy, dx = _phase_corr_shift(s[k], s[k + 1])
        shifts_dy.append(-dy); shifts_dx.append(-dx)
    if label == "x":
        return float(np.mean(shifts_dx))
    if label == "y":
        return float(np.mean(shifts_dy))
    raise ValueError(f"axis must be 'x' or 'y'")


def _motion_coherence(image_stack):
    """[0,1] score: 1.0 = all frame-pair shifts agree in direction;
    0.0 = shifts are random (chaotic / camera shake / panning back
    and forth). Computed as |mean shift| / mean(|shift|)."""
    s = _stack_array(image_stack)
    if s.shape[0] < 2:
        return 1.0
    shifts_dy = []; shifts_dx = []
    for k in range(s.shape[0] - 1):
        dy, dx = _phase_corr_shift(s[k], s[k + 1])
        shifts_dy.append(dy); shifts_dx.append(dx)
    dy_arr = np.array(shifts_dy)
    dx_arr = np.array(shifts_dx)
    mag_per = np.sqrt(dy_arr ** 2 + dx_arr ** 2)
    if mag_per.mean() < 1e-9:
        return 1.0  # no motion at all = coherently motionless
    mean_vec = np.sqrt(dy_arr.mean() ** 2 + dx_arr.mean() ** 2)
    return float(mean_vec / (mag_per.mean() + 1e-9))


def _motion_velocity_mean(image_stack):
    """Mean magnitude (in pixels) of frame-pair shifts."""
    s = _stack_array(image_stack)
    if s.shape[0] < 2:
        return 0.0
    mags = []
    for k in range(s.shape[0] - 1):
        dy, dx = _phase_corr_shift(s[k], s[k + 1])
        mags.append(float(np.sqrt(dy * dy + dx * dx)))
    return float(np.mean(mags))



# ---------- Lighting / illumination primitives (vocabulary v0.11) ----------

def _bright_pixel_fraction(image, threshold=0.85):
    """Fraction of pixels with value above threshold (highlights)."""
    a = np.asarray(image, dtype=np.float64)
    return float((a > float(threshold)).sum()) / float(a.size)


def _dark_pixel_fraction(image, threshold=0.15):
    """Fraction of pixels with value below threshold (shadows)."""
    a = np.asarray(image, dtype=np.float64)
    return float((a < float(threshold)).sum()) / float(a.size)


def _bright_spot_count(image, threshold=0.92):
    """Count small connected regions of pixels above the very-bright
    threshold. Specular highlights show up as multiple tiny hot spots
    rather than one large bright area. Uses scipy.ndimage.label for
    fast vectorised labeling."""
    try:
        from scipy.ndimage import label as _ndlabel
    except ImportError:
        return _bright_spot_count_slow(image, threshold)
    a = np.asarray(image, dtype=np.float64)
    binary = a > float(threshold)
    if binary.sum() == 0:
        return 0
    labels, n = _ndlabel(binary)
    if n == 0:
        return 0
    h, w = binary.shape
    max_size = max(20, h * w // 1000)
    sizes = np.bincount(labels.ravel())[1:]  # skip background label 0
    return int(((sizes >= 1) & (sizes <= max_size)).sum())


def _bright_spot_count_slow(image, threshold=0.92):
    """Numpy-only fallback if scipy is unavailable."""
    a = np.asarray(image, dtype=np.float64)
    binary = a > float(threshold)
    if binary.sum() == 0:
        return 0
    h, w = binary.shape
    visited = np.zeros_like(binary)
    count = 0
    for y in range(h):
        for x in range(w):
            if binary[y, x] and not visited[y, x]:
                stack = [(y, x)]
                size = 0
                while stack:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= h or cx < 0 or cx >= w:
                        continue
                    if visited[cy, cx] or not binary[cy, cx]:
                        continue
                    visited[cy, cx] = True
                    size += 1
                    stack.extend([(cy + 1, cx), (cy - 1, cx),
                                    (cy, cx + 1), (cy, cx - 1)])
                if 1 <= size <= max(20, h * w // 1000):
                    count += 1
    return int(count)


def _center_minus_edge_brightness(image):
    """Mean brightness of centre 50% region minus mean brightness of
    edge ring. Positive = subject lit (portrait / spotlight).
    Negative = vignette / rim lighting."""
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape
    cy0, cy1 = h // 4, 3 * h // 4
    cx0, cx1 = w // 4, 3 * w // 4
    centre = a[cy0:cy1, cx0:cx1]
    centre_mean = float(centre.mean())
    centre_pixels = (cy1 - cy0) * (cx1 - cx0)
    total_pixels = a.size
    edge_pixels = total_pixels - centre_pixels
    if edge_pixels <= 0:
        return 0.0
    edge_sum = float(a.sum()) - float(centre.sum())
    edge_mean = edge_sum / float(edge_pixels)
    return centre_mean - edge_mean



# ---------- Curve detection redesign (vocabulary v0.12) ----------
# Round 11's has_curved_signature was an AND of 4 negations and fired
# 0% on the corpus. Round 18 replaces it with a positive test:
# a curved object has gradient orientations distributed across a
# CONTIGUOUS ARC of bins (smooth, neighboring bins similar) - neither
# a single sharp peak (line) nor uniform (circle) nor 2 disjoint
# clumps (rectangle / diagonal).

def _orientation_distribution_continuity(image, n_bins=18):
    """[0,1] score for curve signature: SINGLE broad peak in the
    cyclic gradient orientation histogram.

      Line:      single NARROW peak (1-2 bins)             -> low score
      Curve:     single BROAD peak (3-10 bins)              -> HIGH score
      Rectangle: TWO peaks separated by valleys              -> 0
      Diagonal:  TWO peaks (45 + 135 deg)                    -> 0
      Circle:    no clear peak (uniform)                     -> 0

    Algorithm: count local maxima of the histogram cyclically. If
    exactly 1, measure its width above half-max. Width 3-10 = curve."""
    h = _gradient_orientation_hist(image, n_bins=n_bins)
    if h.sum() < 1e-12:
        return 0.0
    h_max = float(h.max())
    if h_max < 1e-9:
        return 0.0
    # Bins above 0.7 * max are "in the peak region"
    threshold = h_max * 0.7
    above = h > threshold
    n_above = int(above.sum())
    # Width 3-10: broad smooth peak (curve)
    # Width 1-2: sharp narrow peak (line)
    # Width 11+: uniform (circle)
    if n_above < 3 or n_above > 10:
        return 0.0
    # Contiguity check (cyclic): all above-threshold bins form one arc
    extended = np.concatenate([above, above])
    runs = []
    i = 0
    while i < len(extended):
        if extended[i]:
            j = i
            while j < len(extended) and extended[j]:
                j += 1
            runs.append(j - i)
            i = j
        else:
            i += 1
    longest_run = max(runs, default=0)
    # Allow up to 1 stray noise bin outside the main arc
    if longest_run < n_above - 1:
        return 0.0  # peak split into multiple disjoint clumps (grid)
    # Also reject if the main arc itself is 1-2 bins (line, not curve)
    if longest_run < 3:
        return 0.0
    # Map width 3..10 to score 1.0..0.3
    score = max(0.3, 1.0 - (n_above - 3) / 14.0)
    return float(score)



# ---------- Perspective convergence redesign (vocabulary v0.12) ----------
# Round 12's _perspective_convergence_strength used L vs R diagonal
# asymmetry which gave ~0 on perspective_road (lines symmetric around
# centre vanishing point). This redesign uses TOP-vs-BOTTOM dominant
# orientation: a road / hallway has near-vertical lines at the bottom
# (close to camera) and near-horizontal lines at the top (where they
# converge). The angle of the dominant orientation rotates between
# the two strips.

def _top_vs_bottom_orientation_difference(image):
    """Absolute angular difference between the dominant orientation
    in the top 1/3 and bottom 1/3 of the image, in [0, 90] degrees.
    Larger = stronger perspective tilt."""
    a = np.asarray(image, dtype=np.float64)
    h, w = a.shape
    if h < 24:
        return 0.0
    top = a[:h // 3]
    bot = a[2 * h // 3:]
    # Re-use structure-tensor-like dominant angle via gradient histogram
    def _dominant_angle_deg(strip):
        gx, gy = _gradients(strip)
        mag = np.sqrt(gx * gx + gy * gy)
        if mag.max() < 1e-9:
            return None
        ang = np.arctan2(gy, gx)
        ang_pos = np.mod(ang, np.pi)
        # weighted circular mean (in 2*ang space for axial average)
        weights = mag.ravel()
        a2 = 2.0 * ang_pos.ravel()
        x = (weights * np.cos(a2)).sum()
        y = (weights * np.sin(a2)).sum()
        if x == 0 and y == 0:
            return None
        mean_ang_2 = np.arctan2(y, x)
        mean_ang = mean_ang_2 / 2.0  # back to [0, pi)
        return float(np.degrees(mean_ang) % 180.0)
    a_top = _dominant_angle_deg(top)
    a_bot = _dominant_angle_deg(bot)
    if a_top is None or a_bot is None:
        return 0.0
    diff = abs(a_top - a_bot)
    if diff > 90:
        diff = 180 - diff
    return float(diff)


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
    # Vocabulary v0.6 operators (HSV hue buckets - perceptual wavelength labels)
    R("hue_fraction", ("color_image", "label"), "scalar", _hue_fraction,
       "Fraction of saturated pixels in named hue bucket "
       "(red/orange/yellow/green/cyan/blue/violet/magenta).")
    R("meaningfully_colored_fraction", ("color_image",), "scalar",
       _meaningfully_colored_fraction,
       "Fraction of pixels that are not near-grey/black/white.")
    R("hue_diversity_score", ("color_image",), "scalar",
       _hue_diversity_score,
       "[0,1] score for how many of 8 hue buckets exceed 5% presence.")
    # Vocabulary v0.7 operators (shape primitives via orientation histogram)
    R("orientation_uniformity", ("image",), "scalar",
       _orientation_uniformity,
       "[0,1] score: 1=isotropic gradient distribution (circles/blobs).")
    R("orientation_horizontal_mass", ("image",), "scalar",
       _orientation_horizontal_mass,
       "Fraction of gradient energy at horizontal-axis orientation.")
    R("orientation_vertical_mass", ("image",), "scalar",
       _orientation_vertical_mass,
       "Fraction of gradient energy at vertical-axis orientation.")
    R("orientation_diagonal_mass", ("image",), "scalar",
       _orientation_diagonal_mass,
       "Combined fraction at 45 deg + 135 deg.")
    R("blob_count_thresh", ("image", "scalar"), "int",
       _blob_count_thresh,
       "Connected-component count in thresholded image.")
    # Vocabulary v0.8 operators (depth cues)
    R("perspective_convergence_strength", ("image",), "scalar",
       _perspective_convergence_strength,
       "Asymmetric diagonal-line distribution L vs R (perspective).")
    R("atmospheric_haze_score", ("color_image",), "scalar",
       _atmospheric_haze_score,
       "Top-region desaturation + blue-shift relative to bottom.")
    R("focus_blur_gradient", ("image",), "scalar",
       _focus_blur_gradient,
       "Spread of local sharpness across 4x4 tiles (DOF signature).")
    R("corner_count_thresh", ("image", "scalar"), "int",
       _corner_count_thresh,
       "Harris corner count above 95th-percentile threshold.")
    R("texture_density_top_vs_bottom", ("image",), "scalar",
       _texture_density_top_vs_bottom,
       "High-freq residual top minus bottom (perspective compression).")
    # Vocabulary v0.9 operators (composition primitives)
    R("gradient_energy_at_thirds_point", ("image", "label"), "scalar",
       _gradient_energy_at_thirds_point,
       "Density-normalised gradient energy at named thirds-intersection "
       "(label=tl/tr/bl/br). >1 = concentrated; ~1 = uniform.")
    R("horizontal_split_balance", ("image",), "scalar",
       _horizontal_split_balance,
       "[0,1]: 1=top and bottom equally weighted; 0=one side dominates.")
    R("vertical_split_balance", ("image",), "scalar",
       _vertical_split_balance,
       "[0,1]: 1=left and right equally weighted.")
    R("negative_space_fraction", ("image",), "scalar",
       _negative_space_fraction,
       "Fraction of pixels with below-mean local gradient magnitude.")
    R("horizon_position_estimate", ("image",), "scalar",
       _horizon_position_estimate,
       "[0,1]: y-position of strongest horizontal-edge row (0=top, 1=bottom).")
    # Vocabulary v0.11 operators (lighting / illumination)
    R("bright_pixel_fraction", ("image", "scalar"), "scalar",
       _bright_pixel_fraction,
       "Fraction of pixels above brightness threshold.")
    R("dark_pixel_fraction", ("image", "scalar"), "scalar",
       _dark_pixel_fraction,
       "Fraction of pixels below brightness threshold.")
    R("bright_spot_count", ("image", "scalar"), "int",
       _bright_spot_count,
       "Count of small (1-20px) connected high-brightness regions "
       "(specular highlights).")
    R("center_minus_edge_brightness", ("image",), "scalar",
       _center_minus_edge_brightness,
       "Centre mean brightness minus edge ring mean. + = subject lit.")
    # Vocabulary v0.12 operators (curve / perspective redesign)
    R("orientation_distribution_continuity", ("image",), "scalar",
       _orientation_distribution_continuity,
       "[0,1]: high when orientation histogram is smooth-contiguous "
       "(curve); low for lines (single peak), grids (multiple peaks), "
       "or isotropic (uniform).")
    R("top_vs_bottom_orientation_difference", ("image",), "scalar",
       _top_vs_bottom_orientation_difference,
       "Angular difference (deg) between top-strip and bottom-strip "
       "dominant orientations. Higher = stronger perspective tilt.")
    # Vocabulary v0.10 operators (motion direction via phase correlation)
    R("global_shift_estimate", ("image_stack", "label"), "scalar",
       _global_shift_estimate,
       "Mean signed pixel shift along axis ('x' or 'y') across burst pairs.")
    R("motion_coherence", ("image_stack",), "scalar",
       _motion_coherence,
       "[0,1]: 1=all frame-pair shifts agree (coherent); 0=chaotic/shake.")
    R("motion_velocity_mean", ("image_stack",), "scalar",
       _motion_velocity_mean,
       "Mean magnitude of frame-pair shifts in pixels.")
