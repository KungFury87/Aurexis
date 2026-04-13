"""
Aurexis Core — Unified Substrate Entrypoint Bridge V1

Thin bounded top-level orchestrator that can invoke the existing branch
capabilities without the user having to know every internal file.
Routes into existing validated modules rather than re-implementing them.

What this proves:
  The V1 substrate candidate has one coherent entry surface that can
  route into any of the 5 completed branches, invoke any of the 40
  bridge modules, and return structured results. The entrypoint is
  deterministic and bounded.

What this does NOT prove:
  - Full Aurexis Core completion
  - Production API design
  - Real-time processing capability
  - Security or access control

Design:
  - SubstrateRoute: enum of available top-level routes.
  - RouteResult: structured return from any route invocation.
  - V1_ENTRYPOINT: singleton orchestrator instance.
  - route(): invoke a specific capability by route enum.
  - list_routes(): enumerate all available routes.
  - import_bridge(): dynamically import a bridge module by number or name.

All routing is deterministic. No state mutation.

(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

import importlib
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ── Version / Freeze ──
ENTRYPOINT_VERSION = "V1.0"
ENTRYPOINT_FROZEN = True


# ── Routes ──
class SubstrateRoute(str, Enum):
    """Top-level routes into V1 substrate capabilities."""
    # Branch-level routes
    STATIC_SUBSTRATE = "static_substrate"
    TEMPORAL_TRANSPORT = "temporal_transport"
    HIGHER_ORDER_COHERENCE = "higher_order_coherence"
    VIEW_DEPENDENT = "view_dependent"
    VSA_CLEANUP = "vsa_cleanup"
    # Cross-cutting routes
    MANIFEST = "manifest"
    COMPATIBILITY = "compatibility"


# ── Bridge Registry ──
# Maps bridge number → module name (all 40 bridges)
BRIDGE_REGISTRY: Dict[int, str] = {
    1: "raster_law_bridge_v1",
    2: "capture_tolerance_bridge_v1",
    3: "artifact_localization_bridge_v1",
    4: "orientation_normalization_bridge_v1",
    5: "perspective_normalization_bridge_v1",
    6: "composed_recovery_bridge_v1",
    7: "artifact_dispatch_bridge_v1",
    8: "multi_artifact_layout_bridge_v1",
    9: "artifact_set_contract_bridge_v1",
    10: "recovered_set_signature_bridge_v1",
    11: "recovered_set_signature_match_bridge_v1",
    12: "recovered_page_sequence_contract_bridge_v1",
    13: "recovered_page_sequence_signature_bridge_v1",
    14: "recovered_page_sequence_signature_match_bridge_v1",
    15: "recovered_sequence_collection_contract_bridge_v1",
    16: "recovered_sequence_collection_signature_bridge_v1",
    17: "recovered_sequence_collection_signature_match_bridge_v1",
    18: "recovered_collection_global_consistency_bridge_v1",
    19: "rolling_shutter_temporal_transport_bridge_v1",
    20: "complementary_color_temporal_transport_bridge_v1",
    21: "temporal_transport_dispatch_bridge_v1",
    22: "temporal_consistency_bridge_v1",
    23: "frame_accurate_transport_bridge_v1",
    24: "combined_temporal_fusion_bridge_v1",
    25: "temporal_payload_contract_bridge_v1",
    26: "temporal_payload_signature_bridge_v1",
    27: "temporal_payload_signature_match_bridge_v1",
    28: "temporal_global_consistency_bridge_v1",
    29: "overlap_detection_bridge_v1",
    30: "local_section_consistency_bridge_v1",
    31: "sheaf_style_composition_bridge_v1",
    32: "cohomological_obstruction_bridge_v1",
    33: "view_dependent_marker_profile_bridge_v1",
    34: "moment_invariant_identity_bridge_v1",
    35: "view_facet_recovery_bridge_v1",
    36: "view_dependent_contract_bridge_v1",
    37: "vsa_cleanup_profile_bridge_v1",
    38: "hypervector_binding_bundling_bridge_v1",
    39: "cleanup_retrieval_bridge_v1",
    40: "vsa_consistency_contract_bridge_v1",
}

# Route → bridge number ranges
ROUTE_BRIDGE_RANGES: Dict[SubstrateRoute, Tuple[int, int]] = {
    SubstrateRoute.STATIC_SUBSTRATE: (1, 18),
    SubstrateRoute.TEMPORAL_TRANSPORT: (19, 28),
    SubstrateRoute.HIGHER_ORDER_COHERENCE: (29, 32),
    SubstrateRoute.VIEW_DEPENDENT: (33, 36),
    SubstrateRoute.VSA_CLEANUP: (37, 40),
}


# ── Result types ──
@dataclass(frozen=True)
class RouteResult:
    """Structured return from a route invocation."""
    route: SubstrateRoute
    success: bool
    bridge_count: int
    modules_loaded: Tuple[str, ...]
    error: Optional[str] = None

    @property
    def result_hash(self) -> str:
        raw = f"{self.route.value}:{self.success}:{self.bridge_count}:{len(self.modules_loaded)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ImportResult:
    """Result of importing a specific bridge module."""
    bridge_number: int
    module_name: str
    success: bool
    module: Optional[Any] = None
    error: Optional[str] = None


class UnifiedSubstrateEntrypoint:
    """Thin orchestrator that routes into existing V1 substrate capabilities."""

    def __init__(self):
        self._version = ENTRYPOINT_VERSION
        self._frozen = ENTRYPOINT_FROZEN

    @property
    def version(self) -> str:
        return self._version

    @property
    def frozen(self) -> bool:
        return self._frozen

    def list_routes(self) -> Tuple[SubstrateRoute, ...]:
        """Return all available top-level routes."""
        return tuple(SubstrateRoute)

    def list_bridges(self, route: Optional[SubstrateRoute] = None) -> Dict[int, str]:
        """List bridges, optionally filtered by route."""
        if route is None:
            return dict(BRIDGE_REGISTRY)
        if route in ROUTE_BRIDGE_RANGES:
            lo, hi = ROUTE_BRIDGE_RANGES[route]
            return {k: v for k, v in BRIDGE_REGISTRY.items() if lo <= k <= hi}
        return {}

    def import_bridge(self, bridge_number: int) -> ImportResult:
        """Dynamically import a bridge module by number."""
        if bridge_number not in BRIDGE_REGISTRY:
            return ImportResult(
                bridge_number=bridge_number,
                module_name="",
                success=False,
                error=f"Unknown bridge number: {bridge_number}",
            )
        mod_name = BRIDGE_REGISTRY[bridge_number]
        try:
            mod = importlib.import_module(f"aurexis_lang.{mod_name}")
            return ImportResult(
                bridge_number=bridge_number,
                module_name=mod_name,
                success=True,
                module=mod,
            )
        except ImportError as e:
            return ImportResult(
                bridge_number=bridge_number,
                module_name=mod_name,
                success=False,
                error=str(e),
            )

    def import_bridge_by_name(self, module_name: str) -> ImportResult:
        """Import a bridge module by its module name."""
        number = None
        for k, v in BRIDGE_REGISTRY.items():
            if v == module_name:
                number = k
                break
        if number is None:
            return ImportResult(
                bridge_number=0,
                module_name=module_name,
                success=False,
                error=f"Unknown module name: {module_name}",
            )
        return self.import_bridge(number)

    def route(self, target: SubstrateRoute) -> RouteResult:
        """Invoke a route — load all bridges in the target branch."""
        if target == SubstrateRoute.MANIFEST:
            try:
                mod = importlib.import_module("aurexis_lang.unified_capability_manifest_bridge_v1")
                return RouteResult(
                    route=target, success=True, bridge_count=0,
                    modules_loaded=("unified_capability_manifest_bridge_v1",),
                )
            except ImportError as e:
                return RouteResult(
                    route=target, success=False, bridge_count=0,
                    modules_loaded=(), error=str(e),
                )

        if target == SubstrateRoute.COMPATIBILITY:
            try:
                mod = importlib.import_module("aurexis_lang.cross_branch_compatibility_contract_bridge_v1")
                return RouteResult(
                    route=target, success=True, bridge_count=0,
                    modules_loaded=("cross_branch_compatibility_contract_bridge_v1",),
                )
            except ImportError as e:
                return RouteResult(
                    route=target, success=False, bridge_count=0,
                    modules_loaded=(), error=str(e),
                )

        if target not in ROUTE_BRIDGE_RANGES:
            return RouteResult(
                route=target, success=False, bridge_count=0,
                modules_loaded=(), error=f"No bridge range for route: {target.value}",
            )

        lo, hi = ROUTE_BRIDGE_RANGES[target]
        loaded = []
        errors = []
        for num in range(lo, hi + 1):
            result = self.import_bridge(num)
            if result.success:
                loaded.append(result.module_name)
            else:
                errors.append(f"Bridge {num}: {result.error}")

        return RouteResult(
            route=target,
            success=len(errors) == 0,
            bridge_count=hi - lo + 1,
            modules_loaded=tuple(loaded),
            error="; ".join(errors) if errors else None,
        )

    def route_all(self) -> Dict[SubstrateRoute, RouteResult]:
        """Route into every branch and return all results."""
        return {r: self.route(r) for r in self.list_routes()}

    def entrypoint_hash(self) -> str:
        """Deterministic hash of the entrypoint configuration."""
        parts = [self._version, str(len(BRIDGE_REGISTRY))]
        for k in sorted(BRIDGE_REGISTRY.keys()):
            parts.append(f"{k}:{BRIDGE_REGISTRY[k]}")
        raw = "|".join(parts).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


# ── Singleton ──
V1_ENTRYPOINT = UnifiedSubstrateEntrypoint()

# ── Expected counts ──
EXPECTED_ROUTE_COUNT = len(SubstrateRoute)  # 7
EXPECTED_BRIDGE_REGISTRY_SIZE = 40
EXPECTED_BRANCH_ROUTE_COUNT = 5  # excluding MANIFEST and COMPATIBILITY
