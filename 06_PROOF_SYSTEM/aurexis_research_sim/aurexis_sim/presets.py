"""Preset + run-log I/O. Presets are JSON files.

Schema:
{
  "name":   str,
  "truth":  { "kind": str, "kwargs": dict },
  "params": dict  (SimParams fields, incl. nested 'sensor' dict),
  "seed":   int
}
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .simulate import SimParams
from .sensor import SensorParams
from .utils import save_png
from .color import is_rgb, luma


DEFAULT_PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"
DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def list_presets(presets_dir=None):
    d = Path(presets_dir or DEFAULT_PRESETS_DIR)
    if not d.exists():
        return []
    return sorted([p.stem for p in d.glob("*.json")])


def load_preset(name, presets_dir=None):
    d = Path(presets_dir or DEFAULT_PRESETS_DIR)
    p = d / (name + ".json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_preset(preset, name, presets_dir=None):
    d = Path(presets_dir or DEFAULT_PRESETS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    p = d / (name + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(preset, f, indent=2)
    return p


def preset_from_ui(name, truth_kind, truth_kwargs, params, seed):
    return {
        "name": name,
        "truth": {"kind": truth_kind, "kwargs": truth_kwargs},
        "params": asdict(params),
        "seed": int(seed),
    }


def params_from_preset(preset):
    pdict = dict(preset["params"])
    sensor_dict = pdict.pop("sensor", None)
    sp = SensorParams(**sensor_dict) if sensor_dict is not None else SensorParams()
    return SimParams(sensor=sp, **pdict)


def log_run(preset, truth_img, captured, metrics,
            corruption_map=None, runs_dir=None):
    d = Path(runs_dir or DEFAULT_RUNS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    run_dir = d / (ts + "_" + preset.get("name", "run"))
    run_dir.mkdir(parents=True, exist_ok=True)

    with open(run_dir / "preset.json", "w", encoding="utf-8") as f:
        json.dump(preset, f, indent=2)
    with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
        safe = {k: (None if isinstance(v, float) and (v != v) else v)
                for k, v in metrics.items()}
        json.dump(safe, f, indent=2)

    save_png(run_dir / "truth.png", truth_img)
    save_png(run_dir / "captured.png", captured)

    t_l = luma(truth_img) if is_rgb(truth_img) else truth_img.astype(np.float32)
    c_l = luma(captured) if is_rgb(captured) else captured.astype(np.float32)
    diff = np.abs(t_l - c_l)
    dm = float(diff.max()) or 1.0
    save_png(run_dir / "diff.png", diff / dm)
    if corruption_map is not None:
        save_png(run_dir / "corruption.png", corruption_map)

    return run_dir
