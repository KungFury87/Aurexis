"""Shared helpers. Keep small."""
from __future__ import annotations

import numpy as np


def to_float(img):
    a = np.asarray(img)
    if a.dtype == np.uint8:
        return (a.astype(np.float32)) / 255.0
    a = a.astype(np.float32)
    if a.max() > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def to_uint8(img):
    a = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    return (a * 255.0 + 0.5).astype(np.uint8)


def save_png(path, img):
    from PIL import Image as _Image
    a = to_uint8(img)
    if a.ndim == 3 and a.shape[2] == 3:
        _Image.fromarray(a, mode="RGB").save(path)
    else:
        if a.ndim == 3 and a.shape[2] == 1:
            a = a[..., 0]
        _Image.fromarray(a, mode="L").save(path)


def ensure_gray(img):
    a = to_float(img)
    if a.ndim == 2:
        return a
    if a.ndim == 3 and a.shape[2] >= 3:
        return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    if a.ndim == 3 and a.shape[2] == 1:
        return a[..., 0]
    raise ValueError("Unsupported image shape " + str(a.shape))


def resize_to(img, size_hw):
    from PIL import Image
    h, w = size_hw
    a = to_uint8(img)
    mode = "L" if a.ndim == 2 else "RGB"
    pil = Image.fromarray(a, mode=mode)
    pil = pil.resize((w, h), Image.BILINEAR)
    return to_float(np.asarray(pil))


def clip01(a):
    return np.clip(a, 0.0, 1.0)
