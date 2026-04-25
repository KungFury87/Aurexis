"""Sensor-path smoke tests (v0.2).

Run:

    python -m pytest tests -q
"""
from __future__ import annotations

import numpy as np

from aurexis_sim import truth as truth_mod
from aurexis_sim import metrics as metrics_mod
from aurexis_sim.simulate import SimParams, run_chain
from aurexis_sim.sensor import (
    SensorParams, BAYER_PATTERNS,
    bayer_mosaic, demosaic_bilinear, _cfa_masks,
)
from aurexis_sim.color import (
    is_rgb, promote_to_rgb, luma, rgb_blocks, color_relation_probe, color_bars,
)
from aurexis_sim.presets import preset_from_ui, params_from_preset


# ---- color / promote ----------------------------------------------------

def test_promote_gray_to_rgb():
    g = np.linspace(0, 1, 64 * 64, dtype=np.float32).reshape(64, 64)
    r = promote_to_rgb(g)
    assert r.shape == (64, 64, 3)
    assert np.allclose(r[..., 0], r[..., 1])
    assert np.allclose(r[..., 1], r[..., 2])


def test_luma_rgb_channels():
    img = np.zeros((8, 8, 3), dtype=np.float32)
    img[..., 1] = 1.0
    l = luma(img)
    # Rec.709 green coefficient is ~0.7152
    assert abs(l.mean() - 0.7152) < 1e-4


# ---- CFA masks are disjoint & cover everything --------------------------

def test_cfa_masks_disjoint_and_complete():
    for pat in BAYER_PATTERNS:
        mR, mG, mB = _cfa_masks((16, 16), pat)
        # Disjoint
        assert not np.any(mR & mG)
        assert not np.any(mG & mB)
        assert not np.any(mR & mB)
        # Complete coverage
        assert np.all(mR | mG | mB)
        # Density: G should be half, R and B should be quarter each
        assert mR.sum() == 16 * 16 // 4
        assert mB.sum() == 16 * 16 // 4
        assert mG.sum() == 16 * 16 // 2


# ---- mosaic + demosaic round-trip --------------------------------------

def test_mosaic_demosaic_roundtrip_uniform():
    """On a uniform-color RGB field, demosaic should recover it exactly."""
    img = np.zeros((32, 32, 3), dtype=np.float32)
    img[..., 0] = 0.3; img[..., 1] = 0.6; img[..., 2] = 0.9
    mos = bayer_mosaic(img, "RGGB")
    out = demosaic_bilinear(mos, "RGGB")
    # Allow small edge-effects near borders; check center region
    center = out[4:-4, 4:-4, :]
    assert np.allclose(center[..., 0], 0.3, atol=0.02)
    assert np.allclose(center[..., 1], 0.6, atol=0.02)
    assert np.allclose(center[..., 2], 0.9, atol=0.02)


def test_demosaic_output_shape_and_range():
    img = rgb_blocks(size=32, n=4, seed=1)["image"]
    mos = bayer_mosaic(img, "RGGB")
    out = demosaic_bilinear(mos, "RGGB")
    assert out.shape == img.shape
    assert 0.0 <= out.min() and out.max() <= 1.0


# ---- full chain with sensor path ---------------------------------------

def test_chain_sensor_enabled_returns_rgb():
    pkt = rgb_blocks(size=64, n=4, seed=0)
    sp = SimParams(sensor=SensorParams(enabled=True, pattern="RGGB"))
    result = run_chain(pkt["image"], sp, seed=0)
    cap = result["captured"]
    assert is_rgb(cap)
    # Sensor intermediates must be present
    for k in ("sensor_pre_cfa", "sensor_mosaic", "sensor_mosaic_noisy", "sensor_demosaiced"):
        assert k in result["stages"], f"missing stage {k}"


def test_chain_sensor_disabled_on_grayscale_stays_gray():
    pkt = truth_mod.generate("blocks", size=64, n=4, seed=0)
    result = run_chain(pkt["image"], SimParams(), seed=0)
    assert result["captured"].ndim == 2


def test_sensor_clean_is_near_identity_on_rgb_blocks():
    pkt = rgb_blocks(size=64, n=4, seed=0)
    sp = SimParams(sensor=SensorParams(enabled=True, pattern="RGGB"))
    result = run_chain(pkt["image"], sp, seed=0)
    m = metrics_mod.compute_all(pkt, result["captured"])
    # CFA + demosaic never gets perfect recovery due to interpolation,
    # but clean path should still be high quality on block patterns.
    assert m["psnr_db"] > 20.0
    # Per-channel PSNRs should be finite
    assert m["psnr_r_db"] > 15.0
    assert m["psnr_g_db"] > 15.0
    assert m["psnr_b_db"] > 15.0


def test_sensor_noise_degrades_vs_clean():
    pkt = rgb_blocks(size=64, n=4, seed=0)
    sp_clean = SimParams(sensor=SensorParams(enabled=True))
    sp_noisy = SimParams(sensor=SensorParams(
        enabled=True, noise_r=0.04, noise_g=0.02, noise_b=0.04,
    ))
    m_clean = metrics_mod.compute_all(pkt, run_chain(pkt["image"], sp_clean, 0)["captured"])
    m_noisy = metrics_mod.compute_all(pkt, run_chain(pkt["image"], sp_noisy, 0)["captured"])
    assert m_noisy["psnr_db"] < m_clean["psnr_db"]
    assert m_noisy["chroma_error"] >= m_clean["chroma_error"]


def test_chroma_error_detects_color_loss():
    """A grayscale demosaic result should have no chroma error; a mangled
    RGB capture should have some."""
    img = color_bars(size=64)["image"]
    # "identity" RGB capture -> chroma_error == 0
    assert metrics_mod.chroma_error(img, img) < 1e-6
    # Mangled: desaturate captured
    cap = np.broadcast_to(luma(img)[..., None], img.shape).astype(np.float32)
    assert metrics_mod.chroma_error(img, cap) > 0.05


# ---- preset round-trip includes nested SensorParams --------------------

def test_preset_roundtrip_with_sensor(tmp_path):
    from aurexis_sim.presets import save_preset, load_preset
    sp = SimParams(sensor=SensorParams(
        enabled=True, pattern="RGGB",
        blur_sigma_g=0.5, noise_r=0.02,
    ))
    preset = preset_from_ui("sensor_rt", "rgb_blocks",
                            {"size": 32, "n": 4, "seed": 0}, sp, 0)
    save_preset(preset, "sensor_rt", presets_dir=tmp_path)
    loaded = load_preset("sensor_rt", presets_dir=tmp_path)
    p2 = params_from_preset(loaded)
    assert p2.sensor.enabled is True
    assert p2.sensor.pattern == "RGGB"
    assert abs(p2.sensor.blur_sigma_g - 0.5) < 1e-9
    assert abs(p2.sensor.noise_r - 0.02) < 1e-9


# ---- existing grayscale contract is not broken -------------------------

def test_grayscale_path_unchanged():
    pkt = truth_mod.generate("blocks", size=64, n=4, seed=0)
    result = run_chain(pkt["image"], SimParams(), seed=0)
    m = metrics_mod.compute_all(pkt, result["captured"])
    # Identity-ish: v0.1 guarantee still holds
    assert m["psnr_db"] > 40.0
    assert m["ssim_simple"] > 0.95
