"""Live image sources for Phoxelis IR audits at scale.

Pulls public-domain / CC0 / CC-BY images from a curated set of APIs.
Each source is a generator yielding (PIL.Image, alias, source_name).
Images live in RAM; only their predicate verdicts persist.

Modeled after the source router in Donald Pilger's `bigbugnowadaze/scry`
repo (also descended from Aurexis), which provided the API URL set
and the dedup/rotation pattern. This is a fresh, slimmer implementation
focused on no-key public APIs so the audit can run without setup.

URL-level dedup: any URL fetched in a previous run is skipped.
Persists in `<archive>/_seen_urls.txt`.

Optional API keys (env vars) for the keyed sources:
    NASA_API_KEY, UNSPLASH_ACCESS_KEY, PEXELS_API_KEY, PIXABAY_API_KEY
Without them, the keyed sources just print a one-line skip notice.
"""
from __future__ import annotations

import datetime
import io
import os
import random
import time
from pathlib import Path

import requests
from PIL import Image

UA = {"User-Agent": "Phoxelis/1.0 (research; offline-non-LLM)"}


# ---- URL-level dedup ----------------------------------------------------

class SkipURL(Exception):
    """Raised when a URL has already been fetched in a prior run."""


_SEEN: set = set()
_SEEN_FILE: Path | None = None
_SEEN_DIRTY = 0


def init_dedup(archive_dir: str | Path) -> None:
    global _SEEN, _SEEN_FILE
    p = Path(archive_dir)
    p.mkdir(parents=True, exist_ok=True)
    _SEEN_FILE = p / "_seen_urls.txt"
    if _SEEN_FILE.exists():
        try:
            _SEEN = set(_SEEN_FILE.read_text(encoding="utf-8").splitlines())
        except Exception:
            _SEEN = set()
    else:
        _SEEN = set()


def _remember(url: str) -> None:
    global _SEEN_DIRTY
    _SEEN.add(url)
    _SEEN_DIRTY += 1
    if _SEEN_FILE and _SEEN_DIRTY >= 50:
        flush_dedup()


def flush_dedup() -> None:
    global _SEEN_DIRTY
    if _SEEN_FILE:
        try:
            _SEEN_FILE.write_text("\n".join(sorted(_SEEN)),
                                    encoding="utf-8")
            _SEEN_DIRTY = 0
        except Exception:
            pass


def _has_key(env_var: str) -> bool:
    return bool(os.environ.get(env_var, "").strip())


def _fetch(url: str, *, timeout: int = 30, params=None,
             headers=None) -> Image.Image:
    if url in _SEEN:
        raise SkipURL(url)
    h = dict(UA)
    if headers:
        h.update(headers)
    r = requests.get(url, headers=h, params=params, timeout=timeout)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    _remember(url)
    return img


def _safe(url: str, alias: str, source: str):
    try:
        return _fetch(url), alias, source
    except SkipURL:
        return None
    except Exception:
        return None


# ---- query rotation -----------------------------------------------------

NATURE = ["nature", "forest", "ocean", "mountain", "desert", "river",
            "wildlife", "flower", "tree", "sky"]
ART    = ["painting", "sculpture", "drawing", "portrait", "landscape",
            "still life", "watercolor", "engraving", "manuscript"]
ASTRO  = ["galaxy", "nebula", "star cluster", "planet", "moon", "comet"]
TAXA   = ["Aves", "Insecta", "Plantae", "Mammalia", "Reptilia",
            "Amphibia", "Mollusca", "Fungi", "Arachnida", "Crustacea"]


def pick(lst):
    return random.choice(lst)


# ---- Stage 0: synthetic (no network) ------------------------------------

def stream_synthetic(n: int = 20, size: int = 256, kind: str = "perlin"):
    import numpy as np
    rng = np.random.default_rng()
    for _ in range(n):
        if kind == "uniform":
            arr = rng.integers(0, 256, (size, size, 3), dtype="uint8")
        elif kind == "gradient":
            x = rng.integers(0, 256, (size, size, 3), dtype="uint8")
            for c in range(3):
                base = rng.integers(0, 256)
                grad = (rng.random((size, size)) * 80 + base) % 256
                x[..., c] = grad.astype("uint8")
            arr = x
        else:  # perlin-ish: low-pass noise
            base = rng.normal(128, 40, (size, size, 3))
            for _ in range(3):
                import numpy as _np
                base = (base + _np.roll(base, 1, axis=0)
                          + _np.roll(base, 1, axis=1)) / 3
            arr = base.clip(0, 255).astype("uint8")
        yield (Image.fromarray(arr),
               f"synth_{kind}_{rng.integers(0, 1 << 30):08x}",
               "synthetic")


# ---- Stage 1: easy photos -----------------------------------------------

def stream_picsum(n: int = 20, w: int = 512, h: int = 512):
    fetched = 0
    attempts = 0
    while fetched < n and attempts < n * 4:
        attempts += 1
        seed = random.randint(1, 10_000_000)
        out = _safe(f"https://picsum.photos/seed/{seed}/{w}/{h}",
                      f"picsum_{seed}", "picsum")
        if out:
            yield out
            fetched += 1


# ---- Stage 2: diverse photos --------------------------------------------

def stream_wikimedia(n: int = 20, thumb: int = 800):
    api = "https://commons.wikimedia.org/w/api.php"
    fetched = 0
    attempts = 0
    while fetched < n and attempts < n * 4:
        attempts += 1
        try:
            r = requests.get(api, headers=UA, timeout=30, params={
                "action": "query", "format": "json",
                "generator": "random", "grnnamespace": 6, "grnlimit": 1,
                "prop": "imageinfo", "iiprop": "url|mime",
                "iiurlwidth": thumb,
            }).json()
            for _, page in r.get("query", {}).get("pages", {}).items():
                info = page.get("imageinfo", [{}])[0]
                mime = info.get("mime", "")
                if not mime.startswith("image/") or "svg" in mime:
                    continue
                url = info.get("thumburl") or info.get("url")
                if not url:
                    continue
                title = page.get("title", "").replace("File:", "")[:30]
                alias = f"wm_{fetched:03d}_{title.replace(' ', '_')}"
                out = _safe(url, alias, "wikimedia")
                if out:
                    yield out
                    fetched += 1
            time.sleep(0.5)
        except Exception:
            time.sleep(1)


def stream_openverse(query: str | None = None, n: int = 20):
    query = query or pick(NATURE)
    try:
        r = requests.get("https://api.openverse.org/v1/images/",
                         headers=UA, timeout=30,
                         params={"q": query,
                                  "page_size": min(n, 20),
                                  "page": random.randint(1, 20),
                                  "license": "cc0,pdm,by"}).json()
        for it in r.get("results", [])[:n]:
            url = it.get("thumbnail") or it.get("url")
            if not url:
                continue
            out = _safe(url, f"openverse_{it.get('id', '?')[:8]}",
                          "openverse")
            if out:
                yield out
    except Exception:
        pass


# ---- Stage 3: wildlife --------------------------------------------------

def stream_inaturalist(taxon: str | None = None, n: int = 20):
    taxon = taxon or pick(TAXA)
    try:
        r = requests.get("https://api.inaturalist.org/v1/observations",
                         headers=UA, timeout=30,
                         params={"taxon_name": taxon, "photos": "true",
                                  "photo_license": "cc-by,cc-by-sa,cc0",
                                  "per_page": n,
                                  "page": random.randint(1, 50),
                                  "order": "desc",
                                  "order_by": "created_at"}).json()
        for obs in r.get("results", [])[:n]:
            for ph in obs.get("photos", []):
                url = ph["url"].replace("square", "medium")
                out = _safe(url, f"inat_{obs['id']}", "inaturalist")
                if out:
                    yield out
                    break
            time.sleep(0.2)
    except Exception:
        pass


# ---- Stage 4: art -------------------------------------------------------

def stream_met(query: str | None = None, n: int = 20):
    query = query or pick(ART)
    try:
        ids = (requests.get(
            "https://collectionapi.metmuseum.org/public/collection/v1/search",
            headers=UA, timeout=30,
            params={"hasImages": "true", "q": query})
               .json().get("objectIDs", []) or [])
        random.shuffle(ids)
        fetched = 0
        for oid in ids:
            if fetched >= n:
                break
            try:
                obj = requests.get(
                    f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}",
                    headers=UA, timeout=30).json()
                if obj.get("isPublicDomain") and obj.get("primaryImageSmall"):
                    out = _safe(obj["primaryImageSmall"], f"met_{oid}", "met")
                    if out:
                        yield out
                        fetched += 1
                time.sleep(0.05)
            except Exception:
                continue
    except Exception:
        pass


def stream_artic(query: str | None = None, n: int = 20):
    query = query or pick(ART)
    try:
        r = requests.get("https://api.artic.edu/api/v1/artworks/search",
                         headers=UA, timeout=30,
                         params={"q": query, "limit": n,
                                  "page": random.randint(1, 20),
                                  "fields": "id,image_id,is_public_domain"}
                         ).json()
        for w in r.get("data", []):
            if not (w.get("is_public_domain") and w.get("image_id")):
                continue
            url = (f"https://www.artic.edu/iiif/2/{w['image_id']}"
                   f"/full/843,/0/default.jpg")
            out = _safe(url, f"artic_{w['id']}", "artic")
            if out:
                yield out
            time.sleep(0.4)
    except Exception:
        pass


# ---- Stage 5: astronomy -------------------------------------------------

def _nasa_key():
    return os.environ.get("NASA_API_KEY", "DEMO_KEY")


def stream_apod(n: int = 20):
    start = datetime.date(1995, 6, 16)
    end = datetime.date.today()
    span = (end - start).days
    fetched = 0
    attempts = 0
    while fetched < n and attempts < n * 3:
        attempts += 1
        d = (start + datetime.timedelta(days=random.randint(0, span))
             ).isoformat()
        try:
            r = requests.get("https://api.nasa.gov/planetary/apod",
                             timeout=30,
                             params={"api_key": _nasa_key(),
                                      "date": d}).json()
            if r.get("media_type") != "image":
                continue
            url = r.get("hdurl") or r.get("url")
            if not url:
                continue
            out = _safe(url, f"apod_{d}", "apod")
            if out:
                yield out
                fetched += 1
        except Exception:
            pass


def stream_mars(rover: str = "curiosity", n: int = 20):
    sol = random.randint(100, 3000)
    try:
        r = requests.get(
            f"https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos",
            timeout=30,
            params={"sol": sol, "api_key": _nasa_key()}).json()
        for p in r.get("photos", [])[:n]:
            out = _safe(p["img_src"], f"mars_{p['id']}", "mars")
            if out:
                yield out
    except Exception:
        pass


# ---- Stage 6: earth from above ------------------------------------------

def stream_osm(n: int = 20, zoom: int = 5):
    max_t = 2 ** zoom
    fetched = 0
    attempts = 0
    while fetched < n and attempts < n * 3:
        attempts += 1
        x = random.randint(0, max_t - 1)
        y = random.randint(0, max_t - 1)
        url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
        out = _safe(url, f"osm_{zoom}_{x}_{y}", "osm")
        if out:
            yield out
            fetched += 1
            time.sleep(0.4)


# ---- Registry -----------------------------------------------------------

SOURCES = {
    "stage_0_synthetic": [
        ("Synthetic uniform",  lambda n: stream_synthetic(n, kind="uniform")),
        ("Synthetic gradient", lambda n: stream_synthetic(n, kind="gradient")),
        ("Synthetic perlin",   lambda n: stream_synthetic(n, kind="perlin")),
    ],
    "stage_1_easy": [
        ("Lorem Picsum",        stream_picsum),
    ],
    "stage_2_diverse": [
        ("Wikimedia random",    stream_wikimedia),
        ("Openverse rotating",  lambda n: stream_openverse(None, n)),
    ],
    "stage_3_wildlife": [
        ("iNaturalist rotating", lambda n: stream_inaturalist(None, n)),
    ],
    "stage_4_art": [
        ("Met Museum rotating", lambda n: stream_met(None, n)),
        ("Art Institute rotating", lambda n: stream_artic(None, n)),
    ],
    "stage_5_astronomy": [
        ("NASA APOD random",    stream_apod),
        ("NASA Mars rover",     lambda n: stream_mars("curiosity", n)),
    ],
    "stage_6_earth_above": [
        ("OpenStreetMap z=5",   lambda n: stream_osm(n, zoom=5)),
    ],
}


def stream_all_stages(per_source: int = 5, archive_dir: str | None = None):
    """Iterate every source in the registry, yielding up to per_source
    images per source. Calls init_dedup() first if archive_dir is given."""
    if archive_dir:
        init_dedup(archive_dir)
    for stage_name, lst in SOURCES.items():
        for label, fn in lst:
            print(f"  [{stage_name}] {label} ...")
            try:
                for item in fn(per_source):
                    yield item
            except Exception as e:
                print(f"    {label} crashed: {type(e).__name__}: {e}")
    flush_dedup()
