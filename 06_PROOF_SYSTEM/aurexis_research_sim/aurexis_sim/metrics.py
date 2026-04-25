"""Survival / recoverability metrics (RGB-aware as of v0.2).

Most metrics operate on luma. v0.2 adds per-channel PSNR and chroma error.
All metrics return plain Python floats. 1.0 = perfectly preserved unless noted.
"""
from __future__ import annotations

import numpy as np

from .utils import ensure_gray
from .color import is_rgb, luma
from .relations import compute_relation_metrics


def _sobel(img):
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = kx.T
    from .simulate import _convolve2d
    gx = _convolve2d(img, kx)
    gy = _convolve2d(img, ky)
    return np.sqrt(gx * gx + gy * gy)


def _as_luma(a):
    if is_rgb(a):
        return luma(a).astype(np.float32)
    return ensure_gray(a).astype(np.float32)


def mse(a, b):
    la = _as_luma(a); lb = _as_luma(b)
    return float(np.mean((la - lb) ** 2))


def psnr(a, b):
    m = mse(a, b)
    if m <= 1e-12:
        return 100.0
    return float(10.0 * np.log10(1.0 / m))


def ssim_simple(a, b):
    la = _as_luma(a); lb = _as_luma(b)
    mu_a = la.mean(); mu_b = lb.mean()
    va = la.var(); vb = lb.var()
    cov = ((la - mu_a) * (lb - mu_b)).mean()
    c1 = 0.01 ** 2; c2 = 0.03 ** 2
    num = (2 * mu_a * mu_b + c1) * (2 * cov + c2)
    den = (mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2)
    if den <= 0:
        return 0.0
    return float(np.clip(num / den, 0.0, 1.0))


def edge_survival(truth, captured, thresh=0.1):
    t = _as_luma(truth); c = _as_luma(captured)
    et = _sobel(t); ec = _sobel(c)
    if et.max() <= 1e-9:
        return 1.0
    mt = et / et.max()
    mc = ec / (ec.max() + 1e-9)
    truth_edges = mt > thresh
    if not truth_edges.any():
        return 1.0
    survived = mc[truth_edges] > thresh
    return float(survived.mean())


def adjacency_survival(labels, captured, tol=0.1):
    if labels is None:
        return float("nan")
    c = _as_luma(captured)
    ids = np.unique(labels)
    means = []
    for i in ids:
        m = labels == i
        if m.any():
            means.append((int(i), float(c[m].mean())))
    if len(means) < 2:
        return 1.0
    ids_arr = np.array([kv[0] for kv in means], dtype=np.float64)
    vals = np.array([kv[1] for kv in means], dtype=np.float64)
    r1 = ids_arr.argsort().argsort()
    r2 = vals.argsort().argsort()
    n = len(r1)
    if n < 2:
        return 1.0
    d2 = ((r1 - r2) ** 2).sum()
    rho = 1.0 - (6.0 * d2) / (n * (n * n - 1))
    return float(np.clip((rho + 1.0) / 2.0, 0.0, 1.0))


def local_corruption_map(truth, captured, block=16):
    t = _as_luma(truth); c = _as_luma(captured)
    h, w = t.shape
    bh = max(1, h // block); bw = max(1, w // block)
    out = np.zeros((bh, bw), dtype=np.float32)
    for i in range(bh):
        for j in range(bw):
            y0 = i * block; y1 = min(h, y0 + block)
            x0 = j * block; x1 = min(w, x0 + block)
            diff = t[y0:y1, x0:x1] - c[y0:y1, x0:x1]
            out[i, j] = float((diff * diff).mean())
    m = out.max()
    if m > 0:
        out = out / m
    return out


def global_recoverability(truth, captured):
    t = _as_luma(truth); c = _as_luma(captured)
    tf = t.flatten(); cf = c.flatten()
    A = np.stack([cf, np.ones_like(cf)], axis=1)
    coef, *_ = np.linalg.lstsq(A, tf, rcond=None)
    fit = A @ coef
    err = np.mean(np.abs(tf - fit))
    return float(np.clip(1.0 - err, 0.0, 1.0))


def relation_stability(labels, captured):
    if labels is None:
        return float("nan")
    c = _as_luma(captured)
    g = float(c.mean())
    ids = [i for i in np.unique(labels) if i != 0]
    if not ids:
        return float("nan")
    kept = 0
    for i in ids:
        m = labels == i
        if m.any() and float(c[m].mean()) > g + 0.05:
            kept += 1
    return float(kept / len(ids))


def per_channel_psnr(truth, captured):
    if not (is_rgb(truth) and is_rgb(captured)):
        return {"r": float("nan"), "g": float("nan"), "b": float("nan")}
    out = {}
    for c, name in enumerate(("r", "g", "b")):
        diff = truth[..., c].astype(np.float32) - captured[..., c].astype(np.float32)
        m = float(np.mean(diff * diff))
        out[name] = 100.0 if m <= 1e-12 else float(10.0 * np.log10(1.0 / m))
    return out


def chroma_error(truth, captured):
    if not (is_rgb(truth) and is_rgb(captured)):
        return float("nan")
    t = truth.astype(np.float32); c = captured.astype(np.float32)
    t_chroma = t - luma(t)[..., None]
    c_chroma = c - luma(c)[..., None]
    d = t_chroma - c_chroma
    return float(np.sqrt(np.mean(np.sum(d * d, axis=-1))))


def compute_all(truth, captured):
    t_img = truth["image"]
    labels = truth.get("labels")
    out = {
        "mse": mse(t_img, captured),
        "psnr_db": psnr(t_img, captured),
        "ssim_simple": ssim_simple(t_img, captured),
        "edge_survival": edge_survival(t_img, captured),
        "global_recoverability": global_recoverability(t_img, captured),
    }
    out["adjacency_survival"] = adjacency_survival(labels, captured) if labels is not None else float("nan")
    out["relation_stability"] = relation_stability(labels, captured) if labels is not None else float("nan")
    if is_rgb(t_img) and is_rgb(captured):
        pc = per_channel_psnr(t_img, captured)
        out["psnr_r_db"] = pc["r"]
        out["psnr_g_db"] = pc["g"]
        out["psnr_b_db"] = pc["b"]
        out["chroma_error"] = chroma_error(t_img, captured)
    # v0.3: bundle relation-survival if the probe advertises one
    rel_metrics = compute_relation_metrics(truth, captured)
    out.update(rel_metrics)
    return out
