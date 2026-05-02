"""R181: engineer stimuli to satisfy strict thresholds for the last 6 dead.

Computes operator outputs first, then searches for stimuli that hit target ranges.
"""
import warnings; warnings.filterwarnings('ignore')
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops, fields as F
from aurexis_workbench.fields import FieldBundle
from aurexis_workbench.vision_ops import (
    _row_autocorr_peak, _high_frequency_residual, _edge_density,
    _dynamic_range, _green_imbalance, _channel_spread_norm,
    _bayer_R, _block_avg_2x2, _fft_peak_to_floor, _rotated_pair_anisotropy,
    _text_likeness_score, _screen_likeness_score, _face_likeness_score,
)

for t in ("raw_bayer",):
    F.VALID_DTYPES = F.VALID_DTYPES | {t}

vision_ops.register_all()
text = (ROOT/'data'/'vision'/'vocab.aurex').read_text()
runtime = Runtime()
for pp in dsl.parse_source(text):
    if pp.ok:
        try: P.type_check(pp.pred); runtime.install(pp.pred)
        except: pass
pred_names = sorted(runtime.installed())

def measure_screen_like_inputs(scene, label=""):
    """Print the 4 components for screen+text scores."""
    h, w = scene.shape
    row_y = h // 2
    autocorr = _row_autocorr_peak(scene, row_y)
    hfr = _high_frequency_residual(scene)
    edens = _edge_density(scene, 1.0)
    dynr = _dynamic_range(scene)
    text = _text_likeness_score(scene, row_y)
    screen = _screen_likeness_score(scene, row_y)
    print(f"  {label:30s} autocorr={autocorr:.3f} hfr={hfr:.3f} edens={edens:.3f} dynr={dynr:.3f} text_score={text:.3f} screen_score={screen:.3f}")
    return text, screen

stimuli = {}

# ---------------------------------------------------------------------------
# Engineering pass 1: search for SCREEN+TEXT composite that fires both at >=0.60
# Strategy: horizontal stripes of various pixel widths, with different
# duty cycles, to find the ones that hit (text, screen) both >= 0.60 with margin.
# ---------------------------------------------------------------------------
print("\nSearching for screen+text composite stimulus...")
H, W = 240, 320

best_combo = None
for stripe_period in [3, 4, 5, 6, 8, 10]:
    for duty in [0.3, 0.4, 0.5]:
        scene = np.ones((H, W))
        on_h = max(1, int(stripe_period * duty))
        for y in range(0, H, stripe_period):
            scene[y:y+on_h, :] = 0.0
        # add a small uniform region top/bottom to vary dynamic range
        text, screen = measure_screen_like_inputs(scene, f"stripes p={stripe_period} d={duty:.1f}")
        if text >= 0.60 and screen >= 0.60 and abs(text - screen) < 0.05:
            best_combo = (stripe_period, duty, scene.copy(), text, screen)
            break
    if best_combo: break

# If we don't find a perfect combo, try gradient + stripes
if best_combo is None:
    for stripe_period in [4, 6]:
        scene = np.linspace(0, 1, W)[None, :].repeat(H, axis=0)  # gradient
        for y in range(0, H, stripe_period):
            scene[y, :] *= 0.3  # darken every Nth row
        text, screen = measure_screen_like_inputs(scene, f"grad+stripes p={stripe_period}")
        if text >= 0.60 and screen >= 0.60 and abs(text - screen) < 0.05:
            best_combo = (stripe_period, None, scene.copy(), text, screen)
            break

if best_combo:
    sp, duty, scene, t_score, s_score = best_combo
    print(f"\n  → BEST: period={sp} duty={duty} text={t_score:.3f} screen={s_score:.3f}")

# Let's also pick a few candidates that hit just one of them strictly,
# and a candidate for screen-displaying-text/face composites.
# ---------------------------------------------------------------------------
# Stim 1: pure horizontal stripes — should fire has_screen_like_signature
def make_stripes(period, duty, h=240, w=320):
    scene = np.ones((h, w))
    on_h = max(1, int(period * duty))
    for y in range(0, h, period):
        scene[y:y+on_h, :] = 0.0
    return scene

# Stim 1: wide stripes for screen_like
scene1 = make_stripes(6, 0.5)
measure_screen_like_inputs(scene1, "s1_period6")
stimuli['s1_screen_period6'] = scene1

scene2 = make_stripes(4, 0.5)
measure_screen_like_inputs(scene2, "s2_period4")
stimuli['s2_screen_period4'] = scene2

scene3 = make_stripes(8, 0.5)
measure_screen_like_inputs(scene3, "s3_period8")
stimuli['s3_screen_period8'] = scene3

# Stim 4: mixed pattern - stripes with overlaid face features for screen_displaying_face
scene4 = make_stripes(6, 0.5, h=H, w=W).copy()
# overlay a face-like circular region in middle: brightens it
y_idx, x_idx = np.mgrid[:H, :W]
face_mask = (y_idx - H/2)**2 + (x_idx - W/2)**2 < (H/3)**2
# Add a face-mirror-symmetric pattern by averaging stripe scene with its horizontal flip
scene4_face = (scene4 + scene4[:, ::-1]) / 2  # boosts mirror correlation
# Add a centered concentration
g = np.exp(-((y_idx - H/2)**2 + (x_idx - W/2)**2) / (2 * (H/4)**2))
scene4 = scene4_face * (1 - 0.3*g) + 0.5 * g  # centered brightening
measure_screen_like_inputs(scene4, "s4_mirror_stripes")
stimuli['s4_screen_with_face'] = scene4

# Stim 5: tighter stripes with text-like characteristics  
def make_text_pattern(h=240, w=320):
    """Horizontal text-like rows: dark blocks at irregular positions."""
    scene = np.full((h, w), 0.95)
    rng = np.random.default_rng(181)
    for line_y in range(8, h-8, 12):  # text lines every 12 rows
        x = 10
        while x < w - 20:
            char_w = int(rng.integers(4, 10))
            scene[line_y:line_y+5, x:x+char_w] = 0.05
            x += char_w + int(rng.integers(2, 5))
    return scene

scene5 = make_text_pattern()
measure_screen_like_inputs(scene5, "s5_text_pattern")
stimuli['s5_text_pattern'] = scene5

# Stim 6: stripes mixed with text-pattern overlay - for screen_displaying_text
scene6_screen = make_stripes(4, 0.5)
scene6_text = make_text_pattern()
scene6 = 0.5 * scene6_screen + 0.5 * scene6_text  # blend
measure_screen_like_inputs(scene6, "s6_mixed_screen_text")
stimuli['s6_screen_displaying_text'] = scene6

# ---------------------------------------------------------------------------
# Bayer engineering: has_subpixel_periodicity + has_spectral_band_anomaly
# ---------------------------------------------------------------------------
print("\nBayer engineering...")

# has_spectral_band_anomaly: green_imbalance > 0.02 OR channel_spread_norm > 0.05
# Make a flat Bayer with strong G1≠G2 difference
def make_bayer_anomaly(h=240, w=320, gr=0.6, gb=0.4, r=0.5, b=0.5):
    bayer = np.zeros((h, w))
    bayer[0::2, 0::2] = r
    bayer[0::2, 1::2] = gr
    bayer[1::2, 0::2] = gb
    bayer[1::2, 1::2] = b
    return bayer

bayer1 = make_bayer_anomaly(gr=0.7, gb=0.3, r=0.5, b=0.5)
gi = _green_imbalance(bayer1)
csn = _channel_spread_norm(bayer1)
print(f"  bayer_g1_07_g2_03: green_imbalance={gi:.3f} channel_spread_norm={csn:.3f}")
stimuli['s7_bayer_anomaly'] = bayer1

# has_subpixel_periodicity: gt(fft_peak_to_floor(bayer_R), 5.0)
# AND gt(div_s(fft_peak_to_floor(bayer_R), fft_peak_to_floor(block_avg_2x2)), 1.6)
# Need bayer_R (sampled at even rows/cols) to have above-Nyquist content
def make_bayer_subpixel(h=240, w=320):
    """Bayer pattern where R-channel has strong periodic pattern that
    block_avg_2x2 does NOT see (above Nyquist of 2x2 averaging)."""
    bayer = np.zeros((h, w))
    y, x = np.mgrid[:h, :w]
    # Period exactly 2 pixels in R-pattern: strong in bayer_R[i,j] but
    # gets averaged out by block_avg_2x2
    # Actually bayer_R is at [0::2, 0::2] - those are spaced 2px apart.
    # If we make bayer[0::2, 0::2] alternate strongly, that's period 2 in
    # the SAMPLED R-channel = above Nyquist of full 2x2 averaging.
    rch = np.zeros((h//2, w//2))
    # Make rch alternate
    rch[:, 0::2] = 0.9
    rch[:, 1::2] = 0.1
    bayer[0::2, 0::2] = rch
    # Other channels are flat-ish to NOT add their own peak
    bayer[0::2, 1::2] = 0.5
    bayer[1::2, 0::2] = 0.5
    bayer[1::2, 1::2] = 0.5
    return bayer

bayer2 = make_bayer_subpixel()
fft_R = _fft_peak_to_floor(_bayer_R(bayer2))
fft_block = _fft_peak_to_floor(_block_avg_2x2(bayer2))
print(f"  bayer_subpixel: fft_R={fft_R:.2f} fft_block_avg={fft_block:.2f} ratio={fft_R/(fft_block+1e-9):.2f}")
stimuli['s8_bayer_subpixel'] = bayer2

# Stronger subpixel: combine the alternation across rows too
def make_bayer_subpixel_strong(h=240, w=320):
    bayer = np.zeros((h, w))
    rch = np.zeros((h//2, w//2))
    yy, xx = np.mgrid[:h//2, :w//2]
    rch = 0.5 + 0.45 * np.cos(np.pi * xx) * np.cos(np.pi * yy)  # strong alternation
    bayer[0::2, 0::2] = rch
    bayer[0::2, 1::2] = 0.5
    bayer[1::2, 0::2] = 0.5
    bayer[1::2, 1::2] = 0.5
    return bayer

bayer3 = make_bayer_subpixel_strong()
fft_R3 = _fft_peak_to_floor(_bayer_R(bayer3))
fft_block3 = _fft_peak_to_floor(_block_avg_2x2(bayer3))
print(f"  bayer_subpixel_strong: fft_R={fft_R3:.2f} fft_block_avg={fft_block3:.2f} ratio={fft_R3/(fft_block3+1e-9):.2f}")
stimuli['s9_bayer_subpixel_strong'] = bayer3

# ---------------------------------------------------------------------------
# Polarization pair: maximize rotated_pair_anisotropy
# Body: gt(abs_s(rotated_pair_anisotropy(cap_axis_0, cap_axis_90)), 0.10)
# rotated_pair_anisotropy = (mean_a - mean_b) / (mean_a + mean_b)
# Need |mean_a - mean_b| / (mean_a + mean_b) > 0.10
# Easy: cap_axis_0 = 0.7 mean, cap_axis_90 = 0.3 mean → (0.7-0.3)/(0.7+0.3) = 0.40
# ---------------------------------------------------------------------------
y, x = np.mgrid[:H, :W]
axis_0_strong = np.full((H, W), 0.75) + 0.05 * np.sin(y / 4)
axis_90_strong = np.full((H, W), 0.25) + 0.05 * np.sin(x / 4)
anis = _rotated_pair_anisotropy(axis_0_strong, axis_90_strong)
print(f"  polarization strong: anisotropy={anis:.3f}")
stimuli['s10_polarization_strong'] = (axis_0_strong, axis_90_strong)

print("\n--- Now running predicates on each stimulus ---")

def fp_image(scene, name, color_fill=None):
    h, w = scene.shape
    if color_fill is not None:
        color = color_fill
    else:
        color = np.stack([scene]*3, axis=-1)
    bundle = FieldBundle(name=name)
    bundle.add_value("scene", "image", scene, "synthetic")
    bundle.add_value("burst", "image_stack", np.stack([scene, scene], axis=0), "")
    bundle.add_value("color_scene", "color_image", color, "")
    bundle.add_value("patch_size", "int", 64, "")
    bundle.add_value("row_y", "int", h//2, "")
    row = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
            for pn in pred_names for rec in [runtime.evaluate(pn, bundle)]}
    fired = [p for p, v in row.items() if v]
    return row, set(fired)

results = {}
for name, scene in list(stimuli.items()):
    if isinstance(scene, tuple):
        # polarization pair
        axis_0, axis_90 = scene
        bundle = FieldBundle(name=name)
        bundle.add_value("scene", "image", axis_0, "")
        bundle.add_value("cap_axis_0", "image", axis_0, "")
        bundle.add_value("cap_axis_90", "image", axis_90, "")
        bundle.add_value("burst", "image_stack", np.stack([axis_0, axis_90], axis=0), "")
        bundle.add_value("color_scene", "color_image", np.stack([axis_0]*3, axis=-1), "")
        bundle.add_value("patch_size", "int", 64, "")
        bundle.add_value("row_y", "int", axis_0.shape[0]//2, "")
        row = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
                for pn in pred_names for rec in [runtime.evaluate(pn, bundle)]}
        fired = set(p for p, v in row.items() if v)
    elif name.startswith('s7') or name.startswith('s8') or name.startswith('s9'):
        # Bayer field
        bayer = scene
        bundle = FieldBundle(name=name)
        bundle.add_value("scene", "image", bayer, "")
        bundle.add_value("raw_bayer", "raw_bayer", bayer, "")
        bundle.add_value("color_scene", "color_image", np.stack([bayer]*3, axis=-1), "")
        bundle.add_value("patch_size", "int", 64, "")
        bundle.add_value("row_y", "int", bayer.shape[0]//2, "")
        row = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
                for pn in pred_names for rec in [runtime.evaluate(pn, bundle)]}
        fired = set(p for p, v in row.items() if v)
    else:
        row, fired = fp_image(scene, name)
    results[name] = (row, fired)
    target_preds = [p for p in fired if any(x in p for x in
                    ['screen','text','spectral','polariz','subpixel','bayer','face','skin'])]
    print(f"  {name:30s}: {len(fired)} fired, target: {target_preds}")

# Aggregate
all_fired = set()
for _, fired in results.values():
    all_fired |= fired

# R180 still-dead (= R178 final remaining)
r180 = json.loads((ROOT/'round180_edge_modality'/'round180_audit.json').read_text())
remaining = set(r180['final_remaining_truly_dead'])
newly = sorted(remaining & all_fired)
still_dead = sorted(remaining - all_fired)

print(f"\nR180 remaining-truly-dead: {len(remaining)}")
print(f"  Newly activated by R181: {len(newly)}")
for p in newly:
    sources = [n for n, (_, s) in results.items() if p in s]
    print(f"    + {p:35s} (fired on: {','.join(sources)})")
print(f"  Still dead: {len(still_dead)}")
for p in still_dead:
    print(f"    - {p}")

cumulative = json.loads((ROOT/'round180_edge_modality'/'round180_audit.json').read_text())
prior_proven = set()
# Reconstruct from prior round:
for prior_round in ['round176_modality_data','round177_motion_burst','round178_text_screen_face','round180_edge_modality']:
    p = ROOT / prior_round
    aj = list(p.glob('round*_audit.json'))
    if aj:
        a = json.loads(aj[0].read_text())
        if 'cumulative_proven_active' in a:
            prior_proven |= set(a['cumulative_proven_active'])
        elif 'cumulative_proven_active_predicates' in a:
            prior_proven |= set(a['cumulative_proven_active_predicates'])
        elif 'union_demonstrated_active_predicates' in a:
            prior_proven |= set(a['union_demonstrated_active_predicates'])

all_proven = sorted(prior_proven | set(newly))
r175 = json.loads((ROOT/'round175_modality'/'round175_audit.json').read_text())
final_remaining = sorted(set(r175['truly_dead']) - set(all_proven))

audit = {
    'round': 'R181',
    'n_stimuli': len(results),
    'r180_remaining_truly_dead': len(remaining),
    'newly_activated_by_r181': len(newly),
    'newly_activated_predicates': newly,
    'r181_yield': round(len(newly) / max(len(remaining), 1), 3),
    'cumulative_proven_active_count': len(all_proven),
    'cumulative_yield_over_r175_truly_dead': round(len(all_proven) / 38, 3),
    'final_remaining_truly_dead': final_remaining,
    'n_final_remaining': len(final_remaining),
}
out = Path(__file__).parent / 'round181_audit.json'
out.write_text(json.dumps(audit, indent=2))
print(f"\nR181 yield: {audit['r181_yield']:.1%}")
print(f"Cumulative R175-truly-dead: {len(all_proven)}/38 = {audit['cumulative_yield_over_r175_truly_dead']:.1%}")
print(f"wrote {out}")
