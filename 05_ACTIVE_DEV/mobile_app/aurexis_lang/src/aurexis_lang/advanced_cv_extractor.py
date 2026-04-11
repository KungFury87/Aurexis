"""
Advanced Computer Vision Extractor for Aurexis

Enhanced CV extraction with advanced edge detection, contour analysis,
color segmentation, and sophisticated feature recognition.
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Union, Tuple
from dataclasses import dataclass
import math

@dataclass
class ContourFeature:
    """Represents a detected contour with analysis"""
    contour_id: str
    area: float
    perimeter: float
    aspect_ratio: float
    extent: float
    solidity: float
    bbox: Tuple[int, int, int, int]
    centroid: Tuple[int, int]
    confidence: float
    primitive_type: str

@dataclass
class ColorRegion:
    """Represents a color-based region"""
    region_id: str
    color_range: Tuple[np.ndarray, np.ndarray]
    area_ratio: float
    centroid: Tuple[int, int]
    mean_color: np.ndarray
    primitive_role: str
    confidence: float

class AdvancedCVExtractor:
    """Advanced CV extraction with multiple analysis layers"""
    
    def __init__(self):
        self.edge_detectors = {
            'canny': self._canny_edges,
            'sobel': self._sobel_edges,
            'laplacian': self._laplacian_edges,
            'adaptive': self._adaptive_edges
        }
    
    def extract_advanced_primitives(self, image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
        """Extract advanced primitives using multiple CV techniques"""
        
        # Convert input to numpy array
        img = self._prepare_image(image_input)
        if img is None:
            return {"status": "image_prep_failed", "primitives": []}
        
        # Multi-layer analysis
        results = {
            "source": str(image_input) if isinstance(image_input, str) else "numpy_array",
            "status": "ok",
            "image_info": {
                "shape": img.shape,
                "size_bytes": img.nbytes
            },
            "edge_analysis": self._analyze_edges(img),
            "contour_analysis": self._analyze_contours(img),
            "color_regions": self._analyze_color_regions(img),
            "texture_analysis": self._analyze_texture(img),
            "structural_features": self._analyze_structure(img),
            "primitive_observations": []
        }
        
        # Combine all analyses into primitive observations
        results["primitive_observations"] = self._synthesize_primitives(results)
        
        # Calculate overall confidence
        results["confidence"] = self._calculate_overall_confidence(results)
        
        return results
    
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
    
    def _analyze_edges(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze edges using multiple detectors"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        edge_results = {}
        
        # Canny edge detection
        edge_results['canny'] = self._canny_edges(gray)
        
        # Sobel edge detection
        edge_results['sobel'] = self._sobel_edges(gray)
        
        # Laplacian edge detection
        edge_results['laplacian'] = self._laplacian_edges(gray)
        
        # Adaptive threshold
        edge_results['adaptive'] = self._adaptive_edges(gray)
        
        # Edge density analysis
        edge_results['density_analysis'] = self._analyze_edge_density(edge_results)
        
        return edge_results
    
    def _canny_edges(self, gray: np.ndarray) -> Dict[str, Any]:
        """Canny edge detection"""
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Find edge contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return {
            "edges": edges,
            "edge_density": edge_density,
            "contour_count": len(contours),
            "method": "canny"
        }
    
    def _sobel_edges(self, gray: np.ndarray) -> Dict[str, Any]:
        """Sobel edge detection"""
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        magnitude = np.sqrt(sobelx**2 + sobely**2)
        magnitude = np.clip(magnitude, 0, 255).astype(np.uint8)
        
        edge_density = np.sum(magnitude > 30) / magnitude.size
        
        return {
            "edges": magnitude,
            "edge_density": edge_density,
            "gradient_x": sobelx,
            "gradient_y": sobely,
            "method": "sobel"
        }
    
    def _laplacian_edges(self, gray: np.ndarray) -> Dict[str, Any]:
        """Laplacian edge detection"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian = np.absolute(laplacian)
        laplacian = np.clip(laplacian, 0, 255).astype(np.uint8)
        
        edge_density = np.sum(laplacian > 30) / laplacian.size
        
        return {
            "edges": laplacian,
            "edge_density": edge_density,
            "method": "laplacian"
        }
    
    def _adaptive_edges(self, gray: np.ndarray) -> Dict[str, Any]:
        """Adaptive threshold edge detection"""
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
        edge_density = np.sum(adaptive == 255) / adaptive.size
        
        return {
            "edges": adaptive,
            "edge_density": edge_density,
            "method": "adaptive"
        }
    
    def _analyze_edge_density(self, edge_results: Dict[str, Any]) -> Dict[str, float]:
        """Analyze edge density across different methods"""
        densities = {}
        for method, result in edge_results.items():
            if 'edge_density' in result:
                densities[method] = result['edge_density']
        
        return {
            "mean_density": np.mean(list(densities.values())),
            "std_density": np.std(list(densities.values())),
            "max_density": np.max(list(densities.values())),
            "min_density": np.min(list(densities.values())),
            "densities": densities
        }
    
    def _analyze_contours(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze contours with advanced filtering"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Use Canny edges for contour detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        contour_features = []
        
        for i, contour in enumerate(contours):
            if len(contour) < 5:  # Skip very small contours
                continue
            
            # Calculate contour properties
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            if area < 100:  # Skip tiny areas
                continue
            
            # Bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Contour solidity
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = float(area) / hull_area if hull_area > 0 else 0
            
            # Contour extent
            rect_area = w * h
            extent = float(area) / rect_area if rect_area > 0 else 0
            
            # Centroid
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w//2, y + h//2
            
            # Determine primitive type based on properties
            primitive_type = self._classify_contour_primitive(area, aspect_ratio, solidity, extent)
            
            # Calculate confidence
            confidence = self._calculate_contour_confidence(area, aspect_ratio, solidity, extent)
            
            contour_feature = ContourFeature(
                contour_id=f"contour_{i}",
                area=area,
                perimeter=perimeter,
                aspect_ratio=aspect_ratio,
                extent=extent,
                solidity=solidity,
                bbox=(x, y, w, h),
                centroid=(cx, cy),
                confidence=confidence,
                primitive_type=primitive_type
            )
            
            contour_features.append(contour_feature)
        
        # Sort by confidence
        contour_features.sort(key=lambda x: x.confidence, reverse=True)
        
        return {
            "total_contours": len(contours),
            "filtered_contours": len(contour_features),
            "contour_features": [self._contour_to_dict(cf) for cf in contour_features[:20]]  # Top 20
        }
    
    def _classify_contour_primitive(self, area: float, aspect_ratio: float, solidity: float, extent: float) -> str:
        """Classify contour as primitive type"""
        
        # Central sigil candidate: moderate area, high solidity, balanced aspect
        if 500 < area < 50000 and solidity > 0.8 and 0.5 < aspect_ratio < 2.0:
            return "central_sigil"
        
        # Ring/delimiter: large area, moderate solidity
        elif area > 10000 and 0.5 < solidity < 0.9:
            return "ring_delimiter"
        
        # Linear element: high aspect ratio
        elif aspect_ratio > 3.0 or aspect_ratio < 0.33:
            return "linear_element"
        
        # Point/small feature: small area
        elif area < 500:
            return "point_feature"
        
        # Complex region: irregular shape
        elif solidity < 0.5:
            return "complex_region"
        
        # Standard region
        else:
            return "standard_region"
    
    def _calculate_contour_confidence(self, area: float, aspect_ratio: float, solidity: float, extent: float) -> float:
        """Calculate confidence score for contour"""
        
        # Base confidence from solidity (well-defined shapes)
        confidence = solidity * 0.4
        
        # Area contribution (not too small, not too large)
        if 100 < area < 10000:
            confidence += 0.2
        elif 10000 <= area < 50000:
            confidence += 0.1
        
        # Aspect ratio contribution (balanced ratios are often meaningful)
        if 0.5 < aspect_ratio < 2.0:
            confidence += 0.2
        elif 2.0 < aspect_ratio < 4.0 or 0.25 < aspect_ratio < 0.5:
            confidence += 0.1
        
        # Extent contribution (well-filled bounding boxes)
        if extent > 0.5:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _contour_to_dict(self, contour_feature: ContourFeature) -> Dict[str, Any]:
        """Convert contour feature to dictionary"""
        return {
            "contour_id": contour_feature.contour_id,
            "area": contour_feature.area,
            "perimeter": contour_feature.perimeter,
            "aspect_ratio": contour_feature.aspect_ratio,
            "extent": contour_feature.extent,
            "solidity": contour_feature.solidity,
            "bbox": contour_feature.bbox,
            "centroid": contour_feature.centroid,
            "confidence": contour_feature.confidence,
            "primitive_type": contour_feature.primitive_type
        }
    
    def _analyze_color_regions(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze color-based regions"""
        
        # Convert to different color spaces
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        
        color_regions = []
        
        # Define color ranges for different regions
        color_definitions = {
            "red_primary": ([0, 50, 50], [10, 255, 255]),  # Red in HSV
            "blue_primary": ([100, 50, 50], [130, 255, 255]),  # Blue in HSV
            "green_primary": ([40, 50, 50], [80, 255, 255]),  # Green in HSV
            "yellow_primary": ([20, 50, 50], [40, 255, 255]),  # Yellow in HSV
            "warm_colors": ([0, 30, 50], [40, 255, 255]),  # Warm range
            "cool_colors": ([90, 30, 50], [180, 255, 255]),  # Cool range
        }
        
        for region_name, (lower, upper) in color_definitions.items():
            lower = np.array(lower)
            upper = np.array(upper)
            
            # Create mask
            mask = cv2.inRange(hsv, lower, upper)
            
            # Find regions
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area < 100:  # Skip small regions
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
                
                # Determine primitive role
                role = self._classify_color_region_role(region_name, area, (w, h))
                
                # Calculate confidence
                confidence = self._calculate_color_confidence(area, w, h, mean_color)
                
                color_region = ColorRegion(
                    region_id=f"{region_name}_{i}",
                    color_range=(lower, upper),
                    area_ratio=area / (img.shape[0] * img.shape[1]),
                    centroid=(cx, cy),
                    mean_color=mean_color,
                    primitive_role=role,
                    confidence=confidence
                )
                
                color_regions.append(color_region)
        
        # Sort by confidence
        color_regions.sort(key=lambda x: x.confidence, reverse=True)
        
        return {
            "total_regions": len(color_regions),
            "color_regions": [self._color_region_to_dict(cr) for cr in color_regions[:15]]  # Top 15
        }
    
    def _classify_color_region_role(self, color_name: str, area: float, size: Tuple[int, int]) -> str:
        """Classify color region role"""
        
        if "primary" in color_name and area > 1000:
            return "primary_element"
        elif "warm" in color_name:
            return "warm_field"
        elif "cool" in color_name:
            return "cool_field"
        elif area < 500:
            return "accent_feature"
        else:
            return "background_region"
    
    def _calculate_color_confidence(self, area: float, w: int, h: int, mean_color: np.ndarray) -> float:
        """Calculate confidence for color region"""
        
        confidence = 0.0
        
        # Area contribution
        if 200 < area < 10000:
            confidence += 0.3
        elif 10000 <= area < 50000:
            confidence += 0.2
        
        # Size contribution (well-proportioned regions)
        aspect = w / h if h > 0 else 0
        if 0.5 < aspect < 2.0:
            confidence += 0.2
        
        # Color saturation contribution
        max_val = np.max(mean_color)
        if max_val > 100:  # Strong color
            confidence += 0.3
        
        # Color purity contribution
        color_range = np.max(mean_color) - np.min(mean_color)
        if color_range > 50:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _color_region_to_dict(self, color_region: ColorRegion) -> Dict[str, Any]:
        """Convert color region to dictionary"""
        return {
            "region_id": color_region.region_id,
            "area_ratio": color_region.area_ratio,
            "centroid": color_region.centroid,
            "mean_color": list(color_region.mean_color) if hasattr(color_region.mean_color, 'tolist') else color_region.mean_color,
            "primitive_role": color_region.primitive_role,
            "confidence": color_region.confidence
        }
    
    def _analyze_texture(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze texture patterns"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Local Binary Pattern for texture
        try:
            # Simple texture analysis using variance filters
            kernel = np.ones((5, 5), np.float32) / 25
            blurred = cv2.filter2D(gray, -1, kernel)
            
            # Calculate texture measures
            texture_variance = cv2.filter2D((gray - blurred)**2, -1, kernel)
            
            # Standard deviation as texture measure
            texture_std = np.sqrt(texture_variance)
            
            # Texture statistics
            texture_mean = np.mean(texture_std)
            texture_max = np.max(texture_std)
            texture_min = np.min(texture_std)
            
            return {
                "texture_mean": texture_mean,
                "texture_max": texture_max,
                "texture_min": texture_min,
                "texture_range": texture_max - texture_min,
                "has_texture": texture_mean > 10
            }
        except Exception as e:
            return {"error": str(e), "has_texture": False}
    
    def _analyze_structure(self, img: np.ndarray) -> Dict[str, Any]:
        """Analyze structural features"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Harris corner detection
        corners = cv2.goodFeaturesToTrack(gray, maxCorners=100, qualityLevel=0.01, minDistance=10)
        corner_count = len(corners) if corners is not None else 0
        
        # Hough lines for linear structures
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
        line_count = len(lines) if lines is not None else 0
        
        # Grid detection
        grid_score = self._detect_grid_structure(gray)
        
        return {
            "corner_count": corner_count,
            "line_count": line_count,
            "grid_score": grid_score,
            "has_structural_features": corner_count > 5 or line_count > 3
        }
    
    def _detect_grid_structure(self, gray: np.ndarray) -> float:
        """Detect grid-like structures"""
        # Simple grid detection using horizontal and vertical lines
        edges = cv2.Canny(gray, 50, 150)
        
        # Horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        vertical_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combine and score
        grid_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
        grid_density = np.sum(grid_mask > 0) / grid_mask.size
        
        return grid_density
    
    def _synthesize_primitives(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Synthesize all analyses into primitive observations"""
        primitives = []
        
        # From contour analysis
        if 'contour_analysis' in results:
            for contour in results['contour_analysis']['contour_features']:
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
        if 'color_regions' in results:
            for region in results['color_regions']['color_regions']:
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
        
        # From structural analysis
        if 'structural_features' in results:
            struct = results['structural_features']
            if struct['has_structural_features']:
                primitive = {
                    "primitive_type": "structural_pattern",
                    "attributes": {
                        "role": "structural_framework",
                        "corner_count": struct['corner_count'],
                        "line_count": struct['line_count'],
                        "grid_score": struct['grid_score']
                    },
                    "confidence": min(0.8, (struct['corner_count'] / 50) + (struct['line_count'] / 20)),
                    "source": "structural_analysis"
                }
                primitives.append(primitive)
        
        # From texture analysis
        if 'texture_analysis' in results:
            texture = results['texture_analysis']
            if texture.get('has_texture', False):
                primitive = {
                    "primitive_type": "texture_pattern",
                    "attributes": {
                        "role": "texture_field",
                        "texture_mean": texture['texture_mean'],
                        "texture_range": texture['texture_range']
                    },
                    "confidence": min(0.7, texture['texture_mean'] / 50),
                    "source": "texture_analysis"
                }
                primitives.append(primitive)
        
        # Sort by confidence
        primitives.sort(key=lambda x: x['confidence'], reverse=True)
        
        return primitives[:25]  # Top 25 primitives
    
    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate overall confidence scores"""
        
        confidence_scores = {}
        
        # Edge analysis confidence
        if 'edge_analysis' in results and 'density_analysis' in results['edge_analysis']:
            edge_density = results['edge_analysis']['density_analysis']['mean_density']
            confidence_scores['edge_confidence'] = min(1.0, edge_density * 10)  # Scale to 0-1
        
        # Contour confidence
        if 'contour_analysis' in results:
            contour_count = results['contour_analysis']['filtered_contours']
            confidence_scores['contour_confidence'] = min(1.0, contour_count / 20)
        
        # Color confidence
        if 'color_regions' in results:
            color_count = results['color_regions']['total_regions']
            confidence_scores['color_confidence'] = min(1.0, color_count / 10)
        
        # Structure confidence
        if 'structural_features' in results:
            struct = results['structural_features']
            if struct['has_structural_features']:
                confidence_scores['structure_confidence'] = min(1.0, (struct['corner_count'] / 30) + (struct['line_count'] / 10))
        
        # Overall confidence
        if confidence_scores:
            overall = np.mean(list(confidence_scores.values()))
        else:
            overall = 0.0
        
        confidence_scores['overall'] = overall
        
        return confidence_scores


# Convenience function for backward compatibility
def extract_advanced_cv_primitives(image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
    """Extract advanced CV primitives"""
    extractor = AdvancedCVExtractor()
    return extractor.extract_advanced_primitives(image_input)
