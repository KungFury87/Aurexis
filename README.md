# Aurexis Core — Project Workspace
**Owner:** Vincent Anderson
**Current Version:** V86
**Quick status:** Gate 2 in progress | Gate 3 blocked on camera bridge | Gate 4 kickoff started

---

## Folder Structure

```
📁 00_PROJECT_CORE/          ← START HERE — master status, law reference, plain-language overview
   PROJECT_STATUS.md          ← Master project status, gate tracker, honest completion %
   CORE_LAW_REFERENCE.md      ← All 7 frozen law sections in condensed form
   WHAT_AUREXIS_IS.md         ← Plain language explanation of what this project is

📁 01_RELEASES/               ← All release zips organized by version
   RELEASE_HISTORY.md         ← What changed in each version
   V84/                       ← Aurexis_Core_V84_Execution_Runtime_Status.zip
   V85/                       ← Aurexis_Core_V85_Core_Audit_Drop.zip
   V86/                       ← Aurexis_Core_V86_Control_Mutation_Runtime_Status.zip ← LATEST
   LEGACY_V81ISH/             ← Older cleanup track zips + demo prototype

📁 02_GATE_TRACKING/          ← Status of each development gate
   GATE_1/  ✅ COMPLETE        ← Core law frozen at V20
   GATE_2/  🔄 IN PROGRESS    ← Runtime obeys law — V86 is latest pass
   GATE_3/  🟡 INFRA READY    ← Blocked on camera bridge / real capture
   GATE_4/  🟡 KICKOFF DONE   ← Narrow mobile demo — not yet demonstrated

📁 03_HANDOFFS_AND_CONTEXT/   ← AI handoffs, conversation exports, project memory
   HANDOFF_INDEX.md           ← How to use these files for new AI sessions
   AUREXIS_CORE_OLLAMA_QWEN30B_HANDOFF_V80.md  ← Master project briefing
   ChatGPT-Aurexis ONLY.json  ← Primary development conversation (146 messages)
   ChatGPT-*.json             ← Other session exports

📁 04_WORKING_SESSIONS/       ← Log of what happened in each session
   SESSION_LOG.md             ← Running log — add an entry after each meaningful session
```

---

## Quick Start for a New AI Session

1. Read `00_PROJECT_CORE/PROJECT_STATUS.md` — understand current gate status and what's done
2. Read `03_HANDOFFS_AND_CONTEXT/AUREXIS_CORE_OLLAMA_QWEN30B_HANDOFF_V80.md` — project law and working style
3. Extract the latest release zip from `01_RELEASES/V86/`
4. Check `02_GATE_TRACKING/GATE_2/GATE_2_STATUS.md` for current focus
5. Continue from the next real seam — do not redo completed work

**Current next real seam:** Complete the camera bridge (`camera_bridge_stub.py` → real OpenCV capture)

---

## What NOT to do

- Do not claim Gate 3 earned evidence without REAL_CAPTURE tier inputs
- Do not modify anything in `02_GATE_TRACKING/GATE_1/` — Gate 1 is frozen
- Do not expand toward Aurexis E/D — that is deferred downstream
- Do not fake progress or inflate completion percentages
- Do not add speculative features that don't directly advance the next gate

---

## Ownership

© 2026 Vincent Anderson — Aurexis Core. All rights reserved for the core concept and implementation.
