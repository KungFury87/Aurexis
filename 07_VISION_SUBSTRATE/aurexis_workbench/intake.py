"""Candidate predicate intake + before/after Independence Ratio.

Reads a `.aurex` file containing candidate predicate blocks, parses
them with the v2.1 surface DSL, accepts those that pass parse + type-
check, rejects those that don't (with diagnostics), then runs the IR
runner twice: once on a baseline vocabulary, once on the baseline
extended with the accepted candidates. Returns a single dossier
that captures parsing diagnostics, accept/reject lists, and the IR
delta — i.e. how much the authoring step actually moved the
substrate's coverage.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import dsl
from . import vocabulary as V
from . import predicates as P
from . import scenarios as S
from . import independence as I
from .starter import build_starter_vocabulary, build_runtime_tasks


def parse_intake_file(path) -> List[dsl.ParsedPredicate]:
    text = Path(path).read_text(encoding="utf-8")
    return dsl.parse_source(text)


def split_results(results: List[dsl.ParsedPredicate]
                    ) -> Dict[str, List[dsl.ParsedPredicate]]:
    accepted = [r for r in results if r.ok]
    rejected = [r for r in results if not r.ok]
    return {"accepted": accepted, "rejected": rejected}


def extend_vocabulary(baseline: V.Vocabulary,
                        accepted: List[dsl.ParsedPredicate]
                        ) -> V.Vocabulary:
    """Return baseline ∪ accepted (deep-copied; baseline is not mutated)."""
    out = V.Vocabulary(name=baseline.name + "+intake")
    for nm, p in baseline.items.items():
        out.items[nm] = p
    for r in accepted:
        if r.pred is None:
            continue
        out.items[r.pred.name] = r.pred
    return out


def _run_ir(vocab: V.Vocabulary,
              bundle_by_name: Dict[str, Any],
              tasks: List[I.RuntimeTask]) -> Dict[str, Any]:
    return I.run_independence(vocab, tasks, bundle_by_name)


def build_intake_dossier(intake_path,
                            baseline: Optional[V.Vocabulary] = None,
                            tasks: Optional[List[I.RuntimeTask]] = None
                            ) -> Dict[str, Any]:
    baseline = baseline or build_starter_vocabulary()
    tasks = tasks or build_runtime_tasks()

    bundles = S.build_all()
    bundle_by_name = {b.name: b for b in bundles}

    parsed = parse_intake_file(intake_path)
    split = split_results(parsed)
    extended = extend_vocabulary(baseline, split["accepted"])

    ir_before = _run_ir(baseline, bundle_by_name, tasks)
    ir_after = _run_ir(extended, bundle_by_name, tasks)

    # IR delta breakdown
    before_status = {(r["scenario"], r["goal_key"]): r["status"]
                       for r in ir_before["results"]}
    after_status = {(r["scenario"], r["goal_key"]): r["status"]
                       for r in ir_after["results"]}
    transitions = []
    for k in sorted(before_status.keys()):
        b = before_status[k]
        a = after_status.get(k, "?")
        if b != a:
            transitions.append({
                "scenario": k[0], "goal_key": k[1],
                "before": b, "after": a,
            })

    return {
        "schema_version":   "workbench-2.1-intake",
        "intake_path":      str(intake_path),
        "baseline_vocab":   baseline.name,
        "extended_vocab":   extended.name,
        "candidate_count":  len(parsed),
        "accepted":         [
            {"name": r.name,
             "return_type": (r.pred.return_type if r.pred else None),
             "intent": (r.pred.intent if r.pred else "")}
            for r in split["accepted"]
        ],
        "rejected":         [
            {"name": r.name,
             "diagnostics": [d.render() for d in r.diagnostics]}
            for r in split["rejected"]
        ],
        "ir_before":        ir_before,
        "ir_after":         ir_after,
        "ir_delta": {
            "answered_before":      ir_before["answered"],
            "answered_after":       ir_after["answered"],
            "answered_delta":       ir_after["answered"]
                                       - ir_before["answered"],
            "uncovered_before":     ir_before["uncovered"],
            "uncovered_after":      ir_after["uncovered"],
            "uncovered_delta":      ir_after["uncovered"]
                                       - ir_before["uncovered"],
            "ir_before":            ir_before["independence_ratio"],
            "ir_after":             ir_after["independence_ratio"],
            "ir_delta":             (
                (ir_after["independence_ratio"]
                  - ir_before["independence_ratio"])
                if (isinstance(ir_before["independence_ratio"], float)
                     and ir_before["independence_ratio"]
                         == ir_before["independence_ratio"]
                     and isinstance(ir_after["independence_ratio"], float)
                     and ir_after["independence_ratio"]
                         == ir_after["independence_ratio"])
                else None
            ),
        },
        "transitions":      transitions,
    }
