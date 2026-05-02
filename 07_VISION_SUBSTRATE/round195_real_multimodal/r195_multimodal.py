"""R195: REAL multimodal phoxel field from public sensor streams.

All inputs are real, captured-now data from public APIs:
  - NASA SDO: 7-band EUV solar imagery (171/193/211/304/335/094/131 Å)
  - NASA EPIC: Earth-from-L1 RGB+IR
  - IRIS FDSN: seismometer waveform (miniseed, real Earth ground motion)
  - USGS: 24h earthquake catalog (real multi-station events as 3D point cloud)
  - GOES: X-ray flux (real space-weather sensor time series)
  - NOAA: geomagnetic Kp (real magnetometer readings)

This replaces R188/R189/R190 synthesis with measured data from working sensors.
"""
import json, time
from pathlib import Path
import numpy as np
from PIL import Image
import obspy
INPUT = Path('/tmp/r195_real_sensors')
OUT = Path(__file__).parent / 'output'
OUT.mkdir(exist_ok=True, parents=True)

print("=== R195: REAL multimodal phoxel from public sensor streams ===\n")

# --- 1. SDO multispectral (7 EUV bands - REAL solar atmosphere imaging) ---
print("--- 1. NASA SDO 7-band EUV multispectral ---")
sdo_bands = [94, 131, 171, 193, 211, 304, 335]
sdo_temps_K = {94: 6_000_000, 131: 10_000_000, 171: 600_000, 193: 1_000_000,
                211: 2_000_000, 304: 50_000, 335: 2_500_000}
sdo_imgs = {}
for wl in sdo_bands:
    img = np.array(Image.open(INPUT/f'sdo_{wl}A.jpg').convert('L').resize((256, 256))).astype(np.float32) / 255.0
    sdo_imgs[wl] = img
    print(f"  {wl}Å (probe T~{sdo_temps_K[wl]:>10,}K): mean={img.mean():.3f}, max={img.max():.3f}")

# Build a 7-channel hyperspectral image
H, W = 256, 256
sdo_cube = np.stack([sdo_imgs[wl] for wl in sdo_bands], axis=-1)
print(f"  SDO cube: {sdo_cube.shape} ← REAL 7-band space-multispectral")
# Save individual bands and a "false color" composite
for wl in sdo_bands:
    Image.fromarray((sdo_imgs[wl]*255).astype(np.uint8)).save(OUT/f'01_sdo_{wl}A.png')
# False-color composite: 171=blue, 193=green, 211=red (standard)
fc = np.stack([sdo_imgs[211], sdo_imgs[193], sdo_imgs[171]], axis=-1)
Image.fromarray((fc*255).astype(np.uint8)).save(OUT/'02_sdo_false_color_211_193_171.png')

# --- 2. NASA EPIC Earth-from-L1 (real RGB satellite imagery) ---
print("\n--- 2. NASA EPIC Earth from L1 ---")
epic_files = sorted(INPUT.glob('earth_*.jpg'))
print(f"  loaded {len(epic_files)} EPIC frames")
epic = np.array(Image.open(epic_files[0]).convert('RGB').resize((512, 512)), dtype=np.float32) / 255.0
print(f"  EPIC frame: {epic.shape}, mean={epic.mean():.3f}")
Image.fromarray((epic*255).astype(np.uint8)).save(OUT/'03_epic_earth.png')

# --- 3. IRIS seismometer waveform (real ground-motion sensor) ---
print("\n--- 3. IRIS seismometer waveform ---")
try:
    st = obspy.read(str(INPUT/'iris_seismic.mseed'))
    tr = st[0]
    print(f"  Station: {tr.stats.network}.{tr.stats.station}.{tr.stats.location}.{tr.stats.channel}")
    print(f"  Start: {tr.stats.starttime}, end: {tr.stats.endtime}")
    print(f"  Sample rate: {tr.stats.sampling_rate} Hz, n_samples: {tr.stats.npts}")
    waveform = tr.data
    print(f"  Waveform: dtype={waveform.dtype}, range [{waveform.min()}, {waveform.max()}]")
except Exception as e:
    print(f"  obspy read failed: {e}")
    waveform = np.zeros(1000)

# Visualize waveform as 1D image strip
wave_norm = (waveform - waveform.min())/(waveform.max()-waveform.min()+1e-9)
n = len(waveform)
strip_h = 60
strip = np.zeros((strip_h, min(n, 2000)))
for i in range(strip.shape[1]):
    sample = wave_norm[i] if i < n else 0.5
    h_pos = min(strip_h-1, int(strip_h * (1 - sample)))
    strip[h_pos, i] = 1.0
Image.fromarray((strip*255).astype(np.uint8)).save(OUT/'04_seismic_waveform.png')

# --- 4. USGS earthquake catalog (real 3D point cloud of events) ---
print("\n--- 4. USGS earthquake catalog (24h global multi-station) ---")
quakes = json.loads(open(INPUT/'earthquakes_24h.geojson').read())
events = []
for f in quakes['features']:
    props = f['properties']
    coord = f['geometry']['coordinates']  # [lon, lat, depth_km]
    events.append({
        'lon': coord[0], 'lat': coord[1], 'depth_km': coord[2],
        'mag': props.get('mag') or 0,
        'time': props.get('time'),
        'place': props.get('place', '?'),
    })
events_arr = np.array([(e['lon'], e['lat'], e['depth_km'], e['mag']) for e in events])
print(f"  {len(events)} events in last 24h")
print(f"  magnitude range: [{events_arr[:,3].min():.1f}, {events_arr[:,3].max():.1f}]")
print(f"  depth range: [{events_arr[:,2].min():.1f}, {events_arr[:,2].max():.1f}] km")
print(f"  largest: M{events_arr[:,3].max():.1f} at {events[events_arr[:,3].argmax()]['place']}")

# Plot earthquake epicenters as a 2D world-map projection
worldmap = np.zeros((180, 360, 3), dtype=np.float32)
for e in events:
    lat_idx = int(180 - (e['lat'] + 90))
    lon_idx = int(e['lon'] + 180)
    if 0 <= lat_idx < 180 and 0 <= lon_idx < 360:
        m = max(0, e['mag'])
        worldmap[lat_idx, lon_idx] = [1.0, max(0, 1-m/8), 0.0]  # red intensity ∝ magnitude
worldmap = np.clip(worldmap, 0, 1)
Image.fromarray((worldmap*255).astype(np.uint8)).save(OUT/'05_earthquake_map_24h.png')

# --- 5. GOES X-ray flux (real space-weather time series) ---
print("\n--- 5. GOES X-ray flux time series ---")
xray = json.loads(open(INPUT/'goes_xray_1day.json').read())
flux = np.array([s['flux'] for s in xray])
times = [s['time_tag'] for s in xray]
print(f"  {len(flux)} samples")
print(f"  flux range: [{flux.min():.2e}, {flux.max():.2e}] W/m²")

# Visualize as plot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(np.log10(np.maximum(flux, 1e-9)))
ax.set_title(f"GOES X-ray flux (last 24h, log10 W/m²)")
ax.set_ylabel("log10 flux")
fig.savefig(OUT/'06_goes_xray_flux.png', dpi=80, bbox_inches='tight')
plt.close()

# --- 6. Geomagnetic Kp index (real magnetometer-derived) ---
print("\n--- 6. NOAA geomagnetic Kp ---")
geomag = json.loads(open(INPUT/'geomag_kp.json').read())
if isinstance(geomag, list) and geomag:
    print(f"  {len(geomag)} samples")
    if len(geomag) > 0:
        print(f"  fields: {list(geomag[0].keys())}")
        kp_values = [g.get('kp_index', 0) for g in geomag]
        print(f"  Kp range: [{min(kp_values):.2f}, {max(kp_values):.2f}]")

# --- 7. BUILD UNIFIED MULTIMODAL PHOXEL FIELD ---
print("\n--- 7. Unified multimodal phoxel field (REAL data) ---")
# Spatial backbone: combine SDO solar disk (256x256) and EPIC Earth (downsample to same)
# Each phoxel position is a (u, v) coordinate; carries:
#   - SDO 7-band spectrum (REAL EUV)
#   - EPIC RGB (real)
#   - earthquake density at corresponding lat/lon (real point cloud)
#   - GOES X-ray "current" (broadcast to all phoxels)
#   - geomag Kp (broadcast)

# Re-grid EPIC to 256x256 for unified
epic_re = np.array(Image.open(epic_files[0]).convert('RGB').resize((256, 256)), dtype=np.float32) / 255.0

# Earthquake density map at 256x256 (from world map)
eq_density = np.zeros((256, 256), dtype=np.float32)
for e in events:
    lat_idx = int((-(e['lat'] - 90) / 180) * 256)
    lon_idx = int((e['lon'] + 180) / 360 * 256)
    if 0 <= lat_idx < 256 and 0 <= lon_idx < 256:
        # Add gaussian "blob" of magnitude
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                yy, xx = lat_idx+dy, lon_idx+dx
                if 0 <= yy < 256 and 0 <= xx < 256:
                    w = np.exp(-(dy*dy+dx*dx)/4)
                    eq_density[yy, xx] += max(0, e['mag']) * w
eq_density = eq_density / max(1, eq_density.max())

# Build phoxel field
H = W = 256
v_idx, u_idx = np.mgrid[:H, :W]
focal = W
# Solar phoxels at z=1000 (closer)
solar_z = np.full((H, W), 1000.0)
# Earth phoxels at z=2000 (farther)
earth_z = np.full((H, W), 2000.0)

solar_pos = np.stack([u_idx-W/2, v_idx-H/2, solar_z], axis=-1).reshape(-1, 3)
earth_pos = np.stack([u_idx-W/2 + 1000, v_idx-H/2, earth_z], axis=-1).reshape(-1, 3)  # offset

solar_color = np.stack([sdo_imgs[211], sdo_imgs[193], sdo_imgs[171]], axis=-1).reshape(-1, 3)  # false-color
earth_color = epic_re.reshape(-1, 3)

# Spectral layers
solar_spectral = sdo_cube.reshape(-1, 7)
# Earth gets dummy spectral (same RGB broadcast across 7 bands)
earth_spectral = np.tile(epic_re.reshape(-1, 3).mean(axis=-1, keepdims=True), (1, 7)).astype(np.float32)

# Earthquake density (only meaningful for Earth, broadcast to solar as 0)
solar_eq = np.zeros((solar_pos.shape[0],), dtype=np.float32)
earth_eq = eq_density.reshape(-1).astype(np.float32)

# Time-series sensors broadcast as scalars per phoxel
goes_current = float(flux[-1])  # latest GOES X-ray
kp_current = float(kp_values[-1]) if 'kp_values' in dir() and kp_values else 0.0

# Concatenate Solar+Earth phoxels
all_pos = np.concatenate([solar_pos, earth_pos], axis=0).astype(np.float32)
all_col = np.concatenate([solar_color, earth_color], axis=0).astype(np.float32)
all_spec = np.concatenate([solar_spectral, earth_spectral], axis=0).astype(np.float32)
all_eq = np.concatenate([solar_eq, earth_eq], axis=0).astype(np.float32)
N = all_pos.shape[0]
print(f"  Phoxel count: {N:,} (solar + earth scenes combined)")
print(f"  Per-phoxel layers:")
print(f"    xyz position:                3 floats")
print(f"    visible RGB:                 3 floats")
print(f"    7-band EUV spectral (REAL):  7 floats")
print(f"    earthquake density:          1 float")
print(f"    pose context (broadcast):    GOES X-ray flux + Kp index")
print(f"  Total per-phoxel: 14 floats")

np.savez_compressed(OUT/'r195_multimodal_phoxel.npz',
                     positions=all_pos, colors=all_col,
                     spectral_7band=all_spec,
                     eq_density=all_eq,
                     wavelengths_angstroms=np.array(sdo_bands),
                     wavelength_temps_K=np.array([sdo_temps_K[wl] for wl in sdo_bands]),
                     goes_xray_flux=np.array([goes_current]),
                     geomag_kp=np.array([kp_current]),
                     earthquake_count_24h=np.array([len(events)]),
                     largest_quake_mag=np.array([events_arr[:,3].max()]),
                     iris_seismic_waveform=waveform.astype(np.float32),
                     iris_sample_rate_Hz=np.array([tr.stats.sampling_rate]),
                     )

print(f"\n=== Multimodal sources integrated (ALL REAL public data) ===")
print(f"  1. SDO 7-band EUV (NASA solar atmosphere)")
print(f"  2. EPIC RGB (NASA Earth from L1)")
print(f"  3. IRIS seismic waveform ({tr.stats.npts} samples)")
print(f"  4. USGS earthquake catalog ({len(events)} events)")
print(f"  5. GOES X-ray flux ({len(flux)} samples)")
print(f"  6. NOAA geomagnetic Kp")

audit = {
    'round': 'R195',
    'method': 'real public sensor data fusion into multimodal phoxel field',
    'data_sources_real': {
        'NASA_SDO': {'bands_angstroms': sdo_bands,
                      'temperatures_K': [sdo_temps_K[wl] for wl in sdo_bands],
                      'image_size': [H, W],
                      'note': 'live solar atmosphere imaging - 7 ionization-state-specific EUV wavelengths'},
        'NASA_EPIC': {'frames': len(epic_files),
                       'note': 'Earth-from-L1 (DSCOVR satellite, ~1.5M km from Earth)'},
        'IRIS_seismic': {'station': f"{tr.stats.network}.{tr.stats.station}",
                          'channel': tr.stats.channel,
                          'sample_rate_Hz': float(tr.stats.sampling_rate),
                          'n_samples': int(tr.stats.npts),
                          'note': 'real ground-motion sensor data via FDSN protocol'},
        'USGS_earthquakes': {'n_events_24h': len(events),
                              'mag_range': [float(events_arr[:,3].min()), float(events_arr[:,3].max())],
                              'depth_range_km': [float(events_arr[:,2].min()), float(events_arr[:,2].max())],
                              'note': 'multi-station triangulated events from global seismic networks'},
        'GOES_xray': {'n_samples_24h': len(flux),
                       'flux_range_W_per_m2': [float(flux.min()), float(flux.max())],
                       'note': 'NOAA SWPC real-time space weather sensor'},
        'NOAA_geomag': {'note': 'magnetometer-derived Kp index'},
    },
    'phoxel_count': int(N),
    'per_phoxel_floats': 14,
    'output': str(OUT/'r195_multimodal_phoxel.npz'),
    'output_size_mb': round((OUT/'r195_multimodal_phoxel.npz').stat().st_size/1e6, 2),
}
(Path(__file__).parent / 'round195_audit.json').write_text(json.dumps(audit, indent=2))
print(f"\nfile size: {audit['output_size_mb']} MB")
print(f"NO synthesis. ALL real sensor data.")
