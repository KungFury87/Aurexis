# What Aurexis Core Is — Plain Language Summary

**Owner:** Vincent Anderson
**Purpose:** Reference document for anyone (AI or human) picking this project up

---

## The one-sentence version

Aurexis Core is a programming language where the data type is *visual evidence from the physical world* — not text, not numbers, but pixel-grounded observations from a camera.

---

## The fuller version

Normal programming languages process text or numbers. Aurexis Core processes what a camera sees. Every "variable" is a visual observation. Every "value" is backed by pixel coordinates, a timestamp, and a chain of evidence proving the observation is real.

The system exists to answer the question: *how do you make a computer understand the visual world in a way that is lawful, honest, and grounded in physical reality rather than AI guesswork?*

The answer Aurexis Core gives: you build a language where the rules of evidence are baked into the type system itself. A claim about the visual world is only valid if you can prove it from pixel data. You can't skip steps, you can't hallucinate observations, and you can't claim certainty you didn't earn.

---

## What it is NOT

- Not a normal image processing library
- Not an AI vision wrapper
- Not a product or app (those come later, built on top of Core)
- Not "Aurexis E/D" — that is a downstream, deferred concept
- Not finished

---

## The phoxel

The atomic unit of Aurexis Core is the **phoxel** — photon + pixel bridge object.

A phoxel is the smallest machine-usable unit where physical light, observed image position, world-side spatial meaning, and relation to nearby structure all meet in one object. It is not just a pixel value. It is the machine equivalent of a human noticing something specific in their field of vision and being able to point to exactly where and when they saw it.

---

## The long-term vision

- File → image → file workflows using ordinary phone cameras
- Stronger offline camera-based interpretation
- Robot vision that operates more like true visual understanding
- Visual analysis systems that interpret the world more like humans do
- Future software ecosystems built on top of Aurexis Core as the vision law layer

Core itself = the language/law layer.
Future apps built on Core = downstream applications. Do not collapse the two.

---

## Why the rules are so strict

The core law is strict because the failure mode of visual AI — claiming to see things it didn't, asserting certainty it didn't earn, confusing resemblance with identity — is exactly what makes current machine vision untrustworthy in the real world.

Aurexis Core is built with the philosophy that the solution isn't to build a more confident AI. It's to build a language that makes false confidence structurally impossible.

That is the actual innovation. Not the computer vision techniques. Not the mobile optimization. The law itself.

---

## Current state (April 2026)

The core law is frozen and fully implemented. The runtime enforcement chain works and is tested. The system is on Gate 2 (runtime obeys law) and has kicked off Gate 4 (narrow mobile demo). The gap between "the law engine works" and "a deployable product exists" is still significant, but the foundation is genuinely solid and the architecture is right.

The next critical unlock is real camera integration — connecting a live camera to the pipeline to produce REAL_CAPTURE tier evidence, which unblocks Gate 3.
