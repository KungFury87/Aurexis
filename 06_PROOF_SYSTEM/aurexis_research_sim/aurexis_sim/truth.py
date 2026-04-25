"""Truth plane generators.

Each generator returns a dict:
    {
        "image":   float32 HxW (grayscale) or HxWx3 (RGB) in [0,1],
        "labels":  optional int32 HxW label map (or None),
        "meta":    dict of params that produced it,
    }
"""
from __future__ import annotations

from typing import Callable

import numpy as np

PatternFn = Callable[..., dict]


def blocks(size=256, n=8, seed=0):
    rng = np.random.default_rng(seed)
    side = size // n
    img = np.zeros((size, size), dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    vals = rng.uniform(0.1, 0.9, size=(n, n)).astype(np.float32)
    k = 0
    for i in range(n):
        for j in range(n):
            y0, y1 = i*side, (i+1)*side
            x0, x1 = j*side, (j+1)*side
            img[y0:y1, x0:x1] = vals[i, j]
            lab[y0:y1, x0:x1] = k
            k += 1
    return {"image": img, "labels": lab, "meta": {"kind": "blocks", "size": size, "n": n, "seed": seed}}


def grid(size=256, cell=16, line=1):
    img = np.ones((size, size), dtype=np.float32)
    for y in range(0, size, cell):
        img[y:y+line, :] = 0.0
    for x in range(0, size, cell):
        img[:, x:x+line] = 0.0
    return {"image": img, "labels": None, "meta": {"kind": "grid", "size": size, "cell": cell, "line": line}}


def edges(size=256):
    img = np.zeros((size, size), dtype=np.float32)
    img[:, size//4:] = 1.0
    yy, xx = np.mgrid[0:size, 0:size]
    img[(yy + xx) > (size * 1.25)] = 0.5
    img[int(size*0.7):int(size*0.8), :] = 0.8
    return {"image": img, "labels": None, "meta": {"kind": "edges", "size": size}}


def fiducial(size=256):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    cy, cx = size/2, size/2
    r = np.sqrt((yy - cy)**2 + (xx - cx)**2)
    img = 0.5 + 0.5 * np.sin(r / 4.0)
    arm = size // 32
    img[int(cy-arm):int(cy+arm), :] = 1.0
    img[:, int(cx-arm):int(cx+arm)] = 1.0
    b = size // 20
    img[:b, :] = 0.0; img[-b:, :] = 0.0
    img[:, :b] = 0.0; img[:, -b:] = 0.0
    return {"image": img.astype(np.float32), "labels": None, "meta": {"kind": "fiducial", "size": size}}


def gradient(size=256, axis="x"):
    x = np.linspace(0.0, 1.0, size, dtype=np.float32)
    if axis == "x":
        img = np.tile(x, (size, 1))
    elif axis == "y":
        img = np.tile(x[:, None], (1, size))
    else:
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        cy, cx = size/2, size/2
        img = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        img = img / img.max()
    return {"image": img.astype(np.float32), "labels": None, "meta": {"kind": "gradient", "size": size, "axis": axis}}


def relation_probe(size=256, seed=0):
    rng = np.random.default_rng(seed)
    img = np.full((size, size), 0.2, dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    r = max(4, size // 40)
    markers = [
        (int(size*0.25), int(size*0.5), 1, 0.9),
        (int(size*0.45), int(size*0.5), 2, 0.9),
        (int(size*0.75), int(size*0.3), 3, 0.9),
        (int(size*0.75), int(size*0.7), 4, 0.9),
    ]
    yy, xx = np.mgrid[0:size, 0:size]
    for (cx, cy, idx, val) in markers:
        m = (yy - cy)**2 + (xx - cx)**2 <= r*r
        img[m] = val
        lab[m] = idx
    img += rng.normal(0.0, 0.01, img.shape).astype(np.float32)
    img = np.clip(img, 0.0, 1.0)
    return {"image": img, "labels": lab, "meta": {"kind": "relation_probe", "size": size, "seed": seed}}


def phoxel_probe(size=256, cell=8, seed=0):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size), dtype=np.float32)
    lab = np.zeros((size, size), dtype=np.int32)
    levels = np.array([0.15, 0.40, 0.65, 0.90], dtype=np.float32)
    idx = 0
    for i in range(0, size, cell):
        for j in range(0, size, cell):
            v = levels[rng.integers(0, len(levels))]
            img[i:i+cell, j:j+cell] = v
            lab[i:i+cell, j:j+cell] = idx
            idx += 1
    return {"image": img, "labels": lab, "meta": {"kind": "phoxel_probe", "size": size, "cell": cell, "seed": seed}}


from . import color as _color_mod
from . import relations as _rel_mod

REGISTRY = {
    "blocks": blocks,
    "grid": grid,
    "edges": edges,
    "fiducial": fiducial,
    "gradient": gradient,
    "relation_probe": relation_probe,
    "phoxel_probe": phoxel_probe,
    "rgb_blocks": _color_mod.rgb_blocks,
    "color_relation_probe": _color_mod.color_relation_probe,
    "color_bars": _color_mod.color_bars,
    # v0.3 relation-primitive probes
    "ordering_probe": _rel_mod.ordering_probe,
    "adjacency_probe": _rel_mod.adjacency_probe,
    "symmetry_probe": _rel_mod.symmetry_probe,
    "orientation_probe": _rel_mod.orientation_probe,
    "hierarchy_probe": _rel_mod.hierarchy_probe,
    # v0.4 hard probe variants - designed to fail under moderate stress
    "ordering_probe_hard":    _rel_mod.ordering_probe_hard,
    "adjacency_probe_hard":   _rel_mod.adjacency_probe_hard,
    "symmetry_probe_hard":    _rel_mod.symmetry_probe_hard,
    "orientation_probe_hard": _rel_mod.orientation_probe_hard,
    "hierarchy_probe_hard":   _rel_mod.hierarchy_probe_hard,
    # v0.7 language-relevant primitive probes
    "repetition_probe":       _rel_mod.repetition_probe,
    "cardinality_probe":      _rel_mod.cardinality_probe,
    "role_zone_probe":        _rel_mod.role_zone_probe,
    # v0.8 hard variants of promoted primitives
    "role_zone_probe_hard":   _rel_mod.role_zone_probe_hard,
    "repetition_probe_hard":  _rel_mod.repetition_probe_hard,
    # v0.8 negative controls (should score low if metric is meaningful)
    "null_relation_probe":        _rel_mod.null_relation_probe,
    "scrambled_ordering_probe":   _rel_mod.scrambled_ordering_probe,
    "non_repetition_probe":       _rel_mod.non_repetition_probe,
    "equalized_role_zone_probe":  _rel_mod.equalized_role_zone_probe,
}

# v1.0 composite probes are registered by aurexis_sim.interaction
# when it is imported (handles circular import cleanly).



def generate(kind, **kwargs):
    if kind not in REGISTRY:
        raise KeyError("Unknown truth pattern " + repr(kind))
    return REGISTRY[kind](**kwargs)


def list_kinds():
    return list(REGISTRY.keys())
