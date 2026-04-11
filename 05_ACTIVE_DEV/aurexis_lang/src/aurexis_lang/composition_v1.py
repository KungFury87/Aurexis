"""
Aurexis Core — Composition V1 (FROZEN)

Visual programs that reference other visual programs.
Composability rules under law.

V1 composition defines:
  1. ProgramModule: a named, type-checked, reusable visual program
  2. ModuleReference: a reference from one program to another's bindings
  3. compose(): merge two programs, connecting shared bindings
  4. ProgramLibrary: a collection of named modules

Composition rules:
  - Two modules can be composed if they share binding names
  - Shared bindings must reference compatible primitives (same kind)
  - Composition produces a new program with merged bindings and relations
  - Type checking runs on the composed result

This is NOT function calls or parameterized programs. V1 composition
is structural: merge two sets of spatial assertions into one larger
program. Think of it as "this photograph AND that photograph together
make one bigger program."

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum

from aurexis_lang.visual_grammar_v1 import (
    PrimitiveKind, ExecutionStatus, GRAMMAR_VERSION,
)
from aurexis_lang.visual_parse_rules_v1 import (
    ProgramNodeKind, ProgramNode, PARSE_RULES_VERSION,
)
from aurexis_lang.visual_program_executor_v1 import (
    execute_program, ProgramVerdict, ExecutionResult,
)
from aurexis_lang.type_system_v1 import (
    type_check_program, TypeCheckResult, TypeCheckVerdict,
)


# ════════════════════════════════════════════════════════════
# COMPOSITION VERSION
# ════════════════════════════════════════════════════════════

COMPOSITION_VERSION = "V1.0"
COMPOSITION_FROZEN = True


# ════════════════════════════════════════════════════════════
# PROGRAM MODULE — a named, reusable visual program
# ════════════════════════════════════════════════════════════

@dataclass
class ProgramModule:
    """
    A named visual program that can be composed with others.

    A module wraps a ProgramNode tree and adds:
    - A unique name
    - An explicit export list (which bindings are visible to other modules)
    - A type check result (computed at creation time)
    """
    name: str
    program: ProgramNode
    exports: Set[str] = field(default_factory=set)
    type_check: Optional[TypeCheckResult] = None
    module_version: str = COMPOSITION_VERSION

    def __post_init__(self):
        # Auto-compute type check if not provided
        if self.type_check is None:
            self.type_check = type_check_program(self.program)
        # Auto-populate exports from program bindings if empty
        if not self.exports:
            for child in self.program.children:
                if child.kind == ProgramNodeKind.BINDING_STMT:
                    target = child.value.get("target", "")
                    if target:
                        self.exports.add(target)

    @property
    def is_well_typed(self) -> bool:
        return self.type_check is not None and self.type_check.is_well_typed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "exports": sorted(self.exports),
            "is_well_typed": self.is_well_typed,
            "child_count": len(self.program.children),
            "module_version": self.module_version,
        }


# ════════════════════════════════════════════════════════════
# COMPOSITION ERROR
# ════════════════════════════════════════════════════════════

class CompositionErrorKind(str, Enum):
    ILL_TYPED_MODULE = "ILL_TYPED_MODULE"
    BINDING_KIND_MISMATCH = "BINDING_KIND_MISMATCH"
    NO_SHARED_BINDINGS = "NO_SHARED_BINDINGS"
    COMPOSED_ILL_TYPED = "COMPOSED_ILL_TYPED"


@dataclass
class CompositionError:
    kind: CompositionErrorKind
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind.value, "message": self.message, "details": self.details}


# ════════════════════════════════════════════════════════════
# COMPOSITION RESULT
# ════════════════════════════════════════════════════════════

class CompositionVerdict(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class CompositionResult:
    verdict: CompositionVerdict = CompositionVerdict.FAILED
    composed_program: Optional[ProgramNode] = None
    composed_module: Optional[ProgramModule] = None
    shared_bindings: List[str] = field(default_factory=list)
    errors: List[CompositionError] = field(default_factory=list)
    source_modules: List[str] = field(default_factory=list)
    composition_version: str = COMPOSITION_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "shared_bindings": self.shared_bindings,
            "source_modules": self.source_modules,
            "error_count": len(self.errors),
            "errors": [e.to_dict() for e in self.errors],
            "composed_module": self.composed_module.to_dict() if self.composed_module else None,
            "composition_version": self.composition_version,
        }


# ════════════════════════════════════════════════════════════
# COMPOSE — merge two modules
# ════════════════════════════════════════════════════════════

def compose(
    module_a: ProgramModule,
    module_b: ProgramModule,
    require_shared: bool = False,
) -> CompositionResult:
    """
    Compose two program modules into one.

    Composition merges all bindings and relations from both modules.
    If bindings share a name, they must reference the same primitive kind.

    Parameters:
        module_a: First module.
        module_b: Second module.
        require_shared: If True, fail when no shared bindings exist.

    Returns a CompositionResult.
    """
    result = CompositionResult(
        source_modules=[module_a.name, module_b.name],
    )

    # Check both modules are well-typed
    if not module_a.is_well_typed:
        result.errors.append(CompositionError(
            kind=CompositionErrorKind.ILL_TYPED_MODULE,
            message=f"Module '{module_a.name}' is ill-typed",
        ))
    if not module_b.is_well_typed:
        result.errors.append(CompositionError(
            kind=CompositionErrorKind.ILL_TYPED_MODULE,
            message=f"Module '{module_b.name}' is ill-typed",
        ))
    if result.errors:
        return result

    # Find shared bindings
    shared = module_a.exports & module_b.exports
    result.shared_bindings = sorted(shared)

    if require_shared and not shared:
        result.errors.append(CompositionError(
            kind=CompositionErrorKind.NO_SHARED_BINDINGS,
            message=f"Modules '{module_a.name}' and '{module_b.name}' "
                    f"share no binding names",
        ))
        return result

    # Check shared binding kind compatibility
    a_bindings = _extract_binding_kinds(module_a.program)
    b_bindings = _extract_binding_kinds(module_b.program)

    for name in shared:
        a_kind = a_bindings.get(name)
        b_kind = b_bindings.get(name)
        if a_kind and b_kind and a_kind != b_kind:
            result.errors.append(CompositionError(
                kind=CompositionErrorKind.BINDING_KIND_MISMATCH,
                message=f"Shared binding '{name}': "
                        f"{module_a.name} has {a_kind}, "
                        f"{module_b.name} has {b_kind}",
                details={"binding": name, "a_kind": a_kind, "b_kind": b_kind},
            ))

    if result.errors:
        return result

    # Merge: collect all children from both programs
    # Deduplicate bindings for shared names (keep module_a's version)
    merged_children = []
    seen_bindings: Set[str] = set()

    for child in module_a.program.children:
        if child.kind == ProgramNodeKind.BINDING_STMT:
            target = child.value.get("target", "")
            seen_bindings.add(target)
        merged_children.append(child)

    for child in module_b.program.children:
        if child.kind == ProgramNodeKind.BINDING_STMT:
            target = child.value.get("target", "")
            if target in seen_bindings:
                continue  # Skip duplicate binding
        merged_children.append(child)

    # Build composed program
    if merged_children:
        total_conf = sum(c.confidence for c in merged_children) / len(merged_children)
        has_heuristic = any(
            c.execution_status == ExecutionStatus.HEURISTIC_INPUT
            for c in merged_children
        )
    else:
        total_conf = 0.0
        has_heuristic = False

    composed = ProgramNode(
        kind=ProgramNodeKind.PROGRAM,
        value={
            "frame_index": 0,
            "grammar_version": GRAMMAR_VERSION,
            "parse_rules_version": PARSE_RULES_VERSION,
            "total_statements": len(merged_children),
            "composed_from": [module_a.name, module_b.name],
        },
        children=merged_children,
        confidence=total_conf,
        execution_status=(
            ExecutionStatus.HEURISTIC_INPUT if has_heuristic
            else ExecutionStatus.DETERMINISTIC
        ),
    )

    # Type-check the composed result
    composed_tc = type_check_program(composed)
    if not composed_tc.is_well_typed:
        result.errors.append(CompositionError(
            kind=CompositionErrorKind.COMPOSED_ILL_TYPED,
            message="Composed program failed type check",
            details={"errors": [e.to_dict() for e in composed_tc.errors]},
        ))
        return result

    # Build composed module
    composed_module = ProgramModule(
        name=f"{module_a.name}+{module_b.name}",
        program=composed,
        type_check=composed_tc,
    )

    result.verdict = CompositionVerdict.SUCCESS
    result.composed_program = composed
    result.composed_module = composed_module
    return result


def _extract_binding_kinds(program: ProgramNode) -> Dict[str, str]:
    """Extract binding name → primitive kind map from a program."""
    kinds = {}
    for child in program.children:
        if child.kind == ProgramNodeKind.BINDING_STMT:
            target = child.value.get("target", "")
            if child.children:
                prim_kind = child.children[0].value.get("primitive_kind", "")
                kinds[target] = prim_kind
    return kinds


# ════════════════════════════════════════════════════════════
# PROGRAM LIBRARY — collection of named modules
# ════════════════════════════════════════════════════════════

class ProgramLibrary:
    """
    A collection of named program modules.
    Supports registration, lookup, and composition.
    """

    def __init__(self):
        self._modules: Dict[str, ProgramModule] = {}

    def register(self, module: ProgramModule) -> bool:
        """Register a module. Returns False if name already taken."""
        if module.name in self._modules:
            return False
        self._modules[module.name] = module
        return True

    def get(self, name: str) -> Optional[ProgramModule]:
        return self._modules.get(name)

    def list_modules(self) -> List[str]:
        return sorted(self._modules.keys())

    def compose_by_name(
        self,
        name_a: str,
        name_b: str,
        register_result: bool = True,
    ) -> CompositionResult:
        """Compose two modules by name."""
        a = self._modules.get(name_a)
        b = self._modules.get(name_b)
        if a is None or b is None:
            result = CompositionResult()
            missing = name_a if a is None else name_b
            result.errors.append(CompositionError(
                kind=CompositionErrorKind.ILL_TYPED_MODULE,
                message=f"Module '{missing}' not found in library",
            ))
            return result

        cr = compose(a, b)
        if cr.verdict == CompositionVerdict.SUCCESS and register_result and cr.composed_module:
            self.register(cr.composed_module)
        return cr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_count": len(self._modules),
            "modules": {name: m.to_dict() for name, m in sorted(self._modules.items())},
        }
