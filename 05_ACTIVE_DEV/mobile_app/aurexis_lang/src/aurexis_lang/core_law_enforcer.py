"""
Core Law Enforcer for Aurexis

Immutable enforcement of frozen core law principles.
No development may violate these principles.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import time
from datetime import datetime

from .phoxel_schema import coerce_phoxel_schema, validate_phoxel_schema
from .illegal_inference_matrix import evaluate_blocked_claims
from .relation_legality import validate_relation_legality
from .executable_promotion import validate_executable_promotion_checklist
from .future_tech_ceiling import validate_future_tech_ceiling_criteria
from .mobile_demo_target import validate_narrow_mobile_demonstration_target

class ViolationLevel(Enum):
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class CoreLawSection(Enum):
    PHOXEL_RECORD = "phoxel_record"
    NATIVE_RELATIONS = "native_relations"
    WORLD_IMAGE_AUTHORITY = "world_image_authority"
    EXECUTABLE_PROMOTION = "executable_promotion"
    ILLEGAL_INFERENCE = "illegal_inference"
    CURRENT_TECH_FLOOR = "current_tech_floor"
    FUTURE_TECH_CEILING = "future_tech_ceiling"

@dataclass
class CoreLawViolation:
    """Represents a core law violation"""
    section: CoreLawSection
    level: ViolationLevel
    description: str
    evidence: Dict[str, Any]
    timestamp: datetime
    required_action: str

class CoreLawEnforcer:
    """Immutable enforcer of frozen core law principles"""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.violations: List[CoreLawViolation] = []
        self.mobile_baseline = {
            "min_camera_mp": 8,
            "min_memory_mb": 4000,
            "max_processing_time_seconds": 30,
            "max_memory_usage_mb": 500,
            "max_battery_percent_per_minute": 5
        }
        
    def validate_phoxel_record(self, primitive: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate the Gate 1 minimum legal phoxel record schema."""
        violations = []
        schema = coerce_phoxel_schema(primitive)
        schema_errors = validate_phoxel_schema(schema)

        for error in schema_errors:
            level = ViolationLevel.CRITICAL if 'synthetic_true' in error else ViolationLevel.ERROR
            violations.append(CoreLawViolation(
                section=CoreLawSection.PHOXEL_RECORD,
                level=level,
                description=f"Phoxel schema violation: {error}",
                evidence=schema,
                timestamp=datetime.now(),
                required_action="Bring primitive into the minimum legal phoxel schema or reject it"
            ))

        if not primitive.get('camera_metadata') and not schema.get('photonic_signature', {}).get('camera_metadata'):
            violations.append(CoreLawViolation(
                section=CoreLawSection.PHOXEL_RECORD,
                level=ViolationLevel.WARNING,
                description="Primitive lacks camera metadata",
                evidence=schema,
                timestamp=datetime.now(),
                required_action="Add camera metadata for full compliance"
            ))

        return violations
    
    def validate_native_relations(self, relation: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate native relations against the frozen Gate 1 relation-legality sheet."""
        violations = []

        for error in validate_relation_legality(relation):
            level = ViolationLevel.CRITICAL if error == 'forbidden_abstract_semantic' else ViolationLevel.ERROR
            violations.append(CoreLawViolation(
                section=CoreLawSection.NATIVE_RELATIONS,
                level=level,
                description=f"Relation legality violation: {error}",
                evidence=relation,
                timestamp=datetime.now(),
                required_action="Bring relation into the frozen measurable-requirements sheet or reject it"
            ))

        return violations

    def validate_world_image_authority(self, interpretation: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate dual-register authority compliance.

        Locked Aurexis law:
        - world is primary in authority
        - image is primary in access
        - both registers stay alive in processing
        """
        violations = []

        # The model may not override the observed image register.
        if interpretation.get('model_overrides_image', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.WORLD_IMAGE_AUTHORITY,
                level=ViolationLevel.CRITICAL,
                description="Model interpretation overrides observed image access",
                evidence=interpretation,
                timestamp=datetime.now(),
                required_action="Reject interpretation immediately"
            ))

        # The image may not be treated as the sole final authority about world truth.
        if interpretation.get('image_as_final_world_truth', False) or interpretation.get('image_only_final_authority', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.WORLD_IMAGE_AUTHORITY,
                level=ViolationLevel.ERROR,
                description="Image register treated as final world authority",
                evidence=interpretation,
                timestamp=datetime.now(),
                required_action="Restore world-authority / image-access separation"
            ))

        # World claims must still be evidence-bounded through the image register.
        if interpretation.get('world_knowledge_without_evidence', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.WORLD_IMAGE_AUTHORITY,
                level=ViolationLevel.ERROR,
                description="World knowledge asserted without image-grounded evidence",
                evidence=interpretation,
                timestamp=datetime.now(),
                required_action="Remove unsupported world claim or add image evidence"
            ))

        # Common-sense or prior-model overrides may not suppress the observed register.
        if interpretation.get('common_sense_override', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.WORLD_IMAGE_AUTHORITY,
                level=ViolationLevel.ERROR,
                description="Common-sense override suppresses observed image evidence",
                evidence=interpretation,
                timestamp=datetime.now(),
                required_action="Remove common-sense override"
            ))

        return violations
    
    def validate_executable_promotion(self, executable: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate executable promotion against the frozen Gate 1 checklist."""
        violations = []

        for error in validate_executable_promotion_checklist(executable):
            level = ViolationLevel.CRITICAL if error in {'missing_evidence_validated', 'promotion_by_assumption'} else ViolationLevel.ERROR
            violations.append(CoreLawViolation(
                section=CoreLawSection.EXECUTABLE_PROMOTION,
                level=level,
                description=f"Executable promotion violation: {error}",
                evidence=executable,
                timestamp=datetime.now(),
                required_action="Bring executable candidate into the frozen promotion checklist or reject it"
            ))

        return violations

    def validate_illegal_inference(self, inference: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate illegal inference compliance against the blocked-claim matrix."""
        violations = []

        if not inference.get('evidence_bounded', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.ILLEGAL_INFERENCE,
                level=ViolationLevel.CRITICAL,
                description="Inference beyond evidence bounds",
                evidence=inference,
                timestamp=datetime.now(),
                required_action="Reject unbounded inference immediately"
            ))

        if 'uncertainty' not in inference:
            violations.append(CoreLawViolation(
                section=CoreLawSection.ILLEGAL_INFERENCE,
                level=ViolationLevel.ERROR,
                description="Inference lacks uncertainty quantification",
                evidence=inference,
                timestamp=datetime.now(),
                required_action="Add uncertainty quantification"
            ))

        if inference.get('logical_leap', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.ILLEGAL_INFERENCE,
                level=ViolationLevel.ERROR,
                description="Logical leap without evidence",
                evidence=inference,
                timestamp=datetime.now(),
                required_action="Remove logical leap or add evidence"
            ))

        if 'evidence_chain' not in inference:
            violations.append(CoreLawViolation(
                section=CoreLawSection.ILLEGAL_INFERENCE,
                level=ViolationLevel.WARNING,
                description="Inference lacks evidence chain traceability",
                evidence=inference,
                timestamp=datetime.now(),
                required_action="Add evidence chain for full compliance"
            ))

        for rule in evaluate_blocked_claims(inference):
            violations.append(CoreLawViolation(
                section=CoreLawSection.ILLEGAL_INFERENCE,
                level=ViolationLevel.ERROR,
                description=f"Blocked claim: {rule.claim_id} - {rule.description}",
                evidence=inference,
                timestamp=datetime.now(),
                required_action=rule.required_action,
            ))

        return violations
    
    def validate_current_tech_floor(self, performance: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate current-tech floor and narrow mobile demonstration compliance."""
        violations = []

        processing_time = performance.get('processing_time_seconds', 0)
        if processing_time > self.mobile_baseline['max_processing_time_seconds']:
            violations.append(CoreLawViolation(
                section=CoreLawSection.CURRENT_TECH_FLOOR,
                level=ViolationLevel.ERROR,
                description=f"Processing time {processing_time}s exceeds mobile baseline {self.mobile_baseline['max_processing_time_seconds']}s",
                evidence=performance,
                timestamp=datetime.now(),
                required_action="Optimize processing or reject feature"
            ))

        memory_usage = performance.get('memory_usage_mb', 0)
        if memory_usage > self.mobile_baseline['max_memory_usage_mb']:
            violations.append(CoreLawViolation(
                section=CoreLawSection.CURRENT_TECH_FLOOR,
                level=ViolationLevel.ERROR,
                description=f"Memory usage {memory_usage}MB exceeds mobile baseline {self.mobile_baseline['max_memory_usage_mb']}MB",
                evidence=performance,
                timestamp=datetime.now(),
                required_action="Optimize memory usage or reject feature"
            ))

        if performance.get('exotic_hardware_required', False):
            violations.append(CoreLawViolation(
                section=CoreLawSection.CURRENT_TECH_FLOOR,
                level=ViolationLevel.CRITICAL,
                description="Exotic hardware requirement violates current tech floor",
                evidence=performance,
                timestamp=datetime.now(),
                required_action="Reject exotic hardware dependency immediately"
            ))

        for error in validate_narrow_mobile_demonstration_target(performance):
            level = ViolationLevel.CRITICAL if error in {'missing_no_hidden_exotic_hardware', 'insufficient_mobile_demo_evidence'} else ViolationLevel.ERROR
            violations.append(CoreLawViolation(
                section=CoreLawSection.CURRENT_TECH_FLOOR,
                level=level,
                description=f"Mobile demonstration target violation: {error}",
                evidence=performance,
                timestamp=datetime.now(),
                required_action="Bring demonstration candidate into the frozen narrow mobile target or reject it"
            ))

        return violations

    def validate_future_tech_ceiling(self, scalability: Dict[str, Any]) -> List[CoreLawViolation]:
        """Validate future-tech ceiling compatibility criteria."""
        violations = []

        for error in validate_future_tech_ceiling_criteria(scalability):
            level = ViolationLevel.CRITICAL if error in {'ontology_rewrite_required', 'behavior_changes_with_hardware', 'current_floor_invalidated', 'changes_law_shape'} else ViolationLevel.ERROR
            violations.append(CoreLawViolation(
                section=CoreLawSection.FUTURE_TECH_CEILING,
                level=level,
                description=f"Future-tech ceiling violation: {error}",
                evidence=scalability,
                timestamp=datetime.now(),
                required_action="Bring scalability claim into the frozen compatibility criteria or reject it"
            ))

        return violations
    
    def validate_comprehensive(self, claim: Dict[str, Any]) -> List[CoreLawViolation]:
        """Comprehensive validation against all core law sections"""
        all_violations = []
        
        # Validate based on claim type
        claim_type = claim.get('type', 'unknown')
        
        if claim_type in ['primitive', 'visual_element']:
            all_violations.extend(self.validate_phoxel_record(claim))
        
        if claim_type in ['relation', 'spatial_relationship']:
            all_violations.extend(self.validate_native_relations(claim))
        
        if claim_type in ['interpretation', 'analysis']:
            all_violations.extend(self.validate_world_image_authority(claim))
        
        if claim_type in ['executable', 'action']:
            all_violations.extend(self.validate_executable_promotion(claim))
        
        if claim_type in ['inference', 'reasoning']:
            all_violations.extend(self.validate_illegal_inference(claim))
        
        if claim_type in ['performance', 'resource_usage', 'mobile_demo', 'demonstration']:
            all_violations.extend(self.validate_current_tech_floor(claim))
        
        if claim_type in ['scalability', 'hardware_scaling']:
            all_violations.extend(self.validate_future_tech_ceiling(claim))
        
        # Store violations
        self.violations.extend(all_violations)
        
        return all_violations
    
    def enforce_core_law(self, claim: Dict[str, Any]) -> Tuple[bool, List[CoreLawViolation]]:
        """Enforce core law - return whether claim passes validation"""
        violations = self.validate_comprehensive(claim)
        
        # Determine if claim passes based on violation levels
        critical_violations = [v for v in violations if v.level == ViolationLevel.CRITICAL]
        error_violations = [v for v in violations if v.level == ViolationLevel.ERROR]
        
        if critical_violations:
            return False, violations  # Reject immediately
        elif error_violations and self.strict_mode:
            return False, violations  # Reject in strict mode
        else:
            return True, violations  # Pass (with warnings maybe)
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        if not self.violations:
            return {
                "status": "COMPLIANT",
                "total_violations": 0,
                "critical_violations": 0,
                "error_violations": 0,
                "warning_violations": 0,
                "sections_violated": [],
                "recommendation": "All claims comply with frozen core law"
            }
        
        critical_count = len([v for v in self.violations if v.level == ViolationLevel.CRITICAL])
        error_count = len([v for v in self.violations if v.level == ViolationLevel.ERROR])
        warning_count = len([v for v in self.violations if v.level == ViolationLevel.WARNING])
        
        sections_violated = list(set(v.section.value for v in self.violations))
        
        recommendation = "REJECT" if critical_count > 0 else "REVIEW" if error_count > 0 else "MONITOR"
        
        return {
            "status": "NON_COMPLIANT",
            "total_violations": len(self.violations),
            "critical_violations": critical_count,
            "error_violations": error_count,
            "warning_violations": warning_count,
            "sections_violated": sections_violated,
            "recommendation": recommendation,
            "violations": [
                {
                    "section": v.section.value,
                    "level": v.level.value,
                    "description": v.description,
                    "required_action": v.required_action,
                    "timestamp": v.timestamp.isoformat()
                }
                for v in self.violations
            ]
        }
    
    def clear_violations(self):
        """Clear violations history (for testing only)"""
        self.violations.clear()


# Global enforcer instance
_core_law_enforcer = CoreLawEnforcer(strict_mode=True)

def enforce_core_law(claim: Dict[str, Any]) -> Tuple[bool, List[CoreLawViolation]]:
    """Convenience function for core law enforcement"""
    return _core_law_enforcer.enforce_core_law(claim)

def get_core_law_compliance_report() -> Dict[str, Any]:
    """Convenience function for compliance reporting"""
    return _core_law_enforcer.get_compliance_report()
