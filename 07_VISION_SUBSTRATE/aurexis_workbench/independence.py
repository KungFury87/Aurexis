"""Independence Ratio runner.

A *runtime task* is a (scenario, goal) pair: "given this scenario,
answer this goal." Goals are encoded as goal_keys (strings) — names
that the vocabulary's predicates declare in their `intent` or
`name`. The IR runner:

  1. For each task, look up a vocabulary predicate that claims to
     answer the goal_key. If no predicate matches, the task is
     UNCOVERED — it requires new authorship.
  2. If a predicate matches, evaluate it against the scenario's
     bundle. If it returns a meaningful value (no error, and bool
     truth matches the scenario's declared truth), the task is
     ANSWERED. If it returns the wrong value or errors, the task is
     COVERED_BUT_WRONG.
  3. The Independence Ratio is ANSWERED / TOTAL.

Coverage breakdown:

    ANSWERED              vocabulary contains a predicate that
                           returns the right value.
    COVERED_BUT_WRONG     vocabulary contains a predicate but it
                           returns the wrong value or errored.
    UNCOVERED             no predicate in the vocabulary claims
                           the goal_key.

This is a deliberately strict definition. A vocabulary that
"covers" a task by returning the wrong answer is not credit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .fields import FieldBundle
from . import vocabulary as V
from . import runtime as RT


@dataclass
class RuntimeTask:
    scenario: str
    goal_key: str
    expected: Any
    description: str = ""


@dataclass
class TaskResult:
    task: RuntimeTask
    status: str           # "ANSWERED" | "COVERED_BUT_WRONG" | "UNCOVERED"
    predicate: Optional[str] = None
    actual: Any = None
    error: Optional[str] = None


def _find_predicate_for(goal_key: str,
                          vocab: V.Vocabulary) -> Optional[str]:
    """Return the first predicate name whose intent or name matches
    the goal_key; or None if the vocabulary has no candidate."""
    if vocab.has(goal_key):
        return goal_key
    for nm, p in vocab.items.items():
        if p.intent.strip() == goal_key:
            return nm
    return None


def run_independence(vocab: V.Vocabulary,
                       tasks: List[RuntimeTask],
                       bundle_by_name: Dict[str, FieldBundle]
                       ) -> Dict[str, Any]:
    rt = RT.Runtime()
    vocab.install_into(rt)

    results: List[TaskResult] = []
    for t in tasks:
        if t.scenario not in bundle_by_name:
            results.append(TaskResult(task=t, status="UNCOVERED",
                                        error="scenario not provided"))
            continue
        bundle = bundle_by_name[t.scenario]

        pred_name = _find_predicate_for(t.goal_key, vocab)
        if pred_name is None:
            results.append(TaskResult(task=t, status="UNCOVERED"))
            continue

        rec = rt.evaluate(pred_name, bundle)
        if rec.error:
            results.append(TaskResult(task=t,
                                        status="COVERED_BUT_WRONG",
                                        predicate=pred_name,
                                        actual=None,
                                        error=rec.error))
            continue
        actual = rec.value
        if actual == t.expected:
            results.append(TaskResult(task=t, status="ANSWERED",
                                        predicate=pred_name,
                                        actual=actual))
        else:
            results.append(TaskResult(task=t,
                                        status="COVERED_BUT_WRONG",
                                        predicate=pred_name,
                                        actual=actual))

    n_total = len(results)
    n_answered = sum(1 for r in results if r.status == "ANSWERED")
    n_covered_wrong = sum(1 for r in results
                              if r.status == "COVERED_BUT_WRONG")
    n_uncovered = sum(1 for r in results
                          if r.status == "UNCOVERED")
    ir = (float(n_answered) / float(n_total)
            if n_total > 0 else float("nan"))

    return {
        "schema_version":           "workbench-2.0",
        "vocabulary":               vocab.name,
        "predicate_count":          len(vocab.items),
        "task_count":               n_total,
        "answered":                 n_answered,
        "covered_but_wrong":        n_covered_wrong,
        "uncovered":                n_uncovered,
        "independence_ratio":       ir,
        "results":                  [
            {"scenario":  r.task.scenario,
             "goal_key":  r.task.goal_key,
             "status":    r.status,
             "predicate": r.predicate,
             "expected":  r.task.expected,
             "actual":    r.actual,
             "error":     r.error}
            for r in results
        ],
    }
