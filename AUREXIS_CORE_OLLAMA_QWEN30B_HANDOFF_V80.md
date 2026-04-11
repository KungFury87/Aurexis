# Aurexis Core — Full Local-Model Handoff for Ollama / `qwen3-coder:30b`

**Owner / inventor:** Vincent Anderson  
**Project:** Aurexis Core  
**Current repo baseline:** V80 (`Aurexis_Core_V80_Repo_Verification_Surface.zip`)  
**Primary goal of this handoff:** bring a local coding model up to speed on the actual project truth, repo state, working laws, user preferences, and immediate next milestones so it can continue useful work without drifting.

---

## 0. How to use this handoff

This file is meant to be given to a local model **alongside the V80 repo zip or extracted repo**.

Best usage pattern:
1. Give the model this handoff file first.
2. Give it the V80 repo after that.
3. Tell it to treat this file as the active project law unless Vincent overrides something.
4. Tell it to continue only from the **next real seam**, not from old assumptions.

If you want a copy-paste starter prompt, use this:

```text
You are continuing Aurexis Core from the attached V80 repo and the attached handoff file.
Treat the handoff file as the governing project law and working contract.
Do not guess. Infer from the handoff, repo, and code shape.
Do not drift into Aurexis E/D, app-building, or speculative overexpansion.
Continue from the next real seam only.
When you report progress, always include:
1. current state
2. what changed
3. what was verified
4. honest limit
5. largest-scale tracker with percentages
6. dumbed-down summary
7. best recommended next step
Prefer complete new package-level passes over tiny loose patches whenever practical.
If a decision would change project law, pause and ask Vincent right before the best recommended next step. Otherwise keep going until the next real stop.
```

---

## 1. Canonical project identity

### What Aurexis Core fundamentally is
Aurexis Core is a **programming language** and a **new computer interface layer with the physical world**.

It is meant to become the **underlying code of vision for computers**.

The world is already governed by physics. Light is part of that physics. Humans can interpret visual information from that physical reality. Aurexis Core exists to let computers interpret that same visual information lawfully, at human-like scale or better, using current technology now and future technology later.

This is not merely “image processing.” It is the deeper language layer for machine vision grounded in physics, light, and structured observation.

### Core conceptual sentence
Aurexis Core is the code that sits conceptually in the stream **between a computer’s optic nerve and its brain**.

That means:
- the **world** is primary reality
- the **camera** is the sensory intake surface
- the **phoxel field** is the machine’s immediate observed stream
- **Core** is the law that organizes that stream into structured, bounded, machine-usable reality

---

## 2. What Aurexis Core is **not**

Aurexis Core is **not**:
- a gimmick
- a niche toy
- an app
- Aurexis E/D
- a sigil system
- a purely text-first language
- a normal image parser pretending to be revolutionary
- fake “AI vision magic” that overclaims what the camera knows

Aurexis E/D is **not the active target right now**. It exists only as a deferred downstream concept until Core is sufficiently complete.

---

## 3. Long-term vision and why this matters

Vincent’s vision is bigger than the current prototype repo.

Desired future consequences of Core:
- file → image → file workflows using ordinary phones/cameras
- stronger offline camera-based interpretation
- improved machine vision applications
- robot vision that operates more like true visual understanding
- visual analysis systems that interpret the world more like humans do
- future software ecosystems built **on top of** the new computer vision law

Important distinction:
- **Core itself** = the language/law layer
- **future apps/products built on top of Core** = downstream applications

Do not collapse those into each other.

---

## 4. Feasibility law

This is a top-level governing constraint.

Aurexis Core must be:
- possible with **current technology**
- adoptable on **current mobile technology**
- not capped by current technology
- scalable upward into future cameras/sensors/robots without rewriting the core language law

Correct design stance:
- **current-tech floor**
- **future-tech ceiling**

This means Core cannot rely on:
- exotic sensors as a baseline requirement
- impossible world reconstruction from one weak image
- magical certainty from commodity cameras
- sci-fi assumptions disguised as current reality

Instead, it must be:
- sensor-minimum
- capability-scalable
- world-anchored
- image-accessed
- validation-gated
- uncertainty-aware

---

## 5. The phoxel definition

### Core definition
A **phoxel** is the atomic observation object of Aurexis Core.

It is a **photon/pixel bridge object**:
- tied to the physical world through light
- made computationally available through camera observation
- used by Core as the smallest lawful unit for building visual-world understanding

A phoxel is **not just a pixel value** and **not just a photon**.
It is the smallest machine-usable unit where:
- physical light
- observed image position
- world-side spatial meaning
- relation to nearby structure
meet in one object.

### The phoxel is made of
A phoxel is made of:
- a measurable **photonic signature**
- an **image-side observation location**
- a **world-side anchor state**
- a **time-bound observation**
- a set of **relations** to other phoxels
- an **integrity state** describing how trustworthy it is

### Minimum legal phoxel record
The V21 law reset pushed this schema into code. The lawful phoxel record is:
- `phoxel_id`
- `image_anchor`
- `world_anchor_state`
- `photonic_signature`
- `time_slice`
- `relation_set`
- `integrity_state`

### Current coded phoxel law details
The repo’s law layer currently includes:
- `ObservationState`: `observed`, `estimated`, `validated`, `unknown`
- `WorldAnchorMode`: `unknown`, `estimated`, `resolved`
- `ImageAnchor`
- `WorldAnchorState`
- `PhotonicSignature`
- `RelationLink`
- `RelationSet`
- `IntegrityState`
- scoring helpers for relation structure, integrity, world-anchor confidence, and phoxel promotion state

This is not the final ultimate phoxel law, but it is the active coded law in V80.

---

## 6. World/image authority law

This is already conceptually locked.

Correct interpretation:
- **world first in authority**
- **image first in access**
- **both alive at once in processing**

Meaning:
- the world is what exists
- the image is how the machine gets access to it
- Core must preserve both registers simultaneously
- image appearance is not ultimate truth
- world truth cannot be faked when not earned

Do not reduce Core to pure image-space heuristics.
Do not pretend full world-space certainty when the evidence does not support it.

---

## 7. Native relation law

The project’s foundational relation stack should be treated in roughly this hierarchy.

### Tier 1 — absolutely native
These are the most important primitive relation concepts:
- position
- adjacency
- direction
- distance / proximity
- containment
- boundary
- region membership
- sequence / ordering

### Tier 2 — also native, but higher-order
- scale
- hierarchy
- overlap / intersection
- continuity
- transition / edge relation

### Tier 3 — important, but not first-day primitive bedrock
- occlusion
- projection correspondence
- temporal continuity
- viewpoint relation

The repo currently contains first-pass relation synthesis and relation profiling, but the long-term relation algebra is **not finished**.

---

## 8. Validation / execution law

Observed structure and executable structure are **not the same thing**.

Correct law:
- observed structure enters Core immediately
- interpreted structure can exist provisionally
- executable structure must be **promoted through gates**

### Correct asymmetry
- seeing is broad
- meaning is narrower
- execution is strict

### Promotion gates (current conceptual law)
A structure should only promote from observed/interpreted to executable if it passes enough of the following:
1. geometric coherence
2. cross-register consistency
3. signal integrity
4. temporal or contextual support
5. language legality
6. bounded inference

The repo has already started enforcing this in deeper layers:
- V22 pulled phoxel law into token formation
- V23 pulled law gating into grammar/runtime legality
- parse-only rows are prevented from automatically becoming executable rows

---

## 9. Illegal inference law

This is critical.

### Center rule
**Core can only claim what the visual evidence earns.**

If it did not clearly observe it, validate it, or support it strongly enough, it cannot present it as fact.

### Claim levels
Core outputs should always conceptually distinguish:
- `observed`
- `estimated`
- `validated`
- `unknown`

### Core is allowed to say
At observation level:
- there is light information here
- there is a boundary here
- these phoxels are related
- this region changed
- this pattern exists in the observation

At estimate level:
- this is probably the same structure
- this may belong to the same region
- this may continue behind an edge
- world position is estimated, not confirmed

At validated level:
- this is valid enough to treat as structure
- this relation passed promotion thresholds
- this is strong enough to use downstream

### Core is not allowed to do
- treat one image as full world truth
- pretend uncertainty does not exist
- invent hidden structure as fact
- confuse image truth with world truth
- confuse pattern with language/code automatically
- confuse similarity with identity
- claim causality from appearance alone
- overclaim across time from one slice

The repo has already started carrying this law into runtime outputs and primary output selection.

---

## 10. What the current repo actually is

The current repo is **real** and **meaningful**, but it is still a prototype substrate, not the full final embodiment of the long-term Core vision.

Best honest framing:
- it is a **Core-only prototype repo**
- it has a serious visual/runtime spine
- it already contains meaningful law-facing code
- it contains a large amount of evidence/reporting/export/checklist/health-pack infrastructure
- it is still **not** the completed final machine-vision language promised by the long-term vision

### The repo is farther along than a toy
Already present in real code:
- visual intake
- normalization
- phoxel extraction/runtime objects
- tokenization
- grammar/runtime assembly
- interpreter/runtime logic
- legality gating
- outputs and primary output selection
- observed evidence
- threshold tracking and mutation
- calibration cycles / replay / history
- asset search / replay
- sequence handling
- conformance
- export/report/pack/checklist surfaces
- scoreboard/health/trend surfaces
- repo verification surface and CLI

### But it is not “done” in the grand vision sense
Still not honestly proven as fully complete:
- final live raw-video machine-vision runtime
- final relation algebra
- final world-anchor upgrade law
- complete multi-frame and world strengthening rules
- final transform-heavy semantics
- fully earned broad physical-world trust
- final public-ready machine-vision language implementation

---

## 11. High-level repo history in useful phases

You do **not** need to memorize all 80 versions individually, but you should understand the major arcs.

### Phase A — foundational runtime substrate
Early passes built:
- core objects
- lifecycle/authority logic
- values/operations
- binding/scope/runtime legality
- visual intake / normalization / phoxel extraction
- tokenization / grammar assembly / interpreter runtime
- starter conformance and evaluation kernels

### Phase B — evidence / calibration / reporting growth
Mid passes added:
- observed evidence
- statement layout
- threshold tracking
- calibration replay/history/search
- pattern signatures
- harder assets
- weak-signal recovery
- primary output/program surfaces

### Phase C — law reset and phoxel re-grounding
This is one of the most important inflection points.

From V21 onward, the project was reclassified:
- the old repo became implementation substrate, not project-defining truth
- Core was reaffirmed as a world-anchored, image-accessed language under physics/current tech
- lawful phoxel schema was added
- later token/runtime/output layers were forced to inherit that law more honestly

Important passes in this arc:
- **V21**: Core law reset and phoxel schema
- **V22**: token law alignment
- **V23**: grammar/runtime law gating
- **V24**: illegal inference output discipline

### Phase D — artifact/export/acceptance/reporting surfaces
Later passes built strong outward-facing infrastructure:
- run reports
- history reports
- conformance reports
- artifact export bundles
- lawful export packs
- developer handoff packs
- operator quickstart packs
- release candidate smoke packs
- acceptance checklists for many of these

### Phase E — top-level health/scoreboard/trend visibility
Then the repo added:
- all-artifacts scoreboard
- artifact health report
- artifact health trend
- scoreboard/report/RC/pack layer trends
- exact trouble-spot inheritance through higher surfaces

Important recent passes:
- **V76**: top-level report trouble spots
- **V77**: trend trouble spots
- **V78**: pack-surface trouble spots

### Phase F — repo health repair and proof surface
Most recent two big steps:
- **V79** repaired missing fixture lineage, helper compatibility, and manifest tolerance
- **V80** added a first-class repo verification surface and CLI so proof is part of the repo itself rather than living only in shell history

---

## 12. Current V80 state

### What V79 solved
V79 repaired a meaningful repo-health seam:
- restored missing shared example fixtures
- hardened manifest loading
- hardened helper-call compatibility
- repaired observed-cycle verdict handling
- added score-path caching for repeated calibration/search/history runs

### What V80 solved
V80 added a new first-class verification surface:
- module: `src/aurexis_core/repo_verification_report.py`
- CLI: `aurexis-core repo-verification`
- purpose: collect tests, run them in deterministic batches, emit markdown/json verification artifacts

### What was actually proven
The repo’s own docs say:
- V79 full deterministic 5-file pytest batch verification: **15/15 passing batches**, no failing batches
- V80 delta reruns on changed/new verification surfaces: **8 passed**
- V80 collect-only count: **154 tests**

### Honest limit still active
There is **not yet a claimed one-shot monolithic fresh V80 full-suite artifact run** completed in the current container/session.

So the current proof state is honest and split like this:
- full rebuilt-suite batch verification on V79
- V80 delta reruns on the new verification surfaces
- V80 collect-only test count = 154

That is still meaningful proof. It is just not a fake “everything is complete forever” claim.

---

## 13. Current inferred progress view

These are **inferred operational percentages**, not mystical truth. They are intended to help a local model preserve trajectory honestly.

### Repo/runtime substrate maturity
**~82%**

Reason:
- the repo now has broad real code coverage across extraction, runtime, reporting, export, and verification surfaces
- but there are still important deep-language and live-world gaps

### Law-grounded prototype maturity
**~68%**

Reason:
- the law reset, phoxel schema, token/runtime gating, and illegal-inference discipline are materially real now
- but relation algebra, stronger world-anchor progression, and deeper live-world grounding are still incomplete

### Full long-term Core vision completion
**~35–40%**

Reason:
- Vincent’s true vision is larger than the current implementation
- the repo is a serious substrate and proof framework, not yet the finished “underlying code of vision for computers” in the strongest sense

### Artifact/report/verification infrastructure maturity
**~90%**

Reason:
- the repo is now unusually strong in export/health/acceptance/checklist/verification surfaces for its stage
- the proving/reporting layer is one of the strongest parts of the current codebase

---

## 14. Repo map — key subsystems

This is the most useful way to understand the tree.

### Core law / phoxel / runtime primitives
Key files:
- `src/aurexis_core/phoxel_law.py`
- `src/aurexis_core/phoxel_runtime.py`
- `src/aurexis_core/phoxel_fields.py`
- `src/aurexis_core/phoxel_patterns.py`
- `src/aurexis_core/phoxel_semantics.py`
- `src/aurexis_core/core_objects.py`
- `src/aurexis_core/runtime_legality.py`
- `src/aurexis_core/authority.py`
- `src/aurexis_core/lifecycle.py`

### Visual intake / scene path
- `visual_intake.py`
- `normalization.py`
- `visual_frame.py`
- `frame.py`
- `visual_pipeline.py`
- `visual_sequence.py`
- `visual_trace.py`
- `scene_runtime.py`
- `region_graph.py`
- `sequence_fusion.py`
- `transforms.py`
- `weak_signal_recovery.py`

### Language assembly / meaning / execution
- `tokenization.py`
- `token_disambiguation.py`
- `statement_layout.py`
- `grammar_runtime.py`
- `interpreter_runtime.py`
- `runtime_outputs.py`
- `program_condensation.py`
- `primary_output.py`
- `semantic_aggregation.py`
- `operations.py`
- `values.py`
- `scope_binding.py`

### Evidence / calibration / search / history
- `observed_evidence.py`
- `observed_cycle.py`
- `calibration_cycle.py`
- `calibration_replay.py`
- `calibration_history.py`
- `calibration_asset_replay.py`
- `calibration_asset_search.py`
- `threshold_tracking.py`
- `threshold_mutation.py`
- `threshold_search.py`
- `asset_library.py`
- `asset_scoring.py`
- `conformance.py`

### Discipline / law-enforcement surfaces
- `claim_discipline.py`
- `evaluation_discipline.py`
- `promotion_discipline.py`
- `calibration_discipline.py`

### Reporting / export / operational packs
- `run_report_export.py`
- `history_report_export.py`
- `conformance_report_export.py`
- `artifact_export_smoke.py`
- `artifact_export_pack.py`
- `developer_handoff_pack.py`
- `operator_quickstart.py`
- `release_candidate_smoke.py`
- `all_artifacts_scoreboard.py`
- `artifact_health_report.py`
- `artifact_health_trend.py`
- `repo_verification_report.py`

### CLI
- `src/aurexis_core/cli.py`

### Examples and smoke fixtures
- `examples/visual_sum.png`
- `examples/visual_concat.png`
- `examples/visual_transform.png`
- `examples/sequence_sum/`
- `examples/sequence_branch/`
- `examples/conformance_asset_manifest.json`
- `examples/smoke_asset_manifest.json`
- `examples/manual_repo_verification_v80.json`

### Tests
There are 154 tests collected in V80. The tests cover many of the repo surfaces and should be treated as major navigational anchors.

---

## 15. Practical commands

### Environment
The repo uses:
- Python `>=3.10`
- package name: `aurexis-core`
- dependency: `Pillow>=10.0`

### Basic install
```bash
python -m venv .venv
source .venv/bin/activate    # or Windows equivalent
pip install -U pip
pip install -e .
pip install pytest
```

### Basic commands
```bash
python -m aurexis_core.cli cycle0
python -m aurexis_core.cli scenario F2
python -m aurexis_core.cli visual examples/visual_sum.png
python -m aurexis_core.cli visual-sequence examples/sequence_sum
```

### Report and pack examples
```bash
python -m aurexis_core.cli run-report-smoke --format markdown
python -m aurexis_core.cli history-report-smoke --format markdown
python -m aurexis_core.cli conformance-report-smoke --format markdown
python -m aurexis_core.cli artifact-export-pack-smoke --format markdown
python -m aurexis_core.cli release-candidate-smoke --format markdown
```

### Repo verification
```bash
python -m aurexis_core.cli repo-verification --format markdown --output-dir out/repo_verification
```

### Pytest
```bash
pytest -q
```

If a local environment struggles with one huge run, deterministic batched verification is acceptable and already part of the recent repo history.

---

## 16. Current recommended next milestone

If continuing from V80, the strongest next real seam is:

### Push repo-verification truth upward into the top-level operational surfaces
Specifically:
- release-candidate surfaces
- scoreboard surfaces
- artifact-health surfaces
- outward-facing pack lineage

Reason:
V80 added a first-class verification surface, but the top-level pack/report/health layers can still under-express whether the repo is actually verified.

The next good pass would make the highest-level artifacts say, in a lawful and inheritable way:
- whether the repo verification surface ran
- how strong that proof is
- whether proof is monolithic vs batched vs delta-only
- which areas remain unproven or only partially re-proven

This is a strong next move because it tightens the honesty surface of the repo without pretending the deepest machine-vision problems are solved.

---

## 17. Known incomplete areas / danger zones

A local model must not drift into false completion here.

### Incomplete by design or by current state
- final relation algebra is not finished
- final world-anchor evolution rules are not finished
- stronger multi-frame/world anchoring is incomplete
- full raw-video/live-camera machine-vision runtime is incomplete
- deeper physical-world trust is incomplete
- final transform-heavy semantics are incomplete
- full final language implementation against Vincent’s long-term vision is incomplete

### Common drift risks
Do **not** drift into:
- overclaiming that the current prototype already equals human-like machine vision
- collapsing Core into an encoder/decoder product
- pretending the current repo law already solves all world-image inference problems
- adding flashy but irrelevant UI/product layers
- “finishing” things by writing summaries instead of proving surfaces in code/tests
- broad speculative frameworks that do not improve the real next seam

---

## 18. Required working style for the local model

This matters a lot.

### Behavior contract
The model should behave like this:
- infer from the project truth and current repo shape
- do not guess casually
- if uncertain, mark uncertainty honestly
- if a question would materially change project law, ask Vincent
- otherwise continue until the next real stop
- avoid both bottlenecking and overexpanding
- do not fake progress
- do not inflate percentages or claim proof that was not earned
- prefer meaningful full-package passes over tiny loose patches whenever practical

### Reporting format contract
Every real progress report should include:
1. current state
2. what changed
3. what was verified
4. honest limit
5. largest-scale tracker with percentages
6. dumbed-down summary
7. best recommended next step

### Wording / style contract
- direct language is preferred over fluffy framing
- keep things operational and concrete
- no fake certainty
- no long philosophical lectures unless they directly change project law
- progress should be organized around **done vs left**

### Clarification contract
Ask questions only when they are high-value and project-defining.
If you need to ask one, put it right before the best recommended next step.

---

## 19. User-specific preferences that matter for this project

These are important because a local model will not infer them automatically.

- User prefers concise, direct communication by default.
- User prefers dense formatting with less wasted space.
- User wants a **best recommended next step** every time.
- User also now wants a **dumbed-down summary** before the best recommended next step.
- User wants honest tracking of what is done vs what is left.
- User likes progress percentages when they are meaningful.
- User wants no fake completion theater.
- User wants installable/full-package style handoffs when practical, not lots of tiny patches.
- User wants minimal friction and minimal manual file-combining work.
- User prefers the project name **Aurexis**; old `Aurex` naming is obsolete.
- When the user says something is “finalized,” the better interpretation is usually “intended full package pending validation,” not absolute completion.
- Scope-broadening ideas that do not directly improve viability should usually be deferred.
- For Aurexis Core specifically, the active path is **Core-first**, not E/D-first.
- The user wants future conceptual definitions concretized into actual code when feasible, not left as theory forever.

---

## 20. Ownership / attribution / licensing

Treat these as active project truths unless Vincent changes them.

### Ownership
Vincent is the sole inventor and owner of:
- the original Aurexis visual encoding system
- the new Aurexis Core visual coding language

### Copyright notice preference
Use notices like:

```text
© 2026 Vincent — Aurexis Core. All rights reserved for the core concept and implementation.
```

### License preference
For open-source portions, default working language has been:

```text
MIT for open-source portions; core concept and implementation rights reserved by Vincent.
```

Do **not** attribute authorship of the project to the model.

---

## 21. Safety / red-line constraint

This is non-negotiable.

If any future work touches encoding/decoding or payload transport, the system must maintain a hard block against:
- child sexual abuse material
- sexual exploitation material involving minors
- any encoding, conversion, transport, or support for such material

This is a standing project safety rule.

---

## 22. What the local model should do first after reading this

If the repo is attached, the model should:
1. read this handoff fully
2. inspect `README.md`, `AUREXIS_CORE_LANGUAGE_RUNTIME_V80_STATUS.md`, and `docs/V80_FULL_REPO_VERIFICATION.md`
3. inspect the current top-level operational surfaces and the new verification surface
4. determine the next real seam after V80
5. continue with a real, testable pass

If the repo is **not** attached, the model should:
1. acknowledge that it understands the project law and direction from this handoff
2. state what it can do conceptually now
3. state that actual code continuation requires the V80 repo

---

## 23. Short local-model checklist

Before the model starts coding, it should be able to say “yes” to all of these:

- I understand that Aurexis Core is the active target, not E/D.
- I understand that Core is world-anchored, image-accessed, and validation-gated.
- I understand what a phoxel is in this project.
- I understand the illegal-inference law.
- I understand that current-tech feasibility is mandatory.
- I understand that future scalability is also mandatory.
- I understand that the current repo is meaningful substrate, not final project completion.
- I understand the V79 repair and V80 verification additions.
- I understand the required reporting format.
- I understand that I should continue from the next real seam only.

---

## 24. Bottom-line summary for the local model

Aurexis Core is a world-anchored, image-accessed, physics-grounded machine-vision language project. The current repo is a serious prototype substrate with real law-facing runtime code, strong reporting/export infrastructure, repaired fixture lineage, and a newly added repo verification surface. It is not yet the final embodiment of Vincent’s full vision. Continue from the next real seam honestly, preserve the project law, verify what you change, and report in the required format.

