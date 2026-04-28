"""Structured diff between two vision_vocab.json snapshots.

Usage:
    python -m aurexis_workbench.vocab_diff <OLD_JSON> <NEW_JSON>

Reports:
  - predicates added / removed
  - body text changed (different DSL expression)
  - intent renamed
  - expects clause changed (different field types)
  - return_type changed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_vocab(path: str | Path) -> Dict[str, dict]:
    """Returns {predicate_name: predicate_dict}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for p in data.get("predicates", []):
        out[p["name"]] = p
    return out


def _ast_to_str(node: Any) -> str:
    """Render a predicate AST sub-tree as a stable canonical string."""
    if not isinstance(node, dict):
        return repr(node)
    kind = node.get("kind")
    if kind == "field_ref":
        return f"@{node['name']}"
    if kind == "const":
        return f"{node.get('dtype', '?')}({node.get('value')!r})"
    if kind == "call":
        op = node.get("op", "?")
        args = ",".join(_ast_to_str(a) for a in node.get("args", []))
        return f"{op}({args})"
    return repr(node)


def diff_vocabularies(old_path: str | Path,
                        new_path: str | Path) -> Dict[str, Any]:
    old = _load_vocab(old_path)
    new = _load_vocab(new_path)
    old_names = set(old)
    new_names = set(new)
    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    common = sorted(old_names & new_names)
    body_changed: List[Tuple[str, str, str]] = []
    intent_changed: List[Tuple[str, str, str]] = []
    expects_changed: List[Tuple[str, str, str]] = []
    return_type_changed: List[Tuple[str, str, str]] = []
    for n in common:
        a, b = old[n], new[n]
        a_body = _ast_to_str(a.get("body"))
        b_body = _ast_to_str(b.get("body"))
        if a_body != b_body:
            body_changed.append((n, a_body, b_body))
        if a.get("intent") != b.get("intent"):
            intent_changed.append((n, a.get("intent", ""), b.get("intent", "")))
        if a.get("expects") != b.get("expects"):
            expects_changed.append((n,
                                      str(a.get("expects", {})),
                                      str(b.get("expects", {}))))
        if a.get("return_type") != b.get("return_type"):
            return_type_changed.append((n,
                                          a.get("return_type", "?"),
                                          b.get("return_type", "?")))
    return {
        "old_path":            str(old_path),
        "new_path":            str(new_path),
        "old_count":           len(old),
        "new_count":           len(new),
        "added":               added,
        "removed":             removed,
        "body_changed":        body_changed,
        "intent_changed":      intent_changed,
        "expects_changed":     expects_changed,
        "return_type_changed": return_type_changed,
    }


def render_diff(d: Dict[str, Any]) -> str:
    L = []
    L.append(f"vocab diff: {d['old_path']} -> {d['new_path']}")
    L.append(f"  {d['old_count']} -> {d['new_count']} predicates")
    L.append("")
    if d["added"]:
        L.append(f"+ ADDED ({len(d['added'])}):")
        for n in d["added"]:
            L.append(f"    + {n}")
        L.append("")
    if d["removed"]:
        L.append(f"- REMOVED ({len(d['removed'])}):")
        for n in d["removed"]:
            L.append(f"    - {n}")
        L.append("")
    if d["body_changed"]:
        L.append(f"~ BODY CHANGED ({len(d['body_changed'])}):")
        for n, a, b in d["body_changed"]:
            L.append(f"    ~ {n}")
            L.append(f"        old: {a}")
            L.append(f"        new: {b}")
        L.append("")
    if d["intent_changed"]:
        L.append(f"~ INTENT RENAMED ({len(d['intent_changed'])}):")
        for n, a, b in d["intent_changed"]:
            L.append(f"    ~ {n}: {a} -> {b}")
        L.append("")
    if d["expects_changed"]:
        L.append(f"~ EXPECTS CHANGED ({len(d['expects_changed'])}):")
        for n, a, b in d["expects_changed"]:
            L.append(f"    ~ {n}: {a} -> {b}")
        L.append("")
    if d["return_type_changed"]:
        L.append(f"~ RETURN TYPE CHANGED ({len(d['return_type_changed'])}):")
        for n, a, b in d["return_type_changed"]:
            L.append(f"    ~ {n}: {a} -> {b}")
        L.append("")
    if not any([d["added"], d["removed"], d["body_changed"],
                  d["intent_changed"], d["expects_changed"],
                  d["return_type_changed"]]):
        L.append("(no changes)")
    return "\n".join(L)


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print("usage: python -m aurexis_workbench.vocab_diff OLD.json NEW.json")
        return 1
    d = diff_vocabularies(argv[0], argv[1])
    print(render_diff(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
