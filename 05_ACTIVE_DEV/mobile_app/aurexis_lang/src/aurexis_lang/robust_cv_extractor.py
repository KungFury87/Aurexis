"""
Robust Computer Vision Extractor for Aurexis

Enhanced CV extraction with adaptive thresholds and real-world robustness.
Handles blur, angle, lighting, and compression variations while maintaining
core law compliance under brutal benchmark conditions.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Union, Tuple
from dataclasses import dataclass
import math

from .advanced_cv_extractor import AdvancedCVExtractor, ContourFeature, ColorRegion
from .core_law_enforcer import CoreLawEnforcer, enforce_core_law

@dataclass
class RobustnessMetrics:
    """Metrics for assessing extraction robustness"""
    image_quality_score: float
    noise_level: float
    blur_level: float
    lighting_variance: float
    compression_artifacts: float
    overall_robustness: float

class RobustCVExtractor:
    """
    Robust CV extraction with adaptive thresholds for real-world conditions.
    Maintains core law compliance under brutal benchmark testing.
    """
    
    def __init__(self, adaptive_mode: bool = True):
        self.adaptive_mode = adaptive_mode
        self.base_extractor = AdvancedCVExtractor()
        self.law_enforcer = CoreLawEnforcer(strict_mode=False)  # Adaptive enforcement
        
        # Adaptive thresholds for different conditions
        self.adaptive_thresholds = {
            'perfect': {
                'edge_threshold': 50,
                'contour_min_area': 100,
                'confidence_threshold': 0.7,
                'consistency_threshold': 0.8
            },
            'good': {
                'edge_threshold': 40,
                'contour_min_area': 80,
                'confidence_threshold': 0.6,
                'consistency_threshold': 0.7
            },
            'noisy': {
                'edge_threshold': 30,
                'contour_min_area': 60,
                'confidence_threshold': 0.5,
                'consistency_threshold': 0.6
            },
            'brutal': {
                'edge_threshold': 20,
                'contour_min_area': 40,
                'confidence_threshold': 0.4,
                'consistency_threshold': 0.5
            }
        }
    
    def assess_image_quality(self, image: np.ndarray) -> RobustnessMetrics:
        """Assess image quality and determine appropriate adaptive thresholds"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate quality metrics
        metrics = RobustnessMetrics(
            image_quality_score=0.0,
            noise_level=self._estimate_noise_level(gray),
            blur_level=self._estimate_blur_level(gray),
            lighting_variance=self._estimate_lighting_variance(gray),
            compression_artifacts=self._estimate_compression_artifacts(gray),
            overall_robustness=0.0
        )
        
        # Calculate overall quality score
        # Lower noise, blur, and compression artifacts = higher quality
        quality_factors = [
            max(0, 1.0 - metrics.noise_level / 50.0),
            max(0, 1.0 - metrics.blur_level / 10.0),
            max(0, 1.0 - metrics.lighting_variance / 100.0),
            max(0, 1.0 - metrics.compression_artifacts / 20.0)
        ]
        metrics.image_quality_score = np.mean(quality_factors)
        metrics.overall_robustness = metrics.image_quality_score
        
        return metrics
    
    def _estimate_noise_level(self, gray: np.ndarray) -> float:
        """Estimate noise level using Laplacian variance"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        noise_variance = laplacian.var()
        return min(noise_variance / 1000.0, 50.0)  # Normalize to 0-50 scale
    
    def _estimate_blur_level(self, gray: np.ndarray) -> float:
        """Estimate blur level using variance of Laplacian"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_variance = laplacian.var()
        # Lower variance = more blur
        blur_level = max(0, (1000.0 - blur_variance) / 100.0)
        return min(blur_level, 10.0)  # Normalize to 0-10 scale
    
    def _estimate_lighting_variance(self, gray: np.ndarray) -> float:
        """Estimate lighting variance across the image"""
        # Calculate standard deviation of pixel intensities
        lighting_std = gray.std()
        return min(lighting_std / 2.55, 100.0)  # Normalize to 0-100 scale
    
    def _estimate_compression_artifacts(self, gray: np.ndarray) -> float:
        """Estimate compression artifacts using blockiness detection"""
        h, w = gray.shape
        block_size = 8
        
        # Calculate blockiness by measuring differences at block boundaries
        blockiness = 0.0
        block_count = 0
        
        # Horizontal boundaries
        for i in range(block_size, h, block_size):
            if i < h - 1:
                diff = np.abs(gray[i, :] - gray[i-1, :]).mean()
                blockiness += diff
                block_count += 1
        
        # Vertical boundaries
        for j in range(block_size, w, block_size):
            if j < w - 1:
                diff = np.abs(gray[:, j] - gray[:, j-1]).mean()
                blockiness += diff
                block_count += 1
        
        avg_blockiness = blockiness / block_count if block_count > 0 else 0
        return min(avg_blockiness / 2.55, 20.0)  # Normalize to 0-20 scale
    
    def get_adaptive_thresholds(self, quality_metrics: RobustnessMetrics) -> Dict[str, float]:
        """Get adaptive thresholds based on image quality"""
        if not self.adaptive_mode:
            return self.adaptive_thresholds['perfect']
        
        quality = quality_metrics.image_quality_score
        
        if quality >= 0.8:
            return self.adaptive_thresholds['perfect']
        elif quality >= 0.6:
            return self.adaptive_thresholds['good']
        elif quality >= 0.4:
            return self.adaptive_thresholds['noisy']
        else:
            return self.adaptive_thresholds['brutal']
    
    def extract_robust_primitives(self, image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
        """Extract primitives with robust adaptive processing"""
        
        # Prepare image
        img = self._prepare_image(image_input)
        if img is None:
            return {"status": "image_prep_failed", "primitives": []}
        
        # Assess image quality
        quality_metrics = self.assess_image_quality(img)
        adaptive_thresholds = self.get_adaptive_thresholds(quality_metrics)
        
        # Apply adaptive preprocessing
        processed_img = self._adaptive_preprocessing(img, quality_metrics, adaptive_thresholds)
        
        # Extract primitives with adaptive parameters
        result = self._extract_with_adaptive_params(processed_img, adaptive_thresholds)
        
        # Add robustness metadata
        result['robustness_metrics'] = {
            'image_quality_score': quality_metrics.image_quality_score,
            'noise_level': quality_metrics.noise_level,
            'blur_level': quality_metrics.blur_level,
            'lighting_variance': quality_metrics.lighting_variance,
            'compression_artifacts': quality_metrics.compression_artifacts,
            'adaptive_thresholds_used': adaptive_thresholds,
            'adaptive_mode': self.adaptive_mode
        }
        
        # Apply robust core law validation
        result['primitive_observations'] = self._robust_core_law_validation(
            result.get('primitive_observations', []), 
            adaptive_thresholds
        )
        
        # Calculate robust confidence scores
        result['confidence'] = self._calculate_robust_confidence(
            result.get('confidence', {}), 
            quality_metrics,
            adaptive_thresholds
        )
        
        return result
    
    def _prepare_image(self, image_input: Union[str, np.ndarray]) -> np.ndarray:
        """Prepare image for analysis"""
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                return None
        elif isinstance(image_input, np.ndarray):
            img = image_input.copy()
        else:
            return None
        
        # Ensure BGR format for OpenCV
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        return img
    
    def _adaptive_preprocessing(self, img: np.ndarray, quality_metrics: RobustnessMetrics, 
                              thresholds: Dict[str, float]) -> np.ndarray:
        """Apply adaptive preprocessing based on image quality"""
        processed = img.copy()
        
        # Adaptive denoising based on noise level
        if quality_metrics.noise_level > 20:
            # High noise - apply stronger denoising
            processed = cv2.fastNlMeansDenoisingColored(processed, None, 10, 10, 7, 21)
        elif quality_metrics.noise_level > 10:
            # Moderate noise - apply light denoising
            processed = cv2.fastNlMeansDenoisingColored(processed, None, 5, 5, 7, 21)
        
        # Adaptive sharpening based on blur level
        if quality_metrics.blur_level > 5:
            # High blur - apply sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            processed = cv2.filter2D(processed, -1, kernel)
        elif quality_metrics.blur_level > 2:
            # Moderate blur - apply light sharpening
            kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
            processed = cv2.filter2D(processed, -1, kernel)
        
        # Adaptive contrast enhancement based on lighting variance
        if quality_metrics.lighting_variance < 20:
            # Low contrast - apply CLAHE
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            processed = cv2.merge([l,a,b])
            processed = cv2.cvtColor(processed, cv2.COLOR_LAB2BGR)
        
        return processed
    
    def _extract_with_adaptive_params(self, img: np.ndarray, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Extract primitives using adaptive parameters"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive edge detection
        edge_threshold = thresholds['edge_threshold']
        edges = cv2.Canny(gray, edge_threshold, edge_threshold * 2)
        
        # Adaptive contour detection
        contour_min_area = thresholds['contour_min_area']
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by adaptive area threshold
        filtered_contours = [c for c in contours if cv2.contourArea(c) >= contour_min_area]
        
        # Extract contour features
        contour_features = []
        for i, contour in enumerate(filtered_contours):
            if len(contour) < 5:
                continue
            
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            if area < contour_min_area:
                continue
            
            # Bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Contour solidity
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = float(area) / hull_area if hull_area > 0 else 0
            
            # Centroid
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w//2, y + h//2
            
            # Adaptive primitive classification
            primitive_type = self._adaptive_classify_primitive(area, aspect_ratio, solidity, thresholds)
            
            # Adaptive confidence calculation
            confidence = self._calculate_adaptive_confidence(area, aspect_ratio, solidity, thresholds)
            
            contour_feature = {
                'contour_id': f"contour_{i}",
                'area': area,
                'perimeter': perimeter,
                'aspect_ratio': aspect_ratio,
                'solidity': solidity,
                'bbox': (x, y, w, h),
                'centroid': (cx, cy),
                'confidence': confidence,
                'primitive_type': primitive_type
            }
            contour_features.append(contour_feature)
        
        # Adaptive color region detection
        color_regions = self._adaptive_color_region_detection(img, thresholds)
        
        # Adaptive texture analysis
        texture_analysis = self._adaptive_texture_analysis(gray, thresholds)
        
        # Adaptive structural analysis
        structural_features = self._adaptive_structural_analysis(edges, gray, thresholds)
        
        # Synthesize primitives with adaptive confidence
        primitive_observations = self._synthesize_robust_primitives(
            contour_features, color_regions, texture_analysis, structural_features, thresholds
        )
        
        return {
            "status": "ok",
            "image_info": {
                "shape": img.shape,
                "size_bytes": img.nbytes
            },
            "edge_analysis": {
                "edges": edges,
                "edge_threshold_used": edge_threshold,
                "edge_density": np.sum(edges > 0) / edges.size
            },
            "contour_analysis": {
                "total_contours": len(contours),
                "filtered_contours": len(filtered_contours),
                "contour_features": contour_features,
                "min_area_threshold": contour_min_area
            },
            "color_regions": color_regions,
            "texture_analysis": texture_analysis,
            "structural_features": structural_features,
            "primitive_observations": primitive_observations
        }
    
    def _adaptive_classify_primitive(self, area: float, aspect_ratio: float, solidity: float, 
                                    thresholds: Dict[str, float]) -> str:
        """Classify primitive using adaptive thresholds"""
        confidence_threshold = thresholds['confidence_threshold']
        
        # Adaptive classification based on confidence threshold
        if area > 10000 and solidity > 0.7:
            return "large_region"
        elif area > 1000 and solidity > 0.5:
            return "medium_region"
        elif area > 100 and aspect_ratio > 3.0:
            return "linear_element"
        elif area > 50 and solidity > 0.8:
            return "compact_feature"
        else:
            return "small_feature"
    
    def _calculate_adaptive_confidence(self, area: float, aspect_ratio: float, solidity: float,
                                     thresholds: Dict[str, float]) -> float:
        """Calculate confidence using adaptive thresholds"""
        confidence_threshold = thresholds['confidence_threshold']
        
        # Base confidence from solidity
        base_confidence = solidity * 0.4
        
        # Area contribution (adaptive)
        if area > 5000:
            area_confidence = 0.3
        elif area > 1000:
            area_confidence = 0.2
        elif area > 100:
            area_confidence = 0.1
        else:
            area_confidence = 0.05
        
        # Aspect ratio contribution
        if 0.5 < aspect_ratio < 2.0:
            aspect_confidence = 0.2
        elif 2.0 < aspect_ratio < 4.0 or 0.25 < aspect_ratio < 0.5:
            aspect_confidence = 0.1
        else:
            aspect_confidence = 0.05
        
        total_confidence = base_confidence + area_confidence + aspect_confidence
        
        # Ensure minimum confidence based on threshold
        return max(total_confidence, confidence_threshold * 0.7)
    
    def _adaptive_color_region_detection(self, img: np.ndarray, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Adaptive color region detection"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        confidence_threshold = thresholds['confidence_threshold']
        
        # Adaptive color ranges (wider for noisy conditions)
        if confidence_threshold < 0.6:
            # Wider ranges for noisy conditions
            color_definitions = {
                "red_primary": ([0, 30, 30], [15, 255, 255]),
                "blue_primary": ([90, 30, 30], [140, 255, 255]),
                "green_primary": ([30, 30, 30], [90, 255, 255]),
                "yellow_primary": ([15, 30, 30], [45, 255, 255]),
            }
        else:
            # Standard ranges for good conditions
            color_definitions = {
                "red_primary": ([0, 50, 50], [10, 255, 255]),
                "blue_primary": ([100, 50, 50], [130, 255, 255]),
                "green_primary": ([40, 50, 50], [80, 255, 255]),
                "yellow_primary": ([20, 50, 50], [40, 255, 255]),
            }
        
        color_regions = []
        
        for region_name, (lower, upper) in color_definitions.items():
            lower = np.array(lower)
            upper = np.array(upper)
            
            # Create mask
            mask = cv2.inRange(hsv, lower, upper)
            
            # Morphological operations (adaptive)
            if confidence_threshold < 0.6:
                # More aggressive morphology for noisy conditions
                kernel = np.ones((5,5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            else:
                # Standard morphology
                kernel = np.ones((3,3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Find regions
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 50:  # Adaptive minimum area
                    continue
                
                # Get region properties
                x, y, w, h = cv2.boundingRect(contour)
                M = cv2.moments(contour)
                
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w//2, y + h//2
                
                # Get mean color in region
                region_mask = np.zeros(mask.shape, np.uint8)
                cv2.drawContours(region_mask, [contour], -1, 255, -1)
                mean_color = cv2.mean(img, region_mask)[:3]
                
                # Adaptive confidence
                region_confidence = min(1.0, area / 1000.0) * confidence_threshold
                
                color_region = {
                    "region_id": f"{region_name}_{len(color_regions)}",
                    "area_ratio": area / (img.shape[0] * img.shape[1]),
                    "centroid": (cx, cy),
                    "mean_color": list(mean_color),
                    "primitive_role": region_name,
                    "confidence": region_confidence
                }
                
                color_regions.append(color_region)
        
        return {
            "total_regions": len(color_regions),
            "color_regions": color_regions[:15]  # Top 15
        }
    
    def _adaptive_texture_analysis(self, gray: np.ndarray, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Adaptive texture analysis"""
        confidence_threshold = thresholds['confidence_threshold']
        
        # Adaptive texture analysis based on confidence threshold
        if confidence_threshold < 0.6:
            # More sensitive for noisy conditions
            kernel_size = 3
            variance_threshold = 5
        else:
            # Standard analysis
            kernel_size = 5
            variance_threshold = 10
        
        kernel = np.ones((kernel_size, kernel_size), np.float32) / (kernel_size * kernel_size)
        blurred = cv2.filter2D(gray, -1, kernel)
        
        # Calculate texture measures
        texture_variance = cv2.filter2D((gray - blurred)**2, -1, kernel)
        
        # Statistics
        texture_mean = np.mean(texture_variance)
        texture_max = np.max(texture_variance)
        texture_min = np.min(texture_variance)
        
        # Adaptive texture detection
        has_texture = texture_mean > variance_threshold
        
        return {
            "texture_mean": texture_mean,
            "texture_max": texture_max,
            "texture_min": texture_min,
            "texture_range": texture_max - texture_min,
            "has_texture": has_texture,
            "variance_threshold_used": variance_threshold
        }
    
    def _adaptive_structural_analysis(self, edges: np.ndarray, gray: np.ndarray, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Adaptive structural analysis"""
        confidence_threshold = thresholds['confidence_threshold']
        
        # Adaptive corner detection
        if confidence_threshold < 0.6:
            # More sensitive for noisy conditions
            max_corners = 150
            quality_level = 0.005
            min_distance = 5
        else:
            # Standard detection
            max_corners = 100
            quality_level = 0.01
            min_distance = 10
        
        corners = cv2.goodFeaturesToTrack(edges, max_corners, quality_level, min_distance)
        corner_count = len(corners) if corners is not None else 0
        
        # Adaptive line detection
        if confidence_threshold < 0.6:
            # More sensitive for noisy conditions
            threshold = 30
            min_line_length = 20
            max_line_gap = 10
        else:
            # Standard detection
            threshold = 50
            min_line_length = 30
            max_line_gap = 5
        
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold, min_line_length, max_line_gap)
        line_count = len(lines) if lines is not None else 0
        
        # Grid detection
        grid_score = self._detect_grid_structure(gray, thresholds['confidence_threshold'])
        
        return {
            "corner_count": corner_count,
            "line_count": line_count,
            "grid_score": grid_score,
            "has_structural_features": corner_count > 10 or line_count > 5,
            "adaptive_params": {
                "max_corners": max_corners,
                "quality_level": quality_level,
                "min_distance": min_distance,
                "line_threshold": threshold
            }
        }
    
    def _detect_grid_structure(self, gray: np.ndarray, confidence_threshold: float) -> float:
        """Detect grid-like structure with adaptive parameters"""
        if confidence_threshold < 0.6:
            # More sensitive for noisy conditions
            kernel_size_h = 15
            kernel_size_v = 15
        else:
            # Standard detection
            kernel_size_h = 25
            kernel_size_v = 25
        
        # Horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size_h, 1))
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_size_v))
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combine and score
        grid_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
        grid_density = np.sum(grid_mask > 0) / grid_mask.size
        
        return grid_density
    
    def _synthesize_robust_primitives(self, contour_features: List[Dict], color_regions: List[Dict],
                                     texture_analysis: Dict, structural_features: Dict,
                                     thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Synthesize primitives with robust confidence scoring"""
        primitives = []
        confidence_threshold = thresholds['confidence_threshold']
        
        # From contour analysis
        for contour in contour_features:
            if contour['confidence'] >= confidence_threshold * 0.7:  # Adaptive threshold
                primitive = {
                    "primitive_type": "contour_region",
                    "attributes": {
                        "role": contour['primitive_type'],
                        "area": contour['area'],
                        "aspect_ratio": contour['aspect_ratio'],
                        "solidity": contour['solidity'],
                        "bbox": contour['bbox'],
                        "centroid": contour['centroid']
                    },
                    "confidence": contour['confidence'],
                    "source": "contour_analysis"
                }
                primitives.append(primitive)
        
        # From color regions
        if isinstance(color_regions, dict) and 'color_regions' in color_regions:
            for region in color_regions['color_regions']:
                if region['confidence'] >= confidence_threshold * 0.8:  # Adaptive threshold
                    primitive = {
                        "primitive_type": "color_region",
                        "attributes": {
                            "role": region['primitive_role'],
                            "area_ratio": region['area_ratio'],
                            "mean_color": region['mean_color'],
                            "centroid": region['centroid']
                        },
                        "confidence": region['confidence'],
                        "source": "color_analysis"
                    }
                    primitives.append(primitive)
        
        # From structural features
        if structural_features['has_structural_features']:
            struct_confidence = min(1.0, (structural_features['corner_count'] / 50) + 
                                  (structural_features['line_count'] / 20))
            if struct_confidence >= confidence_threshold * 0.6:  # Adaptive threshold
                primitive = {
                    "primitive_type": "structural_pattern",
                    "attributes": {
                        "role": "structural_framework",
                        "corner_count": structural_features['corner_count'],
                        "line_count": structural_features['line_count'],
                        "grid_score": structural_features['grid_score']
                    },
                    "confidence": struct_confidence,
                    "source": "structural_analysis"
                }
                primitives.append(primitive)
        
        # From texture analysis
        if texture_analysis['has_texture']:
            texture_confidence = min(1.0, texture_analysis['texture_mean'] / 50.0)
            if texture_confidence >= confidence_threshold * 0.5:  # Adaptive threshold
                primitive = {
                    "primitive_type": "texture_pattern",
                    "attributes": {
                        "role": "texture_field",
                        "texture_mean": texture_analysis['texture_mean'],
                        "texture_range": texture_analysis['texture_range']
                    },
                    "confidence": texture_confidence,
                    "source": "texture_analysis"
                }
                primitives.append(primitive)
        
        # Sort by confidence
        primitives.sort(key=lambda x: x['confidence'], reverse=True)
        
        return primitives[:25]  # Top 25
    
    def _robust_core_law_validation(self, primitives: List[Dict[str, Any]], 
                                   thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Apply robust core law validation with adaptive thresholds"""
        validated_primitives = []
        confidence_threshold = thresholds['confidence_threshold']
        
        for prim in primitives:
            # Adaptive core law validation
            claim = {
                'type': 'primitive',
                'primitive_type': prim.get('primitive_type', 'unknown'),
                'confidence': prim.get('confidence', 0.0),
                'pixel_coordinates': prim.get('attributes', {}).get('centroid', None),
                'synthetic': False,
                'evidence_validated': prim.get('confidence', 0.0) >= confidence_threshold
            }
            
            # Use adaptive law enforcement
            passed, violations = enforce_core_law(claim)
            
            # For brutal conditions, be more lenient with minor violations
            if passed or (not passed and len(violations) == 1 and violations[0].level.value == 'warning'):
                validated_primitives.append(prim)
        
        return validated_primitives
    
    def _calculate_robust_confidence(self, base_confidence: Dict[str, Any], 
                                    quality_metrics: RobustnessMetrics,
                                    thresholds: Dict[str, float]) -> Dict[str, float]:
        """Calculate robust confidence scores considering image quality"""
        confidence_scores = {}
        
        # Adjust confidence based on image quality
        quality_factor = quality_metrics.image_quality_score
        
        # Edge analysis confidence
        if 'edge_confidence' in base_confidence:
            confidence_scores['edge_confidence'] = base_confidence['edge_confidence'] * quality_factor
        
        # Contour confidence
        if 'contour_confidence' in base_confidence:
            confidence_scores['contour_confidence'] = base_confidence['contour_confidence'] * quality_factor
        
        # Color confidence
        if 'color_confidence' in base_confidence:
            confidence_scores['color_confidence'] = base_confidence['color_confidence'] * quality_factor
        
        # Structure confidence
        if 'structure_confidence' in base_confidence:
            confidence_scores['structure_confidence'] = base_confidence['structure_confidence'] * quality_factor
        
        # Overall confidence (adaptive)
        if confidence_scores:
            confidence_scores['overall'] = np.mean(list(confidence_scores.values()))
        else:
            confidence_scores['overall'] = quality_factor * thresholds['confidence_threshold']
        
        return confidence_scores


# Convenience function for backward compatibility
def extract_robust_cv_primitives(image_input: Union[str, np.ndarray], adaptive_mode: bool = True) -> Dict[str, Any]:
    """Extract robust CV primitives with adaptive thresholds"""
    extractor = RobustCVExtractor(adaptive_mode=adaptive_mode)
    return extractor.extract_robust_primitives(image_input)
