"""Relation-primitive probes and relation-survival metrics (v0.3).

This module is the first relation-level layer of the research harness.
Each probe isolates ONE spatial/visual relation primitive so metrics can
score that primitive independent of generic image fidelity.

Design:
    - A probe returns the usual (image, labels, meta) triple but the meta
      dict carries an extra key 'relation' describing the relation the
      probe is designed to test, e.g.
          meta["relation"] = {"kind": "ordering", "rank_by_label": {1:1,2:2,...}}
    - A relation-metric function consumes that meta + labels + the
      captured image and returns a single survival score in [0,1]
      (1.0 = relation perfectly preserved).
    - `relation_report(truth_pkt, params, seed)` runs the full chain and
      evaluates the probe's relation metric at every intermediate stage,
      returning dict[stage_name -> survival]. This shows which stage
      kills the relation.

Honest scope:
    - These are SIMPLE, TESTABLE metrics. They are not meant to capture
      the full richness of any relation. They are meant to be useful
      enough to tell you 'the ordering relation is robust to blur but
      dies under Bayer demosaic', which is the point.
    - No claim of matching human perception.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .color import is_rgb, luma


# =========================================================================
# Probes
# =========================================================================

def ordering_probe(size=256, n=6, axis="horizontal", seed=0):
    """n markers arranged along an axis with monotonically increasing intensity.

    Label i encodes rank i. Relation under test: 'does captured-mean
    ordering match label-rank ordering?'
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.1, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(4, size // 40)
    rank_by_label = {}
    for i in range(n):
        frac = (i + 1) / (n + 1)
        # ranks 1..n; intensity monotonically increasing 0.2 .. 0.95
        intensity = 0.2 + 0.75 * (i / max(1, n - 1))
        if axis == "horizontal":
            cx = int(size * frac); cy = size // 2
        else:
            cx = size // 2; cy = int(size * frac)
        yy, xx = np.mgrid[0:size, 0:size]
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = intensity
        lab[m] = i + 1
        rank_by_label[i + 1] = i + 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "kind": "ordering_probe",
            "size": size, "n": n, "axis": axis, "seed": seed,
            "relation": {"kind": "ordering", "rank_by_label": rank_by_label},
        },
    }


def adjacency_probe(size=256, n_pairs=4, seed=0):
    """n_pairs pairs of adjacent markers. Within a pair the two members
    share intensity; different pairs have clearly different intensities.

    Relation under test: 'do paired-label means cluster more tightly with
    their partner than with members of other pairs?'
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 50)
    pair_gap = max(2 * r + 2, size // 18)
    pairs = []
    pair_values = np.linspace(0.25, 0.95, n_pairs).astype(np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    # Arrange pairs on a grid, each pair horizontally adjacent.
    cols = max(1, int(np.ceil(np.sqrt(n_pairs))))
    rows = int(np.ceil(n_pairs / cols))
    margin = size // (max(cols, rows) * 2 + 2)
    slot_w = (size - 2 * margin) // cols
    slot_h = (size - 2 * margin) // rows
    label_id = 1
    for p in range(n_pairs):
        gr = p // cols; gc = p % cols
        cy = margin + slot_h * gr + slot_h // 2
        cx = margin + slot_w * gc + slot_w // 2
        ax = cx - pair_gap // 2
        bx = cx + pair_gap // 2
        mA = (yy - cy) ** 2 + (xx - ax) ** 2 <= r * r
        mB = (yy - cy) ** 2 + (xx - bx) ** 2 <= r * r
        img[mA] = pair_values[p]
        img[mB] = pair_values[p]
        lab[mA] = label_id
        lab[mB] = label_id + 1
        pairs.append((label_id, label_id + 1))
        label_id += 2
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "kind": "adjacency_probe",
            "size": size, "n_pairs": n_pairs, "seed": seed,
            "relation": {"kind": "adjacency", "pairs": pairs},
        },
    }


def symmetry_probe(size=256, axis="vertical", seed=0):
    """Pattern with known bilateral symmetry across an axis.

    Relation under test: 'does the captured image still agree with its
    own mirror about the same axis?'
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    # Put a couple of distinct bright spots on left, then mirror to right.
    h = size
    w = size
    pts = [
        (int(0.30 * h), int(0.25 * w), 0.9),
        (int(0.55 * h), int(0.15 * w), 0.75),
        (int(0.78 * h), int(0.30 * w), 0.55),
        (int(0.40 * h), int(0.08 * w), 0.40),
    ]
    r = max(3, size // 40)
    yy, xx = np.mgrid[0:size, 0:size]
    for (cy, cx, v) in pts:
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = v
    # Mirror across vertical axis (columns) or horizontal axis (rows)
    if axis == "vertical":
        img[:, w // 2:] = img[:, w // 2 - 1::-1][:, :w - w // 2]
    else:
        img[h // 2:, :] = img[h // 2 - 1::-1, :][:h - h // 2, :]
    img += rng.normal(0.0, 0.003, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": None,
        "meta": {
            "kind": "symmetry_probe",
            "size": size, "axis": axis, "seed": seed,
            "relation": {"kind": "symmetry", "axis": axis},
        },
    }


def orientation_probe(size=256, n=4, seed=0):
    """n short strokes at known orientations (0, 45, 90, 135 deg by default).

    Relation under test: 'does the dominant gradient direction inside
    each stroke's region still point within tolerance of the known angle?'
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    angles = [0.0, 45.0, 90.0, 135.0]
    n = min(n, len(angles))
    angles = angles[:n]
    # Place n strokes on a row
    stroke_len = max(8, size // 8)
    stroke_w = max(2, size // 64)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    angle_by_label = {}
    for i, ang in enumerate(angles):
        cx = int(size * (i + 1) / (n + 1))
        cy = size // 2
        # Unit vector along the stroke direction
        rad = np.deg2rad(ang)
        ux, uy = np.cos(rad), np.sin(rad)
        # Perpendicular vector
        vx, vy = -uy, ux
        # Project each pixel onto (u, v)
        dx = xx - cx; dy = yy - cy
        proj_u = dx * ux + dy * uy
        proj_v = dx * vx + dy * vy
        mask = (np.abs(proj_u) <= stroke_len / 2.0) & (np.abs(proj_v) <= stroke_w / 2.0)
        img[mask] = 0.9
        lab[mask] = i + 1
        angle_by_label[i + 1] = float(ang)
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "kind": "orientation_probe",
            "size": size, "n": n, "seed": seed,
            "relation": {"kind": "orientation", "angle_by_label": angle_by_label},
        },
    }


def hierarchy_probe(size=256, seed=0):
    """Two outer groups, each containing two inner markers.

    Relation under test: 'does intra-group intensity difference remain
    smaller than inter-group intensity difference after capture?'
    Outer group A: labels 1,2 (shared intensity).
    Outer group B: labels 3,4 (shared intensity, different from A).
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 45)
    yy, xx = np.mgrid[0:size, 0:size]
    # Group A on left: labels 1, 2
    for i, (cx, cy) in enumerate([
        (int(0.22 * size), int(0.35 * size)),
        (int(0.32 * size), int(0.45 * size)),
    ]):
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.40
        lab[m] = i + 1
    # Group B on right: labels 3, 4
    for i, (cx, cy) in enumerate([
        (int(0.68 * size), int(0.60 * size)),
        (int(0.78 * size), int(0.70 * size)),
    ]):
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.85
        lab[m] = i + 3
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img,
        "labels": lab,
        "meta": {
            "kind": "hierarchy_probe",
            "size": size, "seed": seed,
            "relation": {
                "kind": "hierarchy",
                "groups": {1: "A", 2: "A", 3: "B", 4: "B"},
            },
        },
    }


# =========================================================================
# Metrics
# =========================================================================

def _lum(img):
    return luma(img).astype(np.float32) if is_rgb(img) else img.astype(np.float32)


def ordering_survival(truth_pkt, captured):
    """Spearman-like rank correlation between label rank and captured mean,
    mapped from [-1,1] to [0,1]. 1.0 = ordering perfectly preserved.
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "ordering":
        return float("nan")
    labels = truth_pkt.get("labels")
    rank_by_label = rel.get("rank_by_label", {})
    if labels is None or not rank_by_label:
        return float("nan")
    c = _lum(captured)
    ranks = []
    means = []
    for lbl, rk in rank_by_label.items():
        m = labels == int(lbl)
        if not m.any():
            continue
        ranks.append(int(rk))
        means.append(float(c[m].mean()))
    if len(ranks) < 2:
        return float("nan")
    # v0.8 anti-triviality: if captured means carry no rank
    # information (all nearly equal), ordering cannot be
    # recovered - return 0.0 rather than a spurious 1.0 from
    # stable argsort on tied values.
    means_arr = np.array(means, dtype=np.float64)
    if float(means_arr.std()) < 1e-3:
        return 0.0
    r1 = np.array(ranks).argsort().argsort()
    r2 = np.array(means).argsort().argsort()
    n = len(r1)
    d2 = float(((r1 - r2) ** 2).sum())
    rho = 1.0 - (6.0 * d2) / (n * (n * n - 1))
    return float(np.clip((rho + 1.0) / 2.0, 0.0, 1.0))


def adjacency_pair_survival(truth_pkt, captured):
    """For each labeled pair, score whether the two members' captured
    means are closer to each other than to members of other pairs.

    Returns fraction of pairs that pass that test. 1.0 = all pairs
    still cluster with their partner after capture.
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "adjacency":
        return float("nan")
    labels = truth_pkt.get("labels")
    pairs = rel.get("pairs", [])
    if labels is None or len(pairs) < 1:
        return float("nan")
    c = _lum(captured)
    # Compute mean per label
    label_means = {}
    for p in pairs:
        for lbl in p:
            m = labels == int(lbl)
            if m.any():
                label_means[int(lbl)] = float(c[m].mean())
    passed = 0
    for (a, b) in pairs:
        if a not in label_means or b not in label_means:
            continue
        intra = abs(label_means[a] - label_means[b])
        # inter: distance from a to members of other pairs' closest label
        others = [label_means[l] for l in label_means
                  if l != a and l != b]
        if not others:
            passed += 1
            continue
        inter = min(abs(label_means[a] - o) for o in others)
        if intra <= inter:
            passed += 1
    return float(passed / len(pairs))


def symmetry_survival(truth_pkt, captured):
    """Correlation between captured and its mirror about the declared axis.

    1.0 = perfect symmetry preserved, 0.0 = none.
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "symmetry":
        return float("nan")
    axis = rel.get("axis", "vertical")
    c = _lum(captured)
    if axis == "vertical":
        mirror = c[:, ::-1]
    else:
        mirror = c[::-1, :]
    a = c.flatten().astype(np.float64)
    b = mirror.flatten().astype(np.float64)
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 1.0
    corr = float(np.corrcoef(a, b)[0, 1])
    # Map [-1,1] -> [0,1]
    return float(np.clip((corr + 1.0) / 2.0, 0.0, 1.0))


def _stroke_angle_deg(region):
    """Dominant gradient orientation of a small region in degrees [0,180)."""
    from .simulate import _convolve2d
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = kx.T
    gx = _convolve2d(region, kx)
    gy = _convolve2d(region, ky)
    # For "stroke orientation" we want the axis the stroke runs along,
    # i.e. PERPENDICULAR to the gradient. Average direction via
    # structure-tensor principal axis.
    Jxx = float((gx * gx).sum())
    Jyy = float((gy * gy).sum())
    Jxy = float((gx * gy).sum())
    # Angle of the smallest-eigenvalue eigenvector of [[Jxx,Jxy],[Jxy,Jyy]]
    # which is along the stroke (perpendicular to the gradient).
    theta = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy)  # radians, [-pi/2,pi/2]
    # Stroke direction is perpendicular to that eigenvector direction
    # for the *largest* eigenvalue; our theta above is the angle of the
    # gradient axis (largest eigenvalue). Stroke is perpendicular:
    stroke = theta + np.pi / 2.0
    deg = np.rad2deg(stroke) % 180.0
    return float(deg)


def orientation_survival(truth_pkt, captured, tol_deg=20.0):
    """Fraction of strokes whose measured orientation in the captured
    image is within tol_deg of their declared angle."""
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "orientation":
        return float("nan")
    labels = truth_pkt.get("labels")
    angle_by_label = rel.get("angle_by_label", {})
    if labels is None or not angle_by_label:
        return float("nan")
    c = _lum(captured)
    passed = 0
    total = 0
    for lbl, ang in angle_by_label.items():
        m = labels == int(lbl)
        if not m.any():
            continue
        total += 1
        ys, xs = np.where(m)
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        # pad a little so gradient has context
        pad = 3
        y0p = max(0, y0 - pad); y1p = min(c.shape[0], y1 + pad)
        x0p = max(0, x0 - pad); x1p = min(c.shape[1], x1 + pad)
        region = c[y0p:y1p, x0p:x1p]
        if region.size < 9 or region.std() < 1e-6:
            continue
        meas = _stroke_angle_deg(region)
        target = float(ang) % 180.0
        d = abs(meas - target)
        d = min(d, 180.0 - d)
        if d <= tol_deg:
            passed += 1
    if total == 0:
        return float("nan")
    return float(passed / total)


def hierarchy_survival(truth_pkt, captured):
    """Silhouette-like score: mean intra-group luma distance vs mean
    inter-group luma distance. Returns 1.0 if all inter-group distances
    strictly exceed all intra-group distances, less if they cross.
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "hierarchy":
        return float("nan")
    labels = truth_pkt.get("labels")
    groups = rel.get("groups", {})
    if labels is None or not groups:
        return float("nan")
    c = _lum(captured)
    label_means = {}
    for lbl_str in groups.keys():
        lbl = int(lbl_str)
        m = labels == lbl
        if m.any():
            label_means[lbl] = float(c[m].mean())
    # Build within/between distance sets
    label_group = {int(k): v for k, v in groups.items()}
    within = []
    between = []
    items = list(label_means.items())
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, va = items[i]
            b, vb = items[j]
            d = abs(va - vb)
            if label_group.get(a) == label_group.get(b):
                within.append(d)
            else:
                between.append(d)
    if not within or not between:
        return float("nan")
    # Fraction of (within, between) pairs where within < between
    ok = 0; total = 0
    for w in within:
        for bt in between:
            total += 1
            if w < bt:
                ok += 1
    return float(ok / total)


# Dispatch table
_METRIC_FNS = {
    "ordering":    ordering_survival,
    "adjacency":   adjacency_pair_survival,
    "symmetry":    symmetry_survival,
    "orientation": orientation_survival,
    "hierarchy":   hierarchy_survival,
}


def compute_relation_metrics(truth_pkt, captured):
    """If the truth packet advertises a relation, return a small dict with
    that relation's survival score. Otherwise empty dict."""
    rel = (truth_pkt.get("meta") or {}).get("relation") or {}
    kind = rel.get("kind")
    if kind not in _METRIC_FNS:
        return {}
    fn = _METRIC_FNS[kind]
    try:
        v = fn(truth_pkt, captured)
    except Exception:
        v = float("nan")
    return {"relation_kind": kind, "relation_survival": v}


def relation_report(truth_pkt, params, seed=0):
    """Run the full chain, evaluate the relation metric at every
    intermediate stage, return dict[stage_name -> relation_survival].

    Useful for asking 'at which stage does this relation die?'.
    """
    from .simulate import run_chain
    rel = (truth_pkt.get("meta") or {}).get("relation") or {}
    kind = rel.get("kind")
    if kind not in _METRIC_FNS:
        return {}
    fn = _METRIC_FNS[kind]
    out = {}
    result = run_chain(truth_pkt["image"], params, seed=seed)
    # Evaluate the metric at each intermediate
    for stage_name, stage_img in result["stages"].items():
        try:
            out[stage_name] = float(fn(truth_pkt, stage_img))
        except Exception:
            out[stage_name] = float("nan")
    # And final capture
    out["captured"] = float(fn(truth_pkt, result["captured"]))
    return out


# =========================================================================
# Hard probe variants (v0.4) - tighter geometry / subtler deltas so the
# probes actually fail under moderate stress. These exist specifically to
# avoid the v0.3 "everything stays at 1.0" problem.
# =========================================================================

def ordering_probe_hard(size=256, n=10, axis="horizontal", seed=0):
    """v0.4 hard ordering: more markers (default 10), tighter intensity
    range (0.40..0.70), smaller markers. Rank recovery becomes fragile
    under noise + blur."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(2, size // 60)  # half the v0.3 size
    rank_by_label = {}
    lo, hi = 0.40, 0.70
    for i in range(n):
        frac = (i + 1) / (n + 1)
        intensity = lo + (hi - lo) * (i / max(1, n - 1))
        if axis == "horizontal":
            cx = int(size * frac); cy = size // 2
        else:
            cx = size // 2; cy = int(size * frac)
        yy, xx = np.mgrid[0:size, 0:size]
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = intensity
        lab[m] = i + 1
        rank_by_label[i + 1] = i + 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "ordering_probe_hard", "size": size, "n": n,
            "axis": axis, "seed": seed,
            "relation": {"kind": "ordering", "rank_by_label": rank_by_label},
        },
    }


def adjacency_probe_hard(size=256, n_pairs=6, seed=0):
    """v0.4 hard adjacency: pairs placed close together AND pair intensities
    close to each other, so mild blur merges neighboring pairs into the
    wrong cluster."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(2, size // 70)
    pair_gap = max(2 * r + 1, size // 40)  # very tight
    # Narrow intensity range so pair identities are easier to confuse
    pair_values = np.linspace(0.45, 0.70, n_pairs).astype(np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    cols = max(1, int(np.ceil(np.sqrt(n_pairs))))
    rows = int(np.ceil(n_pairs / cols))
    margin = size // (max(cols, rows) * 2 + 2)
    slot_w = (size - 2 * margin) // cols
    slot_h = (size - 2 * margin) // rows
    label_id = 1
    pairs = []
    for p in range(n_pairs):
        gr = p // cols; gc = p % cols
        cy = margin + slot_h * gr + slot_h // 2
        cx = margin + slot_w * gc + slot_w // 2
        ax = cx - pair_gap // 2
        bx = cx + pair_gap // 2
        mA = (yy - cy) ** 2 + (xx - ax) ** 2 <= r * r
        mB = (yy - cy) ** 2 + (xx - bx) ** 2 <= r * r
        img[mA] = pair_values[p]
        img[mB] = pair_values[p]
        lab[mA] = label_id
        lab[mB] = label_id + 1
        pairs.append((label_id, label_id + 1))
        label_id += 2
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "adjacency_probe_hard", "size": size,
            "n_pairs": n_pairs, "seed": seed,
            "relation": {"kind": "adjacency", "pairs": pairs},
        },
    }


def symmetry_probe_hard(size=256, axis="vertical", seed=0):
    """v0.4 hard symmetry: many small dots (so blur destroys detail) plus
    a thin rotated stripe whose mirror alignment is easily broken by
    rotation / perspective."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    h, w = size, size
    # Dense small dots on left half
    dot_r = max(1, size // 96)
    yy, xx = np.mgrid[0:size, 0:size]
    n_dots = 18
    for k in range(n_dots):
        cy = int(rng.integers(dot_r + 2, size - dot_r - 2))
        # Restrict to left half (so mirroring produces a true partner)
        cx = int(rng.integers(dot_r + 2, w // 2 - dot_r - 2))
        v = float(rng.uniform(0.6, 0.9))
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= dot_r * dot_r
        img[m] = v
    # Mirror across vertical axis (columns) or horizontal axis (rows)
    if axis == "vertical":
        img[:, w // 2:] = img[:, w // 2 - 1::-1][:, :w - w // 2]
    else:
        img[h // 2:, :] = img[h // 2 - 1::-1, :][:h - h // 2, :]
    img += rng.normal(0.0, 0.003, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": None,
        "meta": {
            "kind": "symmetry_probe_hard", "size": size,
            "axis": axis, "seed": seed,
            "relation": {"kind": "symmetry", "axis": axis},
        },
    }


def orientation_probe_hard(size=256, n=4, seed=0):
    """v0.4 hard orientation: near-parallel angles (10, 25, 40, 55 deg)
    instead of cardinal 0/45/90/135. Under blur the structure tensor
    collapses directions together."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    candidate_angles = [10.0, 25.0, 40.0, 55.0, 70.0, 85.0]
    n = min(n, len(candidate_angles))
    angles = candidate_angles[:n]
    stroke_len = max(8, size // 10)
    stroke_w = max(2, size // 80)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    angle_by_label = {}
    for i, ang in enumerate(angles):
        cx = int(size * (i + 1) / (n + 1))
        cy = size // 2
        rad = np.deg2rad(ang)
        ux, uy = np.cos(rad), np.sin(rad)
        vx, vy = -uy, ux
        dx = xx - cx; dy = yy - cy
        proj_u = dx * ux + dy * uy
        proj_v = dx * vx + dy * vy
        mask = (np.abs(proj_u) <= stroke_len / 2.0) & (np.abs(proj_v) <= stroke_w / 2.0)
        img[mask] = 0.9
        lab[mask] = i + 1
        angle_by_label[i + 1] = float(ang)
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "orientation_probe_hard", "size": size,
            "n": n, "seed": seed,
            "relation": {"kind": "orientation", "angle_by_label": angle_by_label},
        },
    }


def hierarchy_probe_hard(size=256, seed=0):
    """v0.4 hard hierarchy: 4 outer groups of 2 inner markers, with the
    outer-group intensities compressed so noise can shuffle groupings.
    Labels 1..8 with groups {1,2}=A, {3,4}=B, {5,6}=C, {7,8}=D."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(2, size // 55)
    yy, xx = np.mgrid[0:size, 0:size]
    # 4 outer group centers arranged in a 2x2 grid; intra-pair members
    # placed within a small offset of the center.
    outer_centers = [
        (int(0.22 * size), int(0.30 * size)),
        (int(0.22 * size), int(0.72 * size)),
        (int(0.78 * size), int(0.30 * size)),
        (int(0.78 * size), int(0.72 * size)),
    ]
    group_values = [0.40, 0.50, 0.60, 0.70]  # tight range
    group_names = ["A", "B", "C", "D"]
    offsets = [(-0.04 * size, 0.0), (+0.04 * size, 0.0)]
    label_id = 1
    groups = {}
    for g, (cx, cy) in enumerate(outer_centers):
        v = group_values[g]
        for dxdy in offsets:
            dcx = int(cx + dxdy[0]); dcy = int(cy + dxdy[1])
            m = (yy - dcy) ** 2 + (xx - dcx) ** 2 <= r * r
            img[m] = v
            lab[m] = label_id
            groups[label_id] = group_names[g]
            label_id += 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {
            "kind": "hierarchy_probe_hard", "size": size, "seed": seed,
            "relation": {"kind": "hierarchy", "groups": groups},
        },
    }


# =========================================================================
# v0.7 - language-relevant primitive probes
#
# These extend the structural starter set with three primitives that
# matter for encoding information visually:
#   repetition (can we still see the period?)
#   cardinality (can we still count?)
#   role/zone  (does the anchor stay distinct from companions?)
# =========================================================================

def repetition_probe(size=256, n=7, seed=0):
    """Evenly spaced markers along a horizontal row. Relation: the period
    between successive markers.
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 48)
    # Fit n markers in a centered band with even spacing
    left = int(size * 0.1); right = int(size * 0.9)
    span = right - left
    period_px = span / max(1, n - 1)
    cy = size // 2
    yy, xx = np.mgrid[0:size, 0:size]
    for i in range(n):
        cx = int(left + i * period_px)
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.85
        lab[m] = i + 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "repetition_probe", "size": size, "n": n,
                 "period_px": float(period_px), "seed": seed,
                 "relation": {"kind": "repetition",
                              "period_px": float(period_px),
                              "row_y": int(cy)}},
    }


def cardinality_probe(size=256, n=5, seed=0):
    """Random placement of n non-overlapping disk markers. Relation: count."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 40)
    pad = r + 2
    placed = []
    attempts = 0
    yy, xx = np.mgrid[0:size, 0:size]
    while len(placed) < n and attempts < 1000:
        attempts += 1
        cy = int(rng.integers(pad, size - pad))
        cx = int(rng.integers(pad, size - pad))
        if any(((cy - py) ** 2 + (cx - px) ** 2) < (2 * r + 4) ** 2
               for (py, px) in placed):
            continue
        placed.append((cy, cx))
    for i, (cy, cx) in enumerate(placed):
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.85
        lab[m] = i + 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "cardinality_probe", "size": size,
                 "n": int(len(placed)), "seed": seed,
                 "relation": {"kind": "cardinality", "count": int(len(placed))}},
    }


def role_zone_probe(size=256, n_secondary=4, seed=0):
    """One bright anchor marker + n_secondary dimmer 'companion' markers.
    Relation: anchor should remain distinctly brighter than companions
    after capture.
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 42)
    # Anchor at center
    cy = size // 2; cx = size // 2
    yy, xx = np.mgrid[0:size, 0:size]
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    img[m] = 0.95
    lab[m] = 1  # anchor label
    # Secondaries around it on a circle
    R = max(r * 4, size // 5)
    for i in range(n_secondary):
        theta = 2.0 * np.pi * i / n_secondary
        sy = int(cy + R * np.sin(theta))
        sx = int(cx + R * np.cos(theta))
        m2 = (yy - sy) ** 2 + (xx - sx) ** 2 <= r * r
        img[m2] = 0.55
        lab[m2] = 2 + i
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "role_zone_probe", "size": size,
                 "n_secondary": int(n_secondary), "seed": seed,
                 "relation": {"kind": "role_zone",
                              "anchor_label": 1,
                              "secondary_labels": list(range(2, 2 + n_secondary))}},
    }


# --- metrics -------------------------------------------------------------

def repetition_survival(truth_pkt, captured):
    """Autocorrelate captured-luma profile along the row. If the peak at
    the expected period is dominant (above neighbors), relation survives.
    Returns [0,1]: peak-at-period / max-peak-in-nontrivial-lags.
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "repetition":
        return float("nan")
    row_y = int(rel.get("row_y", 0))
    period = float(rel.get("period_px", 0.0))
    if period <= 1.0:
        return float("nan")
    c = _lum(captured)
    if row_y < 0 or row_y >= c.shape[0]:
        return float("nan")
    prof = c[row_y].astype(np.float64)
    prof -= prof.mean()
    if prof.std() < 1e-9:
        return 0.0
    # Autocorrelation
    n = prof.size
    ac = np.correlate(prof, prof, mode="full")[n - 1:]
    # Lags 1 .. n//2
    max_lag = n // 2
    if max_lag < 5:
        return float("nan")
    nontrivial = ac[1:max_lag + 1]
    if nontrivial.max() <= 0:
        return 0.0
    nt = nontrivial / nontrivial.max()
    target = int(round(period))
    if target < 1 or target > max_lag:
        return 0.0
    # Score: how close to max the value at target is, averaged over a
    # small window around target to tolerate small shifts.
    lo = max(1, target - 2); hi = min(max_lag, target + 2)
    window_peak = float(nt[lo - 1:hi].max())
    return float(np.clip(window_peak, 0.0, 1.0))


def _count_components(binary: np.ndarray) -> int:
    """4-connected component count via iterative BFS on a numpy mask."""
    h, w = binary.shape
    visited = np.zeros_like(binary, dtype=bool)
    count = 0
    for i in range(h):
        for j in range(w):
            if binary[i, j] and not visited[i, j]:
                count += 1
                stack = [(i, j)]
                while stack:
                    y, x = stack.pop()
                    if y < 0 or y >= h or x < 0 or x >= w:
                        continue
                    if visited[y, x] or not binary[y, x]:
                        continue
                    visited[y, x] = True
                    stack.append((y - 1, x))
                    stack.append((y + 1, x))
                    stack.append((y, x - 1))
                    stack.append((y, x + 1))
    return count


def cardinality_survival(truth_pkt, captured):
    """Count connected components in the captured image above a threshold
    relative to the background. Compare to truth count.
    Score = max(0, 1 - |detected - n|/n).
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "cardinality":
        return float("nan")
    n = int(rel.get("count", 0))
    if n <= 0:
        return float("nan")
    c = _lum(captured)
    # threshold: mean + 2*std, clamped so tiny signals still count
    thr = float(c.mean() + 2.0 * c.std())
    binary = c > max(thr, float(c.mean()) + 0.15)
    detected = _count_components(binary)
    err = abs(detected - n) / float(n)
    return float(max(0.0, 1.0 - err))


def role_zone_survival(truth_pkt, captured):
    """Anchor stays distinctly brighter than the companions.
    Score = 1.0 if anchor mean exceeds ALL secondary means by at least
    0.05; partial credit for fewer.
    """
    rel = truth_pkt["meta"].get("relation", {})
    if rel.get("kind") != "role_zone":
        return float("nan")
    labels = truth_pkt.get("labels")
    if labels is None:
        return float("nan")
    c = _lum(captured)
    anchor_lbl = int(rel.get("anchor_label", 1))
    sec_lbls = [int(x) for x in rel.get("secondary_labels", [])]
    am = labels == anchor_lbl
    if not am.any() or not sec_lbls:
        return float("nan")
    anchor_mean = float(c[am].mean())
    ok = 0
    for l in sec_lbls:
        sm = labels == l
        if not sm.any():
            continue
        if (anchor_mean - float(c[sm].mean())) >= 0.05:
            ok += 1
    return float(ok / len(sec_lbls))


# Extend dispatcher
_METRIC_FNS["repetition"]  = repetition_survival
_METRIC_FNS["cardinality"] = cardinality_survival
_METRIC_FNS["role_zone"]   = role_zone_survival


# =========================================================================
# v0.8 - anti-triviality: harder variants of promoted primitives +
# negative-control probes
#
# Rationale: three v0.7 primitives (ordering, repetition, role_zone) came
# back STABLE_ROBUST across all five scenarios. That might be genuine,
# but it might also be that the probe or metric is too forgiving.
# v0.8 introduces (a) harder variants that risk failure, and (b)
# negative-control probes that *should* score low if the metric is
# meaningful. A metric that happily passes a negative control is
# instantly suspect.
# =========================================================================

def role_zone_probe_hard(size=256, n_secondary=6, seed=0):
    """Anchor-vs-companions but with tight intensity contrast (0.60 vs
    0.50) and smaller markers. Under moderate blur + noise the tight
    margin should degrade."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(2, size // 64)  # half as big as easy
    cy = size // 2; cx = size // 2
    yy, xx = np.mgrid[0:size, 0:size]
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    img[m] = 0.60            # tight contrast
    lab[m] = 1
    R = max(r * 4, size // 6)
    for i in range(n_secondary):
        theta = 2.0 * np.pi * i / n_secondary
        sy = int(cy + R * np.sin(theta))
        sx = int(cx + R * np.cos(theta))
        m2 = (yy - sy) ** 2 + (xx - sx) ** 2 <= r * r
        img[m2] = 0.50
        lab[m2] = 2 + i
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "role_zone_probe_hard", "size": size,
                 "n_secondary": int(n_secondary), "seed": seed,
                 "relation": {"kind": "role_zone",
                              "anchor_label": 1,
                              "secondary_labels": list(range(2, 2 + n_secondary))}},
    }


def repetition_probe_hard(size=256, n=12, seed=0):
    """Twice as many markers (tighter period) with smaller radii. The
    resulting period sits closer to Nyquist of common PSF blurs."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(2, size // 72)
    left = int(size * 0.06); right = int(size * 0.94)
    span = right - left
    period_px = span / max(1, n - 1)
    cy = size // 2
    yy, xx = np.mgrid[0:size, 0:size]
    for i in range(n):
        cx = int(left + i * period_px)
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.85
        lab[m] = i + 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "repetition_probe_hard", "size": size, "n": n,
                 "period_px": float(period_px), "seed": seed,
                 "relation": {"kind": "repetition",
                              "period_px": float(period_px),
                              "row_y": int(cy)}},
    }


# --- Negative controls ---------------------------------------------------
# These advertise a relation_kind but are constructed so that, if the
# metric is meaningful, the score should be low. A metric that scores
# them high is broken or trivial.

def null_relation_probe(size=256, relation_kind="ordering", seed=0):
    """Empty/uniform image labeled with a claimed relation.
    Expected score: low (the relation doesn't exist in the image)."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.5, dtype=np.float32)
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    meta = {"kind": "null_relation_probe", "size": size, "seed": seed}
    if relation_kind == "ordering":
        # Fake ordering: same intensity everywhere -> no rank can be recovered
        lab = np.zeros((size, size), dtype=np.int32)
        n = 5
        r = max(3, size // 40)
        yy, xx = np.mgrid[0:size, 0:size]
        rank_by_label = {}
        for i in range(n):
            cx = int(size * (i + 1) / (n + 1)); cy = size // 2
            m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
            img[m] = 0.5   # all same
            lab[m] = i + 1
            rank_by_label[i + 1] = i + 1
        meta["relation"] = {"kind": "ordering",
                            "rank_by_label": rank_by_label}
    elif relation_kind == "repetition":
        # Claim a period but the image is uniform -> no periodic signal
        meta["relation"] = {"kind": "repetition",
                            "period_px": float(size // 8),
                            "row_y": int(size // 2)}
        lab = None
    elif relation_kind == "role_zone":
        lab = np.zeros((size, size), dtype=np.int32)
        r = max(3, size // 42); cy = size // 2; cx = size // 2
        yy, xx = np.mgrid[0:size, 0:size]
        # All markers at the same intensity -> anchor is not distinct
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.6; lab[m] = 1
        R = max(r * 4, size // 5)
        for i in range(4):
            theta = 2.0 * np.pi * i / 4
            sy = int(cy + R * np.sin(theta))
            sx = int(cx + R * np.cos(theta))
            m2 = (yy - sy) ** 2 + (xx - sx) ** 2 <= r * r
            img[m2] = 0.6  # same as anchor
            lab[m2] = 2 + i
        meta["relation"] = {"kind": "role_zone",
                            "anchor_label": 1,
                            "secondary_labels": [2, 3, 4, 5]}
    else:
        lab = None
    return {"image": img, "labels": lab, "meta": meta}


def scrambled_ordering_probe(size=256, n=6, seed=0):
    """Like ordering_probe but label-vs-intensity mapping is shuffled, so
    captured-mean ordering will NOT match label-rank ordering. Expected
    Spearman score: ~0.5 (random).
    """
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.1, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(4, size // 40)
    # Keep the label rank -> 1..n ascending, but shuffle intensity assignment
    intensities = np.linspace(0.2, 0.95, n).astype(np.float32)
    perm = rng.permutation(n)
    shuffled = intensities[perm]
    rank_by_label = {}
    yy, xx = np.mgrid[0:size, 0:size]
    for i in range(n):
        frac = (i + 1) / (n + 1)
        cx = int(size * frac); cy = size // 2
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = shuffled[i]
        lab[m] = i + 1
        rank_by_label[i + 1] = i + 1   # claim monotone rank
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "scrambled_ordering_probe", "size": size,
                 "n": n, "seed": seed,
                 "relation": {"kind": "ordering", "rank_by_label": rank_by_label}},
    }


def non_repetition_probe(size=256, n=7, seed=0):
    """Markers placed at RANDOM (non-periodic) offsets but labelled with
    a claimed period. Autocorrelation at that period should be weak."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 48)
    cy = size // 2
    # Random x positions (jittered enough to break any period)
    xs = sorted(rng.integers(int(size * 0.08), int(size * 0.92), size=n).tolist())
    yy, xx = np.mgrid[0:size, 0:size]
    for i, cx in enumerate(xs):
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
        img[m] = 0.85
        lab[m] = i + 1
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    claimed_period = float((size * 0.8) / max(1, n - 1))
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "non_repetition_probe", "size": size, "n": n,
                 "claimed_period_px": claimed_period, "seed": seed,
                 "relation": {"kind": "repetition",
                              "period_px": claimed_period,
                              "row_y": int(cy)}},
    }


def equalized_role_zone_probe(size=256, n_secondary=4, seed=0):
    """All markers at the same intensity, but labels advertise an
    anchor. Expected role_zone score: 0.0."""
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.15, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(3, size // 42)
    cy = size // 2; cx = size // 2
    yy, xx = np.mgrid[0:size, 0:size]
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    img[m] = 0.7; lab[m] = 1
    R = max(r * 4, size // 5)
    for i in range(n_secondary):
        theta = 2.0 * np.pi * i / n_secondary
        sy = int(cy + R * np.sin(theta))
        sx = int(cx + R * np.cos(theta))
        m2 = (yy - sy) ** 2 + (xx - sx) ** 2 <= r * r
        img[m2] = 0.7   # SAME as anchor
        lab[m2] = 2 + i
    img += rng.normal(0.0, 0.005, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {
        "image": img, "labels": lab,
        "meta": {"kind": "equalized_role_zone_probe", "size": size,
                 "n_secondary": int(n_secondary), "seed": seed,
                 "relation": {"kind": "role_zone",
                              "anchor_label": 1,
                              "secondary_labels": list(range(2, 2 + n_secondary))}},
    }
