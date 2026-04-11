"""
Multi-Frame Consistency Validator for Aurexis

Enforces the frozen core law requirement that executables must have
multi-frame consistency before promotion. This prevents overclaiming
and ensures only stable visual patterns become executable.
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
import time
from datetime import datetime
import math

class ConsistencyLevel(Enum):
    INCONSISTENT = "inconsistent"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class FramePrimitive:
    """Primitive detected in a single frame"""
    frame_id: int
    primitive_type: str
    attributes: Dict[str, Any]
    confidence: float
    pixel_coordinates: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    timestamp: datetime

@dataclass
class ConsistencyResult:
    """Result of multi-frame consistency analysis"""
    primitive_id: str
    consistency_level: ConsistencyLevel
    consistency_score: float
    frame_appearances: int
    total_frames: int
    stability_metrics: Dict[str, float]
    spatial_variance: float
    confidence_variance: float
    temporal_consistency: float
    promotion_eligible: bool

class MultiFrameConsistencyValidator:
    """
    Validates multi-frame consistency for executable promotion.
    
    Enforces core law: No visual element becomes executable 
    without multi-frame consistency evidence.
    """
    
    def __init__(self, min_frames: int = 3, consistency_threshold: float = 0.7):
        self.min_frames = min_frames
        self.consistency_threshold = consistency_threshold
        
        # Core law compliance parameters
        self.spatial_tolerance = 50  # pixels
        self.confidence_tolerance = 0.2
        self.type_consistency_required = True
        self.attribute_consistency_weight = 0.6
        self.spatial_consistency_weight = 0.4
    
    def track_primitive_across_frames(self, frame_primitives: List[List[Dict[str, Any]]]) -> List[List[FramePrimitive]]:
        """
        Track similar primitives across multiple frames
        """
        tracked_sequences = []
        
        for frame_idx, primitives in enumerate(frame_primitives):
            frame_sequence = []
            
            for prim in primitives:
                # Convert to FramePrimitive
                frame_prim = FramePrimitive(
                    frame_id=frame_idx,
                    primitive_type=prim.get('primitive_type', 'unknown'),
                    attributes=prim.get('attributes', {}),
                    confidence=prim.get('confidence', 0.0),
                    pixel_coordinates=self._extract_centroid(prim),
                    bbox=self._extract_bbox(prim),
                    timestamp=datetime.now()
                )
                frame_sequence.append(frame_prim)
            
            tracked_sequences.append(frame_sequence)
        
        return tracked_sequences
    
    def _extract_centroid(self, primitive: Dict[str, Any]) -> Tuple[int, int]:
        """Extract centroid coordinates from primitive"""
        attrs = primitive.get('attributes', {})
        
        # Try different centroid sources
        if 'centroid' in attrs:
            centroid = attrs['centroid']
            return (int(centroid[0]), int(centroid[1]))
        elif 'bbox' in attrs:
            bbox = attrs['bbox']
            x = (bbox['x0'] + bbox['x1']) // 2
            y = (bbox['y0'] + bbox['y1']) // 2
            return (x, y)
        else:
            # Default to center of image
            return (320, 240)  # Assuming 640x480
    
    def _extract_bbox(self, primitive: Dict[str, Any]) -> Tuple[int, int, int, int]:
        """Extract bounding box from primitive"""
        attrs = primitive.get('attributes', {})
        
        if 'bbox' in attrs:
            bbox = attrs['bbox']
            if isinstance(bbox, dict):
                return (bbox['x0'], bbox['y0'], bbox['x1'], bbox['y1'])
            elif isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                return tuple(bbox)
        
        # Default bbox around centroid
        centroid = self._extract_centroid(primitive)
        return (centroid[0] - 20, centroid[1] - 20, centroid[0] + 20, centroid[1] + 20)
    
    def group_similar_primitives(self, tracked_sequences: List[List[FramePrimitive]]) -> List[List[FramePrimitive]]:
        """
        Group similar primitives across frames based on spatial and attribute similarity
        """
        if len(tracked_sequences) < self.min_frames:
            return []
        
        # Start with first frame primitives as seed groups
        groups = []
        
        # Initialize groups with first frame primitives
        for prim in tracked_sequences[0]:
            groups.append([prim])
        
        # Match primitives from subsequent frames to existing groups
        for frame_idx in range(1, len(tracked_sequences)):
            frame_prims = tracked_sequences[frame_idx]
            unmatched_prims = frame_prims.copy()
            
            for group in groups:
                best_match = None
                best_score = 0.0
                
                for prim in unmatched_prims:
                    similarity_score = self._calculate_primitive_similarity(group[-1], prim)
                    if similarity_score > best_score and similarity_score > 0.5:  # Minimum similarity threshold
                        best_score = similarity_score
                        best_match = prim
                
                if best_match:
                    group.append(best_match)
                    unmatched_prims.remove(best_match)
            
            # Start new groups with unmatched primitives
            for prim in unmatched_prims:
                groups.append([prim])
        
        # Filter groups that don't have enough frames
        consistent_groups = [group for group in groups if len(group) >= self.min_frames]
        
        return consistent_groups
    
    def _calculate_primitive_similarity(self, prim1: FramePrimitive, prim2: FramePrimitive) -> float:
        """Calculate similarity between two primitives"""
        similarity_score = 0.0
        
        # Type consistency (must match for core law compliance)
        if self.type_consistency_required:
            type_score = 1.0 if prim1.primitive_type == prim2.primitive_type else 0.0
            if type_score == 0.0:
                return 0.0  # Different types are not similar
            similarity_score += type_score * 0.3
        
        # Spatial consistency
        spatial_distance = self._calculate_spatial_distance(prim1.pixel_coordinates, prim2.pixel_coordinates)
        spatial_score = max(0.0, 1.0 - (spatial_distance / self.spatial_tolerance))
        similarity_score += spatial_score * self.spatial_consistency_weight
        
        # Confidence consistency
        confidence_diff = abs(prim1.confidence - prim2.confidence)
        confidence_score = max(0.0, 1.0 - (confidence_diff / self.confidence_tolerance))
        similarity_score += confidence_score * 0.1
        
        # Attribute consistency
        attribute_score = self._calculate_attribute_similarity(prim1.attributes, prim2.attributes)
        similarity_score += attribute_score * self.attribute_consistency_weight
        
        return min(similarity_score, 1.0)
    
    def _calculate_spatial_distance(self, coord1: Tuple[int, int], coord2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two coordinates"""
        return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)
    
    def _calculate_attribute_similarity(self, attrs1: Dict[str, Any], attrs2: Dict[str, Any]) -> float:
        """Calculate attribute similarity between two primitives"""
        if not attrs1 or not attrs2:
            return 0.5  # Neutral score for missing attributes
        
        # Compare common attributes
        common_keys = set(attrs1.keys()) & set(attrs2.keys())
        if not common_keys:
            return 0.3  # Low score for no common attributes
        
        similarity_scores = []
        
        for key in common_keys:
            val1 = attrs1[key]
            val2 = attrs2[key]
            
            # Handle different attribute types
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numeric attributes
                diff = abs(val1 - val2)
                max_val = max(abs(val1), abs(val2), 1.0)
                similarity = max(0.0, 1.0 - (diff / max_val))
                similarity_scores.append(similarity)
            elif isinstance(val1, str) and isinstance(val2, str):
                # String attributes
                similarity = 1.0 if val1 == val2 else 0.0
                similarity_scores.append(similarity)
            elif isinstance(val1, (list, tuple)) and isinstance(val2, (list, tuple)):
                # Sequence attributes
                if len(val1) == len(val2):
                    matches = sum(1 for a, b in zip(val1, val2) if a == b)
                    similarity = matches / len(val1)
                    similarity_scores.append(similarity)
                else:
                    similarity_scores.append(0.5)  # Partial credit for similar structure
            else:
                # Other types - exact match
                similarity = 1.0 if val1 == val2 else 0.0
                similarity_scores.append(similarity)
        
        return np.mean(similarity_scores) if similarity_scores else 0.5
    
    def analyze_consistency(self, primitive_group: List[FramePrimitive]) -> ConsistencyResult:
        """
        Analyze consistency of a primitive group across frames
        """
        if len(primitive_group) < self.min_frames:
            return ConsistencyResult(
                primitive_id=f"insufficient_frames_{len(primitive_group)}",
                consistency_level=ConsistencyLevel.INCONSISTENT,
                consistency_score=0.0,
                frame_appearances=len(primitive_group),
                total_frames=self.min_frames,
                stability_metrics={},
                spatial_variance=float('inf'),
                confidence_variance=float('inf'),
                temporal_consistency=0.0,
                promotion_eligible=False
            )
        
        # Calculate consistency metrics
        spatial_variance = self._calculate_spatial_variance(primitive_group)
        confidence_variance = self._calculate_confidence_variance(primitive_group)
        temporal_consistency = self._calculate_temporal_consistency(primitive_group)
        
        # Overall consistency score
        consistency_score = self._calculate_overall_consistency(
            spatial_variance, confidence_variance, temporal_consistency, len(primitive_group)
        )
        
        # Determine consistency level
        consistency_level = self._determine_consistency_level(consistency_score)
        
        # Stability metrics
        stability_metrics = {
            "spatial_stability": max(0.0, 1.0 - (spatial_variance / (self.spatial_tolerance ** 2))),
            "confidence_stability": max(0.0, 1.0 - confidence_variance),
            "temporal_stability": temporal_consistency,
            "appearance_ratio": len(primitive_group) / self.min_frames
        }
        
        # Promotion eligibility (core law enforcement)
        promotion_eligible = bool(
            consistency_score >= self.consistency_threshold and
            spatial_variance <= (self.spatial_tolerance ** 2) and
            confidence_variance <= (self.confidence_tolerance ** 2) and
            temporal_consistency >= 0.7
        )
        
        return ConsistencyResult(
            primitive_id=f"consistent_prim_{primitive_group[0].primitive_type}_{int(time.time())}",
            consistency_level=consistency_level,
            consistency_score=float(consistency_score),
            frame_appearances=len(primitive_group),
            total_frames=self.min_frames,
            stability_metrics={k: float(v) for k, v in stability_metrics.items()},
            spatial_variance=float(spatial_variance),
            confidence_variance=float(confidence_variance),
            temporal_consistency=float(temporal_consistency),
            promotion_eligible=promotion_eligible
        )
    
    def _calculate_spatial_variance(self, primitive_group: List[FramePrimitive]) -> float:
        """Calculate spatial variance across frames"""
        if len(primitive_group) < 2:
            return 0.0
        
        coordinates = [prim.pixel_coordinates for prim in primitive_group]
        x_coords = [coord[0] for coord in coordinates]
        y_coords = [coord[1] for coord in coordinates]
        
        x_variance = np.var(x_coords) if len(x_coords) > 1 else 0.0
        y_variance = np.var(y_coords) if len(y_coords) > 1 else 0.0
        
        return x_variance + y_variance
    
    def _calculate_confidence_variance(self, primitive_group: List[FramePrimitive]) -> float:
        """Calculate confidence variance across frames"""
        if len(primitive_group) < 2:
            return 0.0
        
        confidences = [prim.confidence for prim in primitive_group]
        return np.var(confidences)
    
    def _calculate_temporal_consistency(self, primitive_group: List[FramePrimitive]) -> float:
        """Calculate temporal consistency (appearance pattern)"""
        frame_ids = [prim.frame_id for prim in primitive_group]
        frame_ids.sort()
        
        # Check for regular appearance pattern
        if len(frame_ids) < 2:
            return 1.0
        
        # Calculate frame gaps
        gaps = []
        for i in range(1, len(frame_ids)):
            gap = frame_ids[i] - frame_ids[i-1]
            gaps.append(gap)
        
        # Consistency is higher when gaps are uniform
        if len(gaps) <= 1:
            return 1.0
        
        gap_variance = np.var(gaps)
        max_gap = max(gaps) if gaps else 1
        
        # Normalize by maximum gap
        normalized_variance = gap_variance / (max_gap ** 2) if max_gap > 0 else 0.0
        temporal_consistency = max(0.0, 1.0 - normalized_variance)
        
        return temporal_consistency
    
    def _calculate_overall_consistency(self, spatial_variance: float, confidence_variance: float, 
                                     temporal_consistency: float, frame_count: int) -> float:
        """Calculate overall consistency score"""
        # Spatial consistency (40% weight)
        spatial_score = max(0.0, 1.0 - (spatial_variance / (self.spatial_tolerance ** 2)))
        
        # Confidence consistency (30% weight)
        confidence_score = max(0.0, 1.0 - confidence_variance)
        
        # Temporal consistency (20% weight)
        temporal_score = temporal_consistency
        
        # Frame coverage (10% weight)
        coverage_score = min(1.0, frame_count / self.min_frames)
        
        overall_score = (
            spatial_score * 0.4 +
            confidence_score * 0.3 +
            temporal_score * 0.2 +
            coverage_score * 0.1
        )
        
        return overall_score
    
    def _determine_consistency_level(self, consistency_score: float) -> ConsistencyLevel:
        """Determine consistency level from score"""
        if consistency_score >= 0.9:
            return ConsistencyLevel.VERY_HIGH
        elif consistency_score >= 0.7:
            return ConsistencyLevel.HIGH
        elif consistency_score >= 0.5:
            return ConsistencyLevel.MEDIUM
        elif consistency_score >= 0.3:
            return ConsistencyLevel.LOW
        else:
            return ConsistencyLevel.INCONSISTENT
    
    def validate_multi_frame_consistency(self, frame_primitives: List[List[Dict[str, Any]]]) -> List[ConsistencyResult]:
        """
        Validate multi-frame consistency for all primitives
        """
        # Track primitives across frames
        tracked_sequences = self.track_primitive_across_frames(frame_primitives)
        
        # Group similar primitives
        consistent_groups = self.group_similar_primitives(tracked_sequences)
        
        # Analyze consistency for each group
        consistency_results = []
        for group in consistent_groups:
            result = self.analyze_consistency(group)
            consistency_results.append(result)
        
        return consistency_results
    
    def generate_consistency_report(self, results: List[ConsistencyResult]) -> Dict[str, Any]:
        """Generate comprehensive consistency report"""
        if not results:
            return {
                "status": "no_consistent_primitives",
                "total_groups": 0,
                "promotion_eligible": 0,
                "recommendation": "insufficient_data"
            }
        
        promotion_eligible = [r for r in results if r.promotion_eligible]
        
        # Statistics
        consistency_scores = [r.consistency_score for r in results]
        spatial_variances = [r.spatial_variance for r in results]
        confidence_variances = [r.confidence_variance for r in results]
        
        return {
            "status": "analysis_complete",
            "total_groups": len(results),
            "promotion_eligible_count": len(promotion_eligible),
            "promotion_eligible_rate": len(promotion_eligible) / len(results),
            "average_consistency_score": np.mean(consistency_scores),
            "average_spatial_variance": np.mean(spatial_variances),
            "average_confidence_variance": np.mean(confidence_variances),
            "consistency_distribution": {
                "very_high": len([r for r in results if r.consistency_level == ConsistencyLevel.VERY_HIGH]),
                "high": len([r for r in results if r.consistency_level == ConsistencyLevel.HIGH]),
                "medium": len([r for r in results if r.consistency_level == ConsistencyLevel.MEDIUM]),
                "low": len([r for r in results if r.consistency_level == ConsistencyLevel.LOW]),
                "inconsistent": len([r for r in results if r.consistency_level == ConsistencyLevel.INCONSISTENT])
            },
            "recommendation": self._generate_recommendation(results),
            "core_law_compliance": {
                "multi_frame_consistency_enforced": True,
                "promotion_gates_active": True,
                "evidence_based_promotion": len(promotion_eligible) > 0
            }
        }
    
    def _generate_recommendation(self, results: List[ConsistencyResult]) -> str:
        """Generate recommendation based on consistency results"""
        promotion_eligible = [r for r in results if r.promotion_eligible]
        
        if len(promotion_eligible) == 0:
            avg_score = np.mean([r.consistency_score for r in results])
            if avg_score < 0.3:
                return "LOW_CONSISTENCY: Improve capture stability or increase tolerance"
            elif avg_score < 0.6:
                return "MEDIUM_CONSISTENCY: Refine primitive matching or add more frames"
            else:
                return "HIGH_CONSISTENCY: Adjust promotion thresholds or capture conditions"
        elif len(promotion_eligible) < len(results) * 0.5:
            return "PARTIAL_CONSISTENCY: Some primitives ready for promotion, others need improvement"
        else:
            return "HIGH_CONSISTENCY: Ready for executable promotion"


# Global validator instance
_multi_frame_validator = MultiFrameConsistencyValidator()

def validate_multi_frame_consistency(frame_primitives: List[List[Dict[str, Any]]]) -> List[ConsistencyResult]:
    """Convenience function for multi-frame consistency validation"""
    return _multi_frame_validator.validate_multi_frame_consistency(frame_primitives)

def generate_consistency_report(results: List[ConsistencyResult]) -> Dict[str, Any]:
    """Convenience function for consistency reporting"""
    return _multi_frame_validator.generate_consistency_report(results)
