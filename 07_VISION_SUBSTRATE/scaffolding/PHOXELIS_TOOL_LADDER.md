# Phoxelis Tool Ladder

External tools used as scaffolding while Phoxelis grows. Each row tracks what
the tool does, which Phoxelis predicate(s) or layers it scaffolds, and the
plan for retiring the dependency. A tool that sits in active use for many
rounds without a retirement plan is drift.

## Active scaffolding

| tool | what it does | Phoxelis equivalent | status | retire when |
|---|---|---|---|---|
| `numpy` / `scipy` | Operator implementation primitives (gradients, FFT, label, filter) | None — these are the substrate | **permanent** | never (load-bearing) |
| `Pillow` | Image I/O, format conversion | None — substrate | **permanent** | never |
| `reedsolo` | Reed-Solomon encode/decode | None planned (RS is not "perception") | **permanent** | never |
| `requests` | HTTP fetch for live image sources | None — substrate | **permanent** | never |
| Vincent (manual photo capture) | Real-world phone-camera images | The harness app + a pulled-from-web corpus | **active** | once R28 source router runs at scale (P-11) |
| Vincent (manual predicate authoring) | Writing new predicates by hand | LLM-as-author (P-10) | **active** | once LLM-author flow proves predicates beat random on a test corpus |
| LLM (me, in conversation) | Predicate authoring via dialogue, design decisions | LLM-author as MCP-callable tool (P-05, P-10) | **active scaffolding** | when the LLM authors via batch jobs against unlabeled corpora rather than via dialogue |

## Tools we *should* be using as scaffolding (planned)

| tool | what it would do | maps to | promise id |
|---|---|---|---|
| Face detection (e.g., MediaPipe, dlib) | L2 identity layer — `external_classifier(image, "face_present", ...)` | L2 | P-02 |
| Object detection (YOLO/DETR) | L2 — `external_classifier(image, "person_count", ...)` | L2 | P-02 |
| Scene segmentation (SAM, DeepLab) | L2 — typed regions for region-restricted predicates | L2 | P-02 |
| OCR (Tesseract / EasyOCR) | L2 — `external_classifier(image, "text_present", ...)` | L2 | P-02 |
| Image captioning (BLIP, CLIP-cap) | L3 — caption text feeds LLM-as-author | L3 + T1 | P-10 |
| ImageNet / COCO / OpenImages | T1 corpus, ground truth for predicate validation | T1 | P-11 |
| YouTube frames (via yt-dlp or thumbnail API) | T1 — heterogeneous video corpus for IR audit | T1 | P-11 |
| Chrome MCP (already available) | Real-world browser actions, social-platform round-trips | T2 (P-08) | P-08 |
| Web Fetch (already available) | Pulling specific images by URL | T1 | P-11 |

## Replacement progression

The expected lifecycle of an external tool:

1. **In use as scaffolding** — Phoxelis can't do this yet; the tool fills the
   gap.
2. **Phoxelis predicate authored to compete** — predicate composition aiming
   at the same task gets written.
3. **Predicate audited against the tool** — does the predicate match the
   tool's verdict on a test corpus? IR is the metric.
4. **Predicate accepted into vocabulary** — IR-clean over corpus, retained.
5. **Tool dropped** — the layer that depended on it now uses the predicate
   instead.

A tool that's been in use for 5+ rounds without entering step 2 is drift.
Specifically: as of R47, `Vincent (manual photo capture)` and
`Vincent (manual predicate authoring)` and `LLM (me, in dialogue)` are all
sitting at step 1 with no progression. P-10 and P-11 are the corresponding
promises to move them to step 2.

## Audit triggers

The audit script (`phoxelis_audit.py`) flags this file under the following
conditions:

- A tool listed `active` for >5 rounds with no progression — flag as
  `STAGNANT`.
- A new round commits code that imports an external library not listed here
  — flag as `UNTRACKED_TOOL`.
- A `permanent` tool with no usage in the last 5 rounds — flag as
  `UNUSED_PERMANENT` (not necessarily wrong, but worth a check).
