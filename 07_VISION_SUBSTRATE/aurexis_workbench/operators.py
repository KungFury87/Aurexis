"""Primitive operator registry.

An operator is a typed function over fields and constants: it takes
positional arguments of declared dtypes and returns a value of a
declared dtype. The set is deliberately compact for v2.0 — exactly
the operators the simulator has shown produce stable measurements,
plus a few obvious composers (==, <, >, and/or/not, count).

Adding new operators is a one-line registration. The predicate
compiler resolves operator names against this registry and
type-checks at compile time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple, Any, Optional

import numpy as np


@dataclass
class OpSig:
    name: str
    in_types: Tuple[str, ...]
    out_type: str
    fn: Callable[..., Any]
    doc: str = ""


REGISTRY: Dict[str, OpSig] = {}


def register(name: str, in_types, out_type: str, fn,
              doc: str = "") -> OpSig:
    sig = OpSig(name=name, in_types=tuple(in_types),
                  out_type=out_type, fn=fn, doc=doc)
    REGISTRY[name] = sig
    return sig


def get(name: str) -> OpSig:
    if name not in REGISTRY:
        raise KeyError("unknown operator: " + name)
    return REGISTRY[name]


def list_ops() -> List[str]:
    return sorted(REGISTRY.keys())


# =================================================================
# Image-level operators
# =================================================================

def _mean(image):
    a = np.asarray(image, dtype=np.float64)
    return float(a.mean())


def _std(image):
    a = np.asarray(image, dtype=np.float64)
    return float(a.std())


def _threshold(image, k):
    """Return an image (binary mask in [0,1]) where pixels exceed
    mean + k * std (clamped to mean + 0.10)."""
    a = np.asarray(image, dtype=np.float64)
    thr = float(a.mean() + float(k) * a.std())
    thr = max(thr, float(a.mean()) + 0.10)
    return (a > thr).astype(np.float64)


def _count_components(image):
    """Count 4-connected components of an image whose pixels are >0.5
    (treated as binary)."""
    binary = (np.asarray(image) > 0.5)
    if binary.sum() == 0:
        return 0
    h, w = binary.shape
    labels = np.zeros(binary.shape, dtype=np.int32)
    next_label = 0
    visited = np.zeros_like(binary)
    for y in range(h):
        for x in range(w):
            if binary[y, x] and not visited[y, x]:
                next_label += 1
                stack = [(y, x)]
                while stack:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= h or cx < 0 or cx >= w:
                        continue
                    if visited[cy, cx] or not binary[cy, cx]:
                        continue
                    visited[cy, cx] = True
                    labels[cy, cx] = next_label
                    stack.extend([(cy + 1, cx), (cy - 1, cx),
                                    (cy, cx + 1), (cy, cx - 1)])
    return int(next_label)


def _autocorr_period(image, row_y, target_period):
    """Return the lag (1..n//2) at which row_y's autocorrelation
    peaks. Returns -1 if undefined."""
    a = np.asarray(image, dtype=np.float64)
    if int(row_y) < 0 or int(row_y) >= a.shape[0]:
        return -1
    row = a[int(row_y)]
    n = row.size
    if n < int(2 * float(target_period)):
        return -1
    prof = row - row.mean()
    if prof.std() < 1e-9:
        return -1
    ac = np.correlate(prof, prof, mode="full")[n - 1:]
    max_lag = n // 2
    if max_lag < 5:
        return -1
    nontrivial = ac[1:max_lag + 1]
    if nontrivial.max() <= 0:
        return -1
    return int(np.argmax(nontrivial)) + 1


def _mirror_correlation(image, axis):
    """Return Pearson correlation between image and its mirror along
    axis ('vertical' or 'horizontal'). NaN if degenerate."""
    a = np.asarray(image, dtype=np.float64)
    if a.std() < 1e-9:
        return float("nan")
    if str(axis) == "vertical":
        m = a[:, ::-1]
    elif str(axis) == "horizontal":
        m = a[::-1, :]
    else:
        raise ValueError("axis must be 'vertical' or 'horizontal'")
    av = a.flatten(); mv = m.flatten()
    if mv.std() < 1e-9:
        return float("nan")
    c = float(np.corrcoef(av, mv)[0, 1])
    return c if c == c else float("nan")


def _structure_tensor_angle(image):
    """Dominant axis angle in degrees [0, 180); NaN if degenerate."""
    a = np.asarray(image, dtype=np.float64)
    if a.std() < 1e-6:
        return float("nan")
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
                    dtype=np.float64)
    ky = kx.T
    h, w = a.shape
    gx = np.zeros_like(a); gy = np.zeros_like(a)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ay0 = max(0, dy); ay1 = h + min(0, dy)
            ax0 = max(0, dx); ax1 = w + min(0, dx)
            by0 = max(0, -dy); by1 = h + min(0, -dy)
            bx0 = max(0, -dx); bx1 = w + min(0, -dx)
            gx[ay0:ay1, ax0:ax1] += kx[1 + dy, 1 + dx] \
                                     * a[by0:by1, bx0:bx1]
            gy[ay0:ay1, ax0:ax1] += ky[1 + dy, 1 + dx] \
                                     * a[by0:by1, bx0:bx1]
    Jxx = float((gx * gx).sum())
    Jyy = float((gy * gy).sum())
    Jxy = float((gx * gy).sum())
    if abs(Jxx) + abs(Jyy) + abs(Jxy) < 1e-9:
        return float("nan")
    theta = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy)
    stroke = theta + np.pi / 2.0
    return float(np.rad2deg(stroke) % 180.0)


# =================================================================
# Comparators / boolean composers
# =================================================================

def _eq(a, b): return bool(a == b)
def _neq(a, b): return bool(a != b)
def _lt(a, b): return bool(a < b)
def _gt(a, b): return bool(a > b)
def _leq(a, b): return bool(a <= b)
def _geq(a, b): return bool(a >= b)
def _and(a, b): return bool(a and b)
def _or(a, b):  return bool(a or b)
def _not(a):    return bool(not a)
def _within(x, target, tol):
    """True if abs(x - target) <= tol (numeric)."""
    return bool(abs(float(x) - float(target)) <= float(tol))


# =================================================================
# Built-in operator seeding
# =================================================================

def _seed_registry() -> None:
    REGISTRY.clear()

    # Image -> scalar
    register("mean", ("image",), "scalar", _mean,
             "Mean luminance of an image field.")
    register("std",  ("image",), "scalar", _std,
             "Standard deviation of an image field.")

    # Image, scalar -> image (binary mask as image of 0/1)
    register("threshold", ("image", "scalar"), "image", _threshold,
             "Binary mask of pixels exceeding mean + k*std.")

    # Image -> int
    register("count_components", ("image",), "int", _count_components,
             "Count 4-connected components of a binarised image.")

    # Image, int, scalar -> int  (lag in pixels; -1 if undefined)
    register("autocorr_period", ("image", "int", "scalar"), "int",
             _autocorr_period,
             "Dominant autocorrelation lag of row_y near target_period.")

    # Image, label -> scalar
    register("mirror_correlation", ("image", "label"), "scalar",
             _mirror_correlation,
             "Pearson correlation between image and its mirror "
             "about axis ('vertical' or 'horizontal').")

    # Image -> scalar (degrees, NaN if degenerate)
    register("structure_tensor_angle", ("image",), "scalar",
             _structure_tensor_angle,
             "Dominant axis angle (degrees, [0, 180)).")

    # Comparators
    for nm, fn, intypes in [
        ("eq",  _eq,  ("scalar", "scalar")),
        ("eq_int", _eq, ("int", "int")),
        ("eq_label", _eq, ("label", "label")),
        ("neq", _neq, ("scalar", "scalar")),
        ("lt",  _lt,  ("scalar", "scalar")),
        ("gt",  _gt,  ("scalar", "scalar")),
        ("leq", _leq, ("scalar", "scalar")),
        ("geq", _geq, ("scalar", "scalar")),
        ("lt_int",  _lt,  ("int", "int")),
        ("gt_int",  _gt,  ("int", "int")),
        ("leq_int", _leq, ("int", "int")),
        ("geq_int", _geq, ("int", "int")),
    ]:
        register(nm, intypes, "bool", fn,
                  "Comparator " + nm + ".")

    register("within", ("scalar", "scalar", "scalar"), "bool", _within,
              "True if abs(x - target) <= tol.")
    register("within_int", ("int", "int", "int"), "bool", _within,
              "True if abs(x - target) <= tol (int form).")

    # Boolean composers
    register("AND", ("bool", "bool"), "bool", _and, "Logical AND.")
    register("OR",  ("bool", "bool"), "bool", _or,  "Logical OR.")
    register("NOT", ("bool",), "bool", _not, "Logical NOT.")


_seed_registry()
