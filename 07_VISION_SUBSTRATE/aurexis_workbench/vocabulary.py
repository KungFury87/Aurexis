"""Vocabulary store.

A vocabulary is a named, persisted set of predicates. Predicates
register into the vocabulary by name; loading the vocabulary into a
runtime installs all of them. The store is a small JSON file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from . import predicates as P


@dataclass
class Vocabulary:
    name: str = "default"
    items: Dict[str, P.Predicate] = None

    def __post_init__(self):
        if self.items is None:
            self.items = {}

    def add(self, pred: P.Predicate) -> None:
        # Type-check before accepting.
        P.type_check(pred)
        self.items[pred.name] = pred

    def remove(self, name: str) -> None:
        self.items.pop(name, None)

    def has(self, name: str) -> bool:
        return name in self.items

    def list_names(self) -> List[str]:
        return sorted(self.items.keys())

    def to_dict(self) -> dict:
        return {
            "schema_version": "workbench-2.0",
            "name": self.name,
            "predicates": [P.predicate_to_dict(p)
                            for p in self.items.values()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Vocabulary":
        v = cls(name=str(d.get("name", "default")))
        for pd in d.get("predicates", []):
            v.add(P.predicate_from_dict(pd))
        return v

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2),
                                encoding="utf-8")

    @classmethod
    def load(cls, path) -> "Vocabulary":
        return cls.from_dict(json.loads(Path(path).read_text(
            encoding="utf-8")))

    def install_into(self, runtime) -> None:
        for p in self.items.values():
            runtime.install(p)
