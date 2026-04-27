"""Predicate runtime.

Compiles and caches predicates and evaluates them against
FieldBundles. Tracks per-evaluation outcomes for downstream
independence-ratio reporting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .fields import FieldBundle
from . import predicates as P


@dataclass
class EvalRecord:
    predicate: str
    bundle: str
    return_type: str
    value: Any
    error: Optional[str] = None


class Runtime:
    def __init__(self):
        self._compiled: Dict[str, Callable[[FieldBundle], Any]] = {}
        self._return_types: Dict[str, str] = {}
        self._records: List[EvalRecord] = []

    def install(self, pred: P.Predicate) -> None:
        self._compiled[pred.name] = P.compile_predicate(pred)
        self._return_types[pred.name] = pred.return_type or "?"

    def evaluate(self, pred_name: str,
                  bundle: FieldBundle) -> EvalRecord:
        if pred_name not in self._compiled:
            rec = EvalRecord(predicate=pred_name, bundle=bundle.name,
                              return_type="?", value=None,
                              error="not_installed")
            self._records.append(rec)
            return rec
        try:
            v = self._compiled[pred_name](bundle)
            rec = EvalRecord(predicate=pred_name, bundle=bundle.name,
                              return_type=self._return_types[pred_name],
                              value=v)
        except Exception as e:
            rec = EvalRecord(predicate=pred_name, bundle=bundle.name,
                              return_type=self._return_types.get(pred_name, "?"),
                              value=None, error=str(e))
        self._records.append(rec)
        return rec

    def evaluate_all(self, bundles: List[FieldBundle]
                       ) -> List[EvalRecord]:
        out: List[EvalRecord] = []
        for b in bundles:
            for nm in self._compiled:
                out.append(self.evaluate(nm, b))
        return out

    def installed(self) -> List[str]:
        return list(self._compiled.keys())

    @property
    def records(self) -> List[EvalRecord]:
        return list(self._records)

    def reset_records(self) -> None:
        self._records.clear()
