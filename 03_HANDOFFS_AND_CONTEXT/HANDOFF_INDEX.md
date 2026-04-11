# Handoffs & Context — Index

This folder contains all AI session handoffs, continuation setups, and conversation exports.
These are the "memory" of the project across AI sessions.

---

## Files

### AUREXIS_CORE_OLLAMA_QWEN30B_HANDOFF_V80.md
**Type:** Structured handoff document for local AI models
**Created at:** V80
**Purpose:** Full project briefing including: what Aurexis Core is, core law, phoxel definition,
feasibility law, project identity, working style contract, reporting format contract,
user preferences, ownership, and safety rules.

**Key sections to read:**
- Section 1: Canonical project identity
- Section 5: The phoxel definition
- Section 4: Feasibility law (current-tech floor / future-tech ceiling)
- Section 18: Required working style
- Section 19: User-specific preferences
- Section 20: Ownership / attribution

**This is the master project briefing document. Any AI continuing this project should read this first.**

---

### ChatGPT-Aurexis ONLY.json
**Type:** Exported ChatGPT conversation (146 messages)
**Purpose:** Primary development conversation history — contains the actual development dialogue
that produced Gates 1 through part of Gate 3. The working history of the project.

---

### ChatGPT-JSON Continuation and Analysis.json
**Type:** Exported ChatGPT conversation
**Purpose:** Analysis and continuation setup session.

---

### ChatGPT-Project Continuation Setup.json
**Type:** Exported ChatGPT conversation (10 messages)
**Purpose:** Latest continuation setup — contains current project state context
for handing off to a new AI session.

---

## How to use these when starting a new AI session

1. Give the AI `AUREXIS_CORE_OLLAMA_QWEN30B_HANDOFF_V80.md` first as the project law document.
2. Point it to `00_PROJECT_CORE/PROJECT_STATUS.md` for current gate status.
3. Point it to the latest release zip in `01_RELEASES/` for the actual code.
4. Tell it to continue from the next real seam only (do not re-do completed work).
5. Use the reporting format: current state / what changed / what verified / honest limit / tracker % / plain summary / best next step.
