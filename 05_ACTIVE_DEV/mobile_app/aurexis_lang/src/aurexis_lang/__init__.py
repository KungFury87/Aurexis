from .control_flow_state_machine import step_state_machine, control_steps_to_transitions

from .perception_benchmark import benchmark_profiles
from .control_resolution import resolve_control_step, summarize_control_resolution

from .evaluation_loop_scaffold import evaluate_rows, summarize_by_provenance
from .branch_state_execution import run_branch_state_execution

from .training_loop_scaffold import load_dataset_manifest, run_training_loop_scaffold, write_training_loop_outputs
from .execution_state_propagation import propagate_execution_state

from .perception_inference import infer_from_rows

from .learned_candidate_model import score_candidate_row, rank_candidate_rows
from .execution_interpretation import interpret_execution_result

from .perception_dataset_prep import load_rows, rank_row_usefulness, build_dataset_manifest, write_dataset_manifest

from .perception_dataset_export import perception_row_from_image, export_dataset_rows
from .execution_resolution import run_execution_resolution


from .robust_cv_perception import fuse_perception_layers, summarize_perception_disagreement
from .execution_semantics_deeper import run_execution_plan

from .execution_semantics import ast_to_execution_plan

from .parser_stub import Token, ASTNode, parse_tokens
from .runtime_stub import evaluate_ast
from .visual_tokenizer import PrimitiveObservation, primitives_to_tokens
from .parser_expanded import parse_tokens_expanded
from .ir import IRNode, ast_to_ir
from .camera_bridge_stub import camera_input_to_ir
from .runtime_expanded import evaluate_ir
from .token_kinds import TOKEN_KINDS
from .parser_syntax_expanded import parse_program, parse_statement
from .ir_expanded import ast_to_ir_expanded
from .runtime_syntax_expanded import evaluate_ir_expanded
from .parser_scope_control import parse_program_with_scope, parse_block, parse_control
from .program_graph import ProgramGraph, GraphEdge, ast_to_program_graph
from .runtime_control import evaluate_program_graph

from .camera_primitive_extractor import load_zone_manifest, extract_primitives_from_zone_data, zone_json_to_parser_bundle

from .image_primitive_extractor import extract_image_primitives, image_to_parser_bundle

from .cv_primitive_extractor import extract_cv_primitives, cv_image_to_parser_bundle

from .segmentation_pipeline import coarse_partition, segments_to_primitives, image_to_segmented_parser_bundle

from .confidence_parser import summarize_confidence, parse_with_confidence
from .execution_trace import ast_to_trace

from .ambiguity import CandidateInterpretation, rank_candidates, summarize_candidates
from .runtime_semantics_stub import ast_to_semantic_summary

from .demo_pipeline import run_zone_demo, write_demo_report

from .cv_segmentation_upgrade import extract_segmented_primitives, segmented_image_to_parser_bundle


from .cv_segmentation_quality import multi_threshold_segment, choose_best_segmentation
from .runtime_semantics_expanded import ast_to_semantic_summary_expanded

from .real_evidence_capture import EvidenceCapture, quick_capture_demo
from .evidence_batch_processor import EvidenceBatchProcessor, process_all_available_batches
from .evidence_tiers import EvidenceTier, build_evidence_stamp, stamp_result, normalize_evidence_tier, is_earned_tier

__all__ = [
    "Token", "ASTNode", "parse_tokens", "evaluate_ast",
    "PrimitiveObservation", "primitives_to_tokens",
    "parse_tokens_expanded", "IRNode", "ast_to_ir",
    "camera_input_to_ir", "evaluate_ir",
    "TOKEN_KINDS", "parse_program", "parse_statement",
    "ast_to_ir_expanded", "evaluate_ir_expanded",
    "parse_program_with_scope", "parse_block", "parse_control",
    "ProgramGraph", "GraphEdge", "ast_to_program_graph",
    "evaluate_program_graph",
        "load_zone_manifest", "extract_primitives_from_zone_data", "zone_json_to_parser_bundle",
        "extract_image_primitives", "image_to_parser_bundle",
        "extract_cv_primitives", "cv_image_to_parser_bundle",
        "coarse_partition", "segments_to_primitives", "image_to_segmented_parser_bundle",
        "extract_segmented_primitives", "segmented_image_to_parser_bundle",
        "summarize_confidence", "parse_with_confidence", "ast_to_trace",
        "CandidateInterpretation", "rank_candidates", "summarize_candidates", "ast_to_semantic_summary",
        "multi_threshold_segment", "choose_best_segmentation", "ast_to_semantic_summary_expanded",
        "run_zone_demo", "write_demo_report",
]

__all__ += [
    "ast_to_execution_plan",
]

__all__ += [
    "fuse_perception_layers",
    "summarize_perception_disagreement",
    "run_execution_plan",
]

__all__ += [
    "perception_row_from_image",
    "export_dataset_rows",
    "run_execution_resolution",
]

__all__ += [
    "load_rows",
    "rank_row_usefulness",
    "build_dataset_manifest",
    "write_dataset_manifest",
]

__all__ += [
    "score_candidate_row",
    "rank_candidate_rows",
    "interpret_execution_result",
]

__all__ += [
    "infer_from_rows",
]

__all__ += [
    "load_dataset_manifest",
    "run_training_loop_scaffold",
    "write_training_loop_outputs",
    "propagate_execution_state",
]

__all__ += [
    "evaluate_rows",
    "summarize_by_provenance",
    "run_branch_state_execution",
]

__all__ += [
    "benchmark_profiles",
    "resolve_control_step",
    "summarize_control_resolution",
]

__all__ += [
    "step_state_machine", "summarize_control_transitions",
    "control_steps_to_transitions",
    "EvidenceCapture", "quick_capture_demo",
    "EvidenceBatchProcessor", "process_all_available_batches",
]

__all__ += [
    "EvidenceTier", "build_evidence_stamp", "stamp_result", "normalize_evidence_tier", "is_earned_tier",
]

from .phoxel_schema import TOP_LEVEL_FIELDS as PHOXEL_SCHEMA_TOP_LEVEL_FIELDS, coerce_phoxel_schema, validate_phoxel_schema
from .illegal_inference_matrix import BLOCKED_CLAIM_RULES, evaluate_blocked_claims

__all__ += [
    "PHOXEL_SCHEMA_TOP_LEVEL_FIELDS", "coerce_phoxel_schema", "validate_phoxel_schema",
    "BLOCKED_CLAIM_RULES", "evaluate_blocked_claims",
]

from .relation_legality import ALLOWED_RELATION_KINDS, PRIMARY_RELATION_KINDS, HIGHER_ORDER_RELATION_KINDS, validate_relation_legality
from .executable_promotion import validate_executable_promotion_checklist

__all__ += [
    "ALLOWED_RELATION_KINDS", "PRIMARY_RELATION_KINDS", "HIGHER_ORDER_RELATION_KINDS", "validate_relation_legality",
    "validate_executable_promotion_checklist",
]

from .future_tech_ceiling import BLOCKED_FUTURE_TECH_DRIFT, validate_future_tech_ceiling_criteria
from .mobile_demo_target import ALLOWED_MOBILE_DEMO_EVIDENCE, validate_narrow_mobile_demonstration_target

__all__ += [
    "BLOCKED_FUTURE_TECH_DRIFT", "validate_future_tech_ceiling_criteria",
    "ALLOWED_MOBILE_DEMO_EVIDENCE", "validate_narrow_mobile_demonstration_target",
]

from .runtime_obedience import evaluate_runtime_obedience, build_runtime_obedience_report

__all__ += [
    "evaluate_runtime_obedience", "build_runtime_obedience_report",
]

from .runtime_reporting import RUNTIME_REPORTING_RULES_VERSION, RUNTIME_EVIDENCE_SCOPE, RUNTIME_GATE_STATUS, stamp_runtime_surface

__all__ += [
    "RUNTIME_REPORTING_RULES_VERSION", "RUNTIME_EVIDENCE_SCOPE", "RUNTIME_GATE_STATUS", "stamp_runtime_surface",
]

from .gate2_completion_audit import AUDIT_RULES_VERSION, COMPLETION_AUTHORITY, audit_gate2_completion

from .gate3_evidence_loop import GATE_3_STATUS, GATE_3_RULES_VERSION, GATE_3_SEPARATION_VERSION, evaluate_gate3_evidence_loop, stamp_gate3_surface

__all__ += [
    "GATE_3_STATUS", "GATE_3_RULES_VERSION", "GATE_3_SEPARATION_VERSION", "evaluate_gate3_evidence_loop", "stamp_gate3_surface",
]

from .gate3_comparison_audit import (
    GATE_3_COMPARISON_RULES_VERSION,
    GATE_3_AUDIT_RULES_VERSION,
    build_authored_reference_surface,
    build_real_capture_reference_surface,
    compare_authored_real_capture_surfaces,
    audit_gate3_earned_evidence_scaffold,
)

__all__ += [
    "GATE_3_COMPARISON_RULES_VERSION", "GATE_3_AUDIT_RULES_VERSION",
    "build_authored_reference_surface", "build_real_capture_reference_surface",
    "compare_authored_real_capture_surfaces", "audit_gate3_earned_evidence_scaffold",
]

from .gate3_batch_comparison import GATE_3_BATCH_COMPARISON_RULES_VERSION, compare_authored_summary_to_batch

from .gate3_batch_comparison import GATE_3_BATCH_COMPARISON_RULES_VERSION, compare_authored_summary_to_batch

__all__ += [
    "GATE_3_BATCH_COMPARISON_RULES_VERSION", "compare_authored_summary_to_batch",
]

from .gate3_batch_reporting import GATE_3_BATCH_REPORT_RULES_VERSION, build_gate3_batch_report_surface

__all__ += [
    "GATE_3_BATCH_REPORT_RULES_VERSION", "build_gate3_batch_report_surface",
]

from .gate3_completion_audit import GATE_3_COMPLETION_AUDIT_RULES_VERSION, GATE_3_COMPLETION_AUTHORITY, audit_gate3_completion

__all__ += [
    "GATE_3_COMPLETION_AUDIT_RULES_VERSION", "GATE_3_COMPLETION_AUTHORITY", "audit_gate3_completion",
]

from .gate3_earned_promotion import (
    GATE_3_EARNED_PROMOTION_RULES_VERSION,
    promote_gate3_earned_candidate,
)

from .gate3_gate_completion_audit import GATE_3_GATE_COMPLETION_AUDIT_RULES_VERSION, GATE_3_GATE_COMPLETION_AUTHORITY, audit_gate3_gate_completion

__all__ += [
    "GATE_3_GATE_COMPLETION_AUDIT_RULES_VERSION", "GATE_3_GATE_COMPLETION_AUTHORITY", "audit_gate3_gate_completion",
]


from .gate3_route_reporting import GATE_3_ROUTE_REPORT_RULES_VERSION, build_gate3_route_report_surface

__all__ += [
    "GATE_3_ROUTE_REPORT_RULES_VERSION", "build_gate3_route_report_surface",
]

from .gate3_saved_run_audit import GATE_3_SAVED_RUN_RULES_VERSION, collect_gate3_saved_route_surfaces, build_gate3_gate_completion_audit_from_project_root
__all__ += [
    "GATE_3_SAVED_RUN_RULES_VERSION", "collect_gate3_saved_route_surfaces", "build_gate3_gate_completion_audit_from_project_root",
]

from .gate3_multi_route_completion import GATE_3_MULTI_ROUTE_COMPLETION_RULES_VERSION, build_gate3_saved_route_package, build_validation_cycle_results_from_route_package, build_complete_cycle_results_from_route_package

from .gate3_global_completion import (
    GATE_3_GLOBAL_COMPLETION_RULES_VERSION,
    GATE_3_DEFAULT_STATE_AUDIT_RULES_VERSION,
    GATE_3_GLOBAL_COMPLETION_AUTHORITY,
    build_gate3_global_completion_report,
)

from .gate3_saved_seed import (
    GATE_3_CANONICAL_SAVED_SEED_RULES_VERSION,
    build_gate3_canonical_saved_seed,
)


from .gate3_packaged_default_state import (
    GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION,
    GATE_3_FINAL_COMPLETION_REPORT_RULES_VERSION,
    GATE_3_FINAL_COMPLETION_AUTHORITY,
    clear_gate3_saved_outputs,
    build_gate3_final_completion_report,
)

__all__ += [
    "GATE_3_PACKAGED_DEFAULT_STATE_RULES_VERSION",
    "GATE_3_FINAL_COMPLETION_REPORT_RULES_VERSION",
    "GATE_3_FINAL_COMPLETION_AUTHORITY",
    "clear_gate3_saved_outputs",
    "build_gate3_final_completion_report",
]

from .gate3_default_pipeline import (
    GATE_3_DEFAULT_PIPELINE_RULES_VERSION,
    GATE_3_PACKAGE_STATE_STAMP_RULES_VERSION,
    GATE_3_DEFAULT_PIPELINE_AUTHORITY,
    build_gate3_default_pipeline_stamp,
)
__all__.extend([
    "GATE_3_DEFAULT_PIPELINE_RULES_VERSION",
    "GATE_3_PACKAGE_STATE_STAMP_RULES_VERSION",
    "GATE_3_DEFAULT_PIPELINE_AUTHORITY",
    "build_gate3_default_pipeline_stamp",
])

from .gate3_release_pipeline import (
    GATE_3_RELEASE_PIPELINE_RULES_VERSION,
    GATE_3_ROOT_PACKAGE_COMPLETION_STAMP_RULES_VERSION,
    GATE_3_RELEASE_PIPELINE_AUTHORITY,
    build_gate3_root_package_completion_stamp,
)
__all__.extend([
    "GATE_3_RELEASE_PIPELINE_RULES_VERSION",
    "GATE_3_ROOT_PACKAGE_COMPLETION_STAMP_RULES_VERSION",
    "GATE_3_RELEASE_PIPELINE_AUTHORITY",
    "build_gate3_root_package_completion_stamp",
])

from .gate4_mobile_demo_kickoff import (
    GATE_4_NARROW_MOBILE_DEMO_RULES_VERSION,
    GATE_4_PACKAGE_QUICKSTART_RULES_VERSION,
    GATE_4_KICKOFF_AUTHORITY,
    build_gate4_narrow_mobile_demo_report,
)
__all__.extend([
    "GATE_4_NARROW_MOBILE_DEMO_RULES_VERSION",
    "GATE_4_PACKAGE_QUICKSTART_RULES_VERSION",
    "GATE_4_KICKOFF_AUTHORITY",
    "build_gate4_narrow_mobile_demo_report",
])
