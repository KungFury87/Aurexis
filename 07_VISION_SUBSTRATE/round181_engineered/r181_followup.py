"""R181 follow-up: add the 2 newly activated predicates from debug session.

Discovered: raw_bayer field must be stored as type='image' (not 'raw_bayer')
because the predicate signatures use 'expects raw_bayer:image' — field NAME
'raw_bayer' but field TYPE 'image'. With this, has_spectral_band_anomaly
fires on G1/G2-imbalanced Bayer. Engineered counter-alternating Bayer
makes block_avg_2x2 flat while bayer_R is alternating, which fires
has_subpixel_periodicity at fft ratio = infinity.
"""
import warnings; warnings.filterwarnings('ignore')
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path('/sessions/wonderful-sharp-rubin/mnt/Aurexis evolved/Aurexis_Core_WORKING_20260414-1339/07_VISION_SUBSTRATE')
sys.path.insert(0, str(ROOT))
from aurexis_workbench.runtime import Runtime
from aurexis_workbench import dsl, predicates as P, vision_ops
from aurexis_workbench.fields import FieldBundle
from aurexis_workbench.vision_ops import (_bayer_R, _block_avg_2x2, _fft_peak_to_floor,
                                            _green_imbalance, _channel_spread_norm)

vision_ops.register_all()
text = (ROOT/'data'/'vision'/'vocab.aurex').read_text()
runtime = Runtime()
for pp in dsl.parse_source(text):
    if pp.ok:
        try: P.type_check(pp.pred); runtime.install(pp.pred)
        except: pass
pred_names = sorted(runtime.installed())

H, W = 240, 320

# === Stim A: counter-alternating Bayer for has_subpixel_periodicity ===
bayer_a = np.zeros((H, W))
y_R, x_R = np.mgrid[:H//2, :W//2]
R_vals = 0.5 + 0.4 * np.cos(np.pi * x_R)
bayer_a[0::2, 0::2] = R_vals
bayer_a[0::2, 1::2] = 1.0 - R_vals  # G1 counter-alternates
bayer_a[1::2, 0::2] = 0.5
bayer_a[1::2, 1::2] = 0.5

bundle_a = FieldBundle(name='r181_subpixel')
bundle_a.add_value("scene", "image", bayer_a, "")
bundle_a.add_value("raw_bayer", "image", bayer_a, "raw_bayer field, stored as type 'image'")
bundle_a.add_value("color_scene", "color_image", np.stack([bayer_a]*3, axis=-1), "")
bundle_a.add_value("patch_size", "int", 64, "")
bundle_a.add_value("row_y", "int", H//2, "")
row_a = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
          for pn in pred_names for rec in [runtime.evaluate(pn, bundle_a)]}
fired_a = sorted(p for p, v in row_a.items() if v)
print(f"r181_subpixel: {len(fired_a)} fired")
print(f"  has_subpixel_periodicity: {row_a.get('has_subpixel_periodicity')}")

# === Stim B: G1/G2-imbalanced Bayer for has_spectral_band_anomaly ===
bayer_b = np.zeros((H, W))
bayer_b[0::2, 0::2] = 0.5
bayer_b[0::2, 1::2] = 0.7  # G1
bayer_b[1::2, 0::2] = 0.3  # G2
bayer_b[1::2, 1::2] = 0.5

bundle_b = FieldBundle(name='r181_spectral_anomaly')
bundle_b.add_value("scene", "image", bayer_b, "")
bundle_b.add_value("raw_bayer", "image", bayer_b, "raw_bayer field stored as 'image' type")
bundle_b.add_value("color_scene", "color_image", np.stack([bayer_b]*3, axis=-1), "")
bundle_b.add_value("patch_size", "int", 64, "")
bundle_b.add_value("row_y", "int", H//2, "")
row_b = {pn: bool(rec.value) if (rec.error is None and rec.value is not None) else False
          for pn in pred_names for rec in [runtime.evaluate(pn, bundle_b)]}
fired_b = sorted(p for p, v in row_b.items() if v)
print(f"r181_spectral_anomaly: {len(fired_b)} fired")
print(f"  has_spectral_band_anomaly: {row_b.get('has_spectral_band_anomaly')}")
print(f"  green_imbalance: {_green_imbalance(bayer_b):.3f}")

# Combine all R181 activations
all_r181_fired = set(fired_a) | set(fired_b)
print(f"\nUnion R181 followup: {len(all_r181_fired)} preds fired")

# Aggregate with prior R181 audit
prior = json.loads((ROOT/'round181_engineered'/'round181_audit.json').read_text())
prior_newly = set(prior.get('newly_activated_predicates', []))

r175 = json.loads((ROOT/'round175_modality'/'round175_audit.json').read_text())
truly_dead = set(r175['truly_dead'])
r180 = json.loads((ROOT/'round180_edge_modality'/'round180_audit.json').read_text())
prior_proven = truly_dead - set(r180['final_remaining_truly_dead'])

newly_total = sorted((set(prior_newly) | (truly_dead & all_r181_fired)) & truly_dead)
all_proven = sorted(prior_proven | set(newly_total))
final_remaining = sorted(truly_dead - set(all_proven))

print(f"\nR181 newly activated total: {len(newly_total)}")
for p in newly_total:
    print(f"  + {p}")
print(f"Cumulative R175-truly-dead activated: {len(all_proven)}/38 = {len(all_proven)/38:.1%}")
print(f"Final remaining truly dead: {len(final_remaining)}")
for p in final_remaining:
    print(f"  - {p}")

audit = {
    'round': 'R181',
    'finding': 'raw_bayer field stored as type=image (not raw_bayer dtype) because predicates expect "raw_bayer:image" - field name + image type. R180/initial-R181 used wrong type tag; fixed here. Engineered counter-alternating Bayer activates has_subpixel_periodicity (block_avg cancels to flat); G1/G2 imbalanced Bayer activates has_spectral_band_anomaly (green_imbalance=0.40>>0.02).',
    'r180_remaining_truly_dead': prior['r180_remaining_truly_dead'],
    'newly_activated_by_r181': len(newly_total),
    'newly_activated_predicates': newly_total,
    'r181_yield': round(len(newly_total) / max(prior['r180_remaining_truly_dead'], 1), 3),
    'cumulative_proven_active_count': len(all_proven),
    'cumulative_proven_active': all_proven,
    'cumulative_yield_over_r175_truly_dead': round(len(all_proven) / 38, 3),
    'final_remaining_truly_dead': final_remaining,
    'n_final_remaining': len(final_remaining),
}
out = ROOT/'round181_engineered'/'round181_audit.json'
out.write_text(json.dumps(audit, indent=2))
print(f"\nR181 yield (over R180 remaining): {audit['r181_yield']:.1%}")
print(f"Cumulative R175-truly-dead activated: {audit['cumulative_yield_over_r175_truly_dead']:.1%}")
print(f"wrote {out}")
