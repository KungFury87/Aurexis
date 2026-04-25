"""Display/capture simulation chain.

Chain order (each stage optional):
    1. geometric        (scale + rotate + perspective)
    2. optical_blur     (gaussian PSF, applied per channel if RGB)
    3. motion_blur      (directional box kernel, per channel if RGB)
    4. rolling_shutter  (per-row horizontal shear, per channel if RGB)
    5. photometric      (exposure * contrast * gamma, per channel if RGB)
    6. SENSOR           (optional, v0.2): per-channel blur -> CFA mosaic ->
                        mosaic noise -> bilinear demosaic
    7. noise            (gaussian / shot, at final image level)
    8. quantize         (bit-depth)

Image representation is float32 in [0,1], shape HxW (grayscale) or HxWx3 (RGB).
Every stage accepts either; sensor stage requires (or promotes to) RGB.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Optional, Tuple

import numpy as np
from PIL import Image

from .utils import to_float, to_uint8, clip01
from .color import is_rgb, promote_to_rgb
from .sensor import SensorParams, run_sensor_stage


@dataclass
class SimParams:
    # Geometric
    scale: float = 1.0
    rotate_deg: float = 0.0
    perspective: float = 0.0
    # Optical
    blur_sigma: float = 0.0
    motion_blur_len: int = 0
    motion_blur_angle: float = 0.0
    rolling_shutter_shift: int = 0
    # Photometric
    exposure: float = 1.0
    gamma: float = 1.0
    contrast: float = 1.0
    # Noise
    gauss_noise: float = 0.0
    shot_noise: float = 0.0
    # Quantization
    bit_depth: int = 8
    # Sensor (v0.2)
    sensor: SensorParams = field(default_factory=SensorParams)

    def as_dict(self) -> dict:
        return asdict(self)


def _apply_per_channel(fn, img, *args, **kwargs):
    if is_rgb(img):
        out = np.empty_like(img)
        for c in range(3):
            out[..., c] = fn(img[..., c], *args, **kwargs)
        return out
    return fn(img, *args, **kwargs)


# ---- Geometric ----------------------------------------------------------

def _pil_gray_from(a):
    return Image.fromarray(to_uint8(a), mode="L")


def _np_gray_from(pil):
    return to_float(np.asarray(pil.convert("L")))


def _geometric_gray(img, p):
    h, w = img.shape
    pil = _pil_gray_from(img)
    if p.scale != 1.0 and p.scale > 0:
        new_w = max(2, int(round(w * p.scale)))
        new_h = max(2, int(round(h * p.scale)))
        pil = pil.resize((new_w, new_h), Image.BILINEAR)
        pil = pil.resize((w, h), Image.BILINEAR)
    if abs(p.rotate_deg) > 1e-6:
        pil = pil.rotate(p.rotate_deg, resample=Image.BILINEAR, fillcolor=0)
    if p.perspective > 1e-6:
        k = float(np.clip(p.perspective, 0.0, 0.45))
        dx = k * w
        src = [(0, 0), (w, 0), (w, h), (0, h)]
        dst = [(dx, 0), (w - dx, 0), (w, h), (0, h)]
        coeffs = _perspective_coeffs(src, dst)
        pil = pil.transform((w, h), Image.PERSPECTIVE, coeffs,
                            resample=Image.BILINEAR, fillcolor=0)
    return _np_gray_from(pil)


def apply_geometric(img, p):
    return _apply_per_channel(_geometric_gray, img, p)


def _perspective_coeffs(src, dst):
    matrix = []
    for (sx, sy), (dx, dy) in zip(src, dst):
        matrix.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        matrix.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
    A = np.array(matrix, dtype=np.float64)
    B = np.array(src, dtype=np.float64).reshape(8)
    res = np.linalg.solve(A, B)
    return tuple(res.tolist())


# ---- Optical blur (exported for sensor.py) ------------------------------

def _gaussian_kernel_1d(sigma):
    if sigma <= 0:
        return np.array([1.0], dtype=np.float32)
    radius = max(1, int(round(sigma * 3.0)))
    x = np.arange(-radius, radius + 1, dtype=np.float32)
    k = np.exp(-(x * x) / (2.0 * sigma * sigma))
    k /= k.sum()
    return k


def _conv1d(img, k, axis):
    r = (len(k) - 1) // 2
    if r == 0:
        return img
    pad = [(0, 0), (0, 0)]
    pad[axis] = (r, r)
    padded = np.pad(img, pad, mode="edge")
    out = np.zeros_like(img, dtype=np.float32)
    for i, wv in enumerate(k):
        sl = [slice(None), slice(None)]
        sl[axis] = slice(i, i + img.shape[axis])
        out += wv * padded[tuple(sl)]
    return out


def _blur_gray(img, sigma):
    if sigma <= 0:
        return img
    k = _gaussian_kernel_1d(sigma)
    out = _conv1d(img, k, axis=1)
    out = _conv1d(out, k, axis=0)
    return out


def apply_optical_blur(img, p):
    return _apply_per_channel(_blur_gray, img, p.blur_sigma)


# ---- Motion blur --------------------------------------------------------

def _convolve2d(img, k):
    from numpy.lib.stride_tricks import sliding_window_view
    kh, kw = k.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = np.pad(img, ((pad_h, pad_h), (pad_w, pad_w)), mode="edge").astype(np.float32)
    windows = sliding_window_view(padded, (kh, kw))
    return np.einsum("ijkl,kl->ij", windows, k.astype(np.float32))


def _motion_kernel(n, angle):
    if n <= 1:
        return None
    if n % 2 == 0:
        n += 1
    kernel = np.zeros((n, n), dtype=np.float32)
    kernel[n // 2, :] = 1.0 / n
    if abs(angle) > 1e-6:
        kpil = Image.fromarray((kernel * 255.0 / kernel.max()).astype(np.uint8), mode="L")
        kpil = kpil.rotate(angle, resample=Image.BILINEAR)
        kernel = np.asarray(kpil, dtype=np.float32)
        s = kernel.sum()
        if s > 0:
            kernel = kernel / s
    return kernel


def _motion_blur_gray(img, kernel):
    if kernel is None:
        return img
    return _convolve2d(img, kernel)


def apply_motion_blur(img, p):
    kernel = _motion_kernel(int(p.motion_blur_len), p.motion_blur_angle)
    return _apply_per_channel(_motion_blur_gray, img, kernel)


# ---- Rolling shutter (shear) --------------------------------------------

def _rolling_gray(img, max_shift):
    if max_shift == 0:
        return img
    h, w = img.shape
    out = np.zeros_like(img)
    for r in range(h):
        shift = int(round((r / max(1, h - 1)) * max_shift))
        if shift == 0:
            out[r] = img[r]
        elif shift > 0:
            out[r, shift:] = img[r, :w - shift]
            out[r, :shift] = img[r, 0]
        else:
            s = -shift
            out[r, :w - s] = img[r, s:]
            out[r, w - s:] = img[r, -1]
    return out


def apply_rolling_shutter(img, p):
    return _apply_per_channel(_rolling_gray, img, int(p.rolling_shutter_shift))


# ---- Photometric --------------------------------------------------------

def apply_photometric(img, p):
    x = img.astype(np.float32) * float(p.exposure)
    x = 0.5 + (x - 0.5) * float(p.contrast)
    x = clip01(x)
    g = float(p.gamma)
    if g > 0 and abs(g - 1.0) > 1e-6:
        x = np.power(x, g, dtype=np.float32)
    return clip01(x)


# ---- Final noise + quantize --------------------------------------------

def apply_noise(img, p, rng):
    out = img.astype(np.float32)
    if p.gauss_noise > 0:
        out = out + rng.normal(0.0, p.gauss_noise, size=out.shape).astype(np.float32)
    if p.shot_noise > 0:
        lam = np.maximum(out, 1e-6) / max(1e-6, p.shot_noise)
        draw = rng.poisson(lam).astype(np.float32) * p.shot_noise
        out = draw
    return clip01(out)


def apply_quantize(img, p):
    bits = int(np.clip(p.bit_depth, 1, 16))
    levels = (1 << bits) - 1
    return np.round(img * levels) / levels


# ---- End-to-end ---------------------------------------------------------

def run_chain(truth_img, params, seed=0):
    rng = np.random.default_rng(seed)

    x = truth_img.astype(np.float32)
    if params.sensor.enabled and not is_rgb(x):
        x = promote_to_rgb(x)

    stages = {"source": x.copy()}

    x = apply_geometric(x, params);    stages["geometric"] = x
    x = apply_optical_blur(x, params); stages["optical_blur"] = x
    x = apply_motion_blur(x, params);  stages["motion_blur"] = x
    x = apply_rolling_shutter(x, params); stages["rolling_shutter"] = x
    x = apply_photometric(x, params);  stages["photometric"] = x

    if params.sensor.enabled:
        if not is_rgb(x):
            x = promote_to_rgb(x)
        sensor_out = run_sensor_stage(x, params.sensor, rng)
        stages["sensor_pre_cfa"] = sensor_out["pre_cfa_rgb"]
        stages["sensor_mosaic"] = sensor_out["mosaic"]
        stages["sensor_mosaic_noisy"] = sensor_out["mosaic_noisy"]
        stages["sensor_demosaiced"] = sensor_out["demosaiced_rgb"]
        x = sensor_out["demosaiced_rgb"]

    x = apply_noise(x, params, rng);   stages["noise"] = x
    x = apply_quantize(x, params);     stages["quantize"] = x

    return {
        "captured": x,
        "stages": stages,
        "params": params.as_dict(),
        "seed": seed,
    }
