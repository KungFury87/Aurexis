"""
Aurexis Core V1 Substrate Candidate — package init.

This reduced package contains only the V1 law-bearing substrate modules.
Legacy pre-substrate modules are not included and not imported.

Scope: Narrow V1 substrate candidate, not full Aurexis Core.
(c) 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

# ── V1 Substrate Modules (shipped in locked package) ──
# All test files import directly from submodules, e.g.:
#   from aurexis_lang.visual_grammar_v1 import ...
# This __init__.py exists only to make aurexis_lang a valid package.
# It does NOT re-export submodule contents to avoid coupling.

__version__ = "V1.0-substrate-candidate"

V1_MODULES = [
    "visual_grammar_v1",
    "visual_parser_v1",
    "visual_parse_rules_v1",
    "visual_executor_v1",
    "visual_program_executor_v1",
    "type_system_v1",
    "composition_v1",
    "print_scan_stability_v1",
    "temporal_law_v1",
    "hardware_calibration_v1",
    "self_hosting_v1",
    "substrate_v1",
    "raster_law_bridge_v1",
    "capture_tolerance_bridge_v1",
    "artifact_localization_bridge_v1",
    "orientation_normalization_bridge_v1",
    "perspective_normalization_bridge_v1",
    "composed_recovery_bridge_v1",
    "artifact_dispatch_bridge_v1",
    "multi_artifact_layout_bridge_v1",
    "artifact_set_contract_bridge_v1",
    "recovered_set_signature_bridge_v1",
    "recovered_set_signature_match_bridge_v1",
]
