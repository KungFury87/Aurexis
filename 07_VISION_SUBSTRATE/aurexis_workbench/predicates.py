"""Predicate AST + compiler + type-checker.

A *predicate* is a typed composition of operators over a FieldBundle.
The AST has three node types:

    FieldRef(name)        -> resolves to bundle[name].value at runtime
    Const(value, dtype)   -> a literal of declared dtype
    Call(op, args)        -> calls a registered operator

Type-checking walks the tree, resolves FieldRef dtypes against an
expected-bundle schema, resolves Const dtypes from the spec, and
checks every Call against the operator registry's in_types/out_type.
A type-checked tree compiles to a Python callable
``compiled(bundle) -> value``.

The dtype inferred for the whole tree is the predicate's *return
type*. Most language-relevant predicates return bool (yes/no), but a
predicate can return scalar/int/label too — useful for predicates
that *measure* rather than gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from .fields import FieldBundle, VALID_DTYPES
from . import operators as ops


# =================================================================
# AST
# =================================================================

@dataclass
class FieldRef:
    name: str
    kind: str = "field_ref"


@dataclass
class Const:
    value: Any
    dtype: str
    kind: str = "const"

    def __post_init__(self):
        if self.dtype not in VALID_DTYPES:
            raise ValueError("unknown const dtype: " + repr(self.dtype))


@dataclass
class Call:
    op: str
    args: List[Any] = field(default_factory=list)
    kind: str = "call"


PredNode = Union[FieldRef, Const, Call]


# =================================================================
# Predicate
# =================================================================

@dataclass
class Predicate:
    name: str
    body: PredNode
    expects: Dict[str, str] = field(default_factory=dict)
    intent: str = ""
    return_type: Optional[str] = None
    source: str = ""


# =================================================================
# Type-checker
# =================================================================

class TypeError_(Exception):
    pass


def infer_type(node: PredNode, expects: Dict[str, str]) -> str:
    if isinstance(node, FieldRef):
        if node.name not in expects:
            raise TypeError_("FieldRef '" + node.name +
                              "' has no declared type in 'expects'.")
        t = expects[node.name]
        if t not in VALID_DTYPES:
            raise TypeError_("unknown dtype for field '" + node.name +
                              "': " + repr(t))
        return t
    if isinstance(node, Const):
        return node.dtype
    if isinstance(node, Call):
        sig = ops.get(node.op)
        if len(node.args) != len(sig.in_types):
            raise TypeError_("op '" + node.op + "' expects "
                              + str(len(sig.in_types))
                              + " args, got "
                              + str(len(node.args)))
        for i, (arg, want) in enumerate(zip(node.args, sig.in_types)):
            got = infer_type(arg, expects)
            if got != want:
                raise TypeError_("op '" + node.op + "' arg " + str(i)
                                  + " expects " + repr(want)
                                  + " got " + repr(got))
        return sig.out_type
    raise TypeError_("unknown node type: " + repr(type(node).__name__))


def type_check(pred: Predicate) -> str:
    rt = infer_type(pred.body, pred.expects)
    if pred.return_type is not None and pred.return_type != rt:
        raise TypeError_("predicate '" + pred.name
                          + "' declares return_type=" + repr(pred.return_type)
                          + " but body infers " + repr(rt))
    pred.return_type = rt
    return rt


# =================================================================
# Compiler / executor
# =================================================================

def _eval(node: PredNode, bundle: FieldBundle) -> Any:
    if isinstance(node, FieldRef):
        return bundle.get(node.name).value
    if isinstance(node, Const):
        return node.value
    if isinstance(node, Call):
        sig = ops.get(node.op)
        evald = [_eval(a, bundle) for a in node.args]
        return sig.fn(*evald)
    raise RuntimeError("unknown node type: " + repr(type(node).__name__))


def compile_predicate(pred: Predicate):
    """Type-check + return a callable[FieldBundle -> value]."""
    type_check(pred)

    def runner(bundle: FieldBundle):
        # Verify bundle has the expected fields with matching dtypes.
        for nm, want in pred.expects.items():
            if not bundle.has(nm):
                raise KeyError("bundle is missing field '" + nm
                                + "' required by predicate '"
                                + pred.name + "'")
            got = bundle.get(nm).dtype
            if got != want:
                raise TypeError_("bundle field '" + nm
                                  + "' dtype " + repr(got)
                                  + " != predicate expects "
                                  + repr(want))
        return _eval(pred.body, bundle)
    return runner


# =================================================================
# Construction helpers / serialisation
# =================================================================

def field_(name: str) -> FieldRef:
    return FieldRef(name=name)


def const(value, dtype: str) -> Const:
    return Const(value=value, dtype=dtype)


def call(op: str, *args) -> Call:
    return Call(op=op, args=list(args))


def to_dict(node: PredNode) -> Dict[str, Any]:
    if isinstance(node, FieldRef):
        return {"kind": "field_ref", "name": node.name}
    if isinstance(node, Const):
        return {"kind": "const", "value": node.value,
                "dtype": node.dtype}
    if isinstance(node, Call):
        return {"kind": "call", "op": node.op,
                "args": [to_dict(a) for a in node.args]}
    raise ValueError("unknown node type")


def from_dict(d: Dict[str, Any]) -> PredNode:
    k = d.get("kind")
    if k == "field_ref":
        return FieldRef(name=str(d["name"]))
    if k == "const":
        return Const(value=d["value"], dtype=str(d["dtype"]))
    if k == "call":
        return Call(op=str(d["op"]),
                    args=[from_dict(a) for a in d.get("args", [])])
    raise ValueError("unknown node kind: " + repr(k))


def predicate_to_dict(p: Predicate) -> Dict[str, Any]:
    return {
        "name":        p.name,
        "intent":      p.intent,
        "expects":     dict(p.expects),
        "return_type": p.return_type,
        "body":        to_dict(p.body),
        "source":      p.source,
    }


def predicate_from_dict(d: Dict[str, Any]) -> Predicate:
    p = Predicate(
        name=str(d["name"]),
        body=from_dict(d["body"]),
        expects=dict(d.get("expects", {})),
        intent=str(d.get("intent", "")),
        return_type=d.get("return_type"),
        source=str(d.get("source", "")),
    )
    return p
