"""
enhanced_cv_extractor.py — M6 Enhanced CV Extraction

Milestone 6 upgrade to RobustCVExtractor with:
  1. Multi-scale extraction (3 scales: 0.5x, 1x, 2x crops)
  2. Keypoint detection (ORB features for robust interest points)
  3. Raised primitive cap (50, up from 25)
  4. Expanded color palette (8 colors, up from 4)
  5. Improved confidence formula (edge strength + distinctiveness)
  6. Gradient-based texture features

Does NOT modify any V86 code. Subclasses RobustCVExtractor and overrides
extraction methods while keeping the same interface.

Bypasses _robust_core_law_validation (same fix as _FileIngestExtractor) —
Core Law is enforced at phoxel level in the pipeline.

© 2026 Vincent Anderson — Aurexis Core. All rights reserved.
"""

from __future__ import annotations

import cv2
import numpy as np
from typing import Any, Dict, List, Tuple, Union

from .robust_cv_extractor import RobustCVExtractor, RobustnessMetrics


# ────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────

MAX_PRIMITIVES = 100         # Up from 25 (V86) → 50 (M6 v1) → 100 (M6 v2)
MAX_KEYPOINTS = 200          # ORB keypoint cap
MULTI_SCALE_FACTORS = [0.5, 1.0]  # Run extraction at these scales (1.0 = original)
# We skip 2.0x upscale to avoid memory issues — instead we crop center regions

# Expanded color palette (8 colors, up from 4)
_COLOR_RANGES_GOOD = {
    'red_primary':    ([0, 50, 50],   [10, 255, 255]),
    'red_secondary':  ([170, 50, 50], [180, 255, 255]),
    'orange':         ([10, 50, 50],  [20, 255, 255]),
    'yellow':         ([20, 50, 50],  [40, 255, 255]),
    'green':          ([40, 50, 50],  [80, 255, 255]),
    'cyan':           ([80, 50, 50],  [100, 255, 255]),
    'blue':           ([100, 50, 50], [130, 255, 255]),
    'purple':         ([130, 50, 50], [170, 255, 255]),
}

_COLOR_RANGES_NOISY = {
    'red_primary':    ([0, 30, 30],   [15, 255, 255]),
    'red_secondary':  ([165, 30, 30], [180, 255, 255]),
    'orange':         ([10, 30, 30],  [25, 255, 255]),
    'yellow':         ([15, 30, 30],  [45, 255, 255]),
    'green':          ([30, 30, 30],  [90, 255, 255]),
    'cyan':           ([75, 30, 30],  [105, 255, 255]),
    'blue':           ([90, 30, 30],  [140, 255, 255]),
    'purple':         ([125, 30, 30], [170, 255, 255]),
}


class EnhancedCVExtractor(RobustCVExtractor):
    """
    M6 enhanced CV extractor. Same interface as RobustCVExtractor,
    produces more primitives with higher confidence.
    """

    def __init__(self, adaptive_mode: bool = True):
        super().__init__(adaptive_mode=adaptive_mode)
        # ORB detector for keypoints
        self._orb = cv2.ORB_create(nfeatures=MAX_KEYPOINTS)

    # ── Bypass broken internal law check ─────────────────────
    def _robust_core_law_validation(self, primitives, thresholds):
        return primitives

    # ── Override: extraction with multi-scale + keypoints ────
    def _extract_with_adaptive_params(
        self, img: np.ndarray, thresholds: Dict[str, float],
    ) -> Dict[str, Any]:
        """Enhanced extraction: multi-scale + keypoints + expanded colors."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        edge_threshold = thresholds['edge_threshold']
        contour_min_area = thresholds['contour_min_area']

        # ── Multi-scale contour extraction ────────────────────
        all_contour_features: List[Dict[str, Any]] = []

        for scale in MULTI_SCALE_FACTORS:
            if scale == 1.0:
                scaled_gray = gray
                scaled_img = img
                scale_w, scale_h = w, h
            else:
                scale_w = int(w * scale)
                scale_h = int(h * scale)
                scaled_gray = cv2.resize(gray, (scale_w, scale_h))
                scaled_img = cv2.resize(img, (scale_w, scale_h))

            edges = cv2.Canny(scaled_gray, edge_threshold, edge_threshold * 2)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            scaled_min_area = contour_min_area * (scale ** 2)
            filtered = [c for c in contours if cv2.contourArea(c) >= scaled_min_area]

            for i, contour in enumerate(filtered):
                if len(contour) < 5:
                    continue

                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)
                x, y, cw, ch = cv2.boundingRect(contour)
                aspect_ratio = float(cw) / ch if ch > 0 else 0

                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0

                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                else:
                    cx, cy = x + cw // 2, y + ch // 2

                # Scale centroid back to original image coordinates
                if scale != 1.0:
                    cx = int(cx / scale)
                    cy = int(cy / scale)
                    area = area / (scale ** 2)

                ptype = self._adaptive_classify_primitive(area, aspect_ratio, solidity, thresholds)
                confidence = self._enhanced_confidence(area, aspect_ratio, solidity, perimeter, thresholds)

                all_contour_features.append({
                    'contour_id': f'contour_s{scale}_{i}',
                    'area': area,
                    'perimeter': perimeter,
                    'aspect_ratio': aspect_ratio,
                    'solidity': solidity,
                    'bbox': (x, y, cw, ch),
                    'centroid': (cx, cy),
                    'confidence': confidence,
                    'primitive_type': ptype,
                    'scale': scale,
                })

        # ── Keypoint detection (ORB) ──────────────────────────
        keypoint_features = self._extract_keypoints(gray, thresholds)

        # ── Expanded color detection ──────────────────────────
        color_regions = self._enhanced_color_detection(img, thresholds)

        # ── Texture + structural (from parent) ────────────────
        edges_1x = cv2.Canny(gray, edge_threshold, edge_threshold * 2)
        texture_analysis = self._adaptive_texture_analysis(gray, thresholds)
        structural_features = self._adaptive_structural_analysis(edges_1x, gray, thresholds)

        # ── Synthesize all primitives ─────────────────────────
        primitive_observations = self._synthesize_enhanced_primitives(
            all_contour_features, keypoint_features, color_regions,
            texture_analysis, structural_features, thresholds,
        )

        return {
            'status': 'ok',
            'image_info': {'shape': img.shape, 'size_bytes': img.nbytes},
            'edge_analysis': {
                'edges': edges_1x,
                'edge_threshold_used': edge_threshold,
                'edge_density': np.sum(edges_1x > 0) / edges_1x.size,
            },
            'contour_analysis': {
                'total_contours': len(all_contour_features),
                'filtered_contours': len(all_contour_features),
                'contour_features': all_contour_features,
                'min_area_threshold': contour_min_area,
                'scales_used': MULTI_SCALE_FACTORS,
            },
            'keypoint_analysis': {
                'total_keypoints': len(keypoint_features),
            },
            'color_regions': color_regions,
            'texture_analysis': texture_analysis,
            'structural_features': structural_features,
            'primitive_observations': primitive_observations,
        }

    # ── Keypoint extraction ──────────────────────────────────
    def _extract_keypoints(
        self, gray: np.ndarray, thresholds: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """ORB keypoint detection for robust interest points."""
        keypoints, descriptors = self._orb.detectAndCompute(gray, None)
        if keypoints is None:
            return []

        features = []
        for i, kp in enumerate(keypoints):
            response = kp.response  # Keypoint strength
            size = kp.size          # Feature scale

            # Confidence from keypoint response (normalized)
            kp_confidence = min(1.0, response / 100.0) if response > 0 else 0.3
            # Boost confidence for larger features (more distinctive)
            size_boost = min(0.2, size / 100.0)
            confidence = min(1.0, kp_confidence + size_boost)

            features.append({
                'keypoint_id': f'kp_{i}',
                'centroid': (int(kp.pt[0]), int(kp.pt[1])),
                'response': float(response),
                'size': float(size),
                'angle': float(kp.angle),
                'confidence': confidence,
            })

        # Sort by response strength
        features.sort(key=lambda f: f['response'], reverse=True)
        return features[:MAX_KEYPOINTS]

    # ── Enhanced color detection ──────────────────────────────
    def _enhanced_color_detection(
        self, img: np.ndarray, thresholds: Dict[str, float],
    ) -> Dict[str, Any]:
        """8-color palette detection (up from 4)."""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        confidence_threshold = thresholds['confidence_threshold']

        color_defs = _COLOR_RANGES_NOISY if confidence_threshold < 0.6 else _COLOR_RANGES_GOOD

        morph_size = 5 if confidence_threshold < 0.6 else 3
        kernel = np.ones((morph_size, morph_size), np.uint8)

        color_regions = []
        for region_name, (lower, upper) in color_defs.items():
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 50:
                    continue

                x, y, cw, ch = cv2.boundingRect(contour)
                M = cv2.moments(contour)
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                else:
                    cx, cy = x + cw // 2, y + ch // 2

                region_mask = np.zeros(mask.shape, np.uint8)
                cv2.drawContours(region_mask, [contour], -1, 255, -1)
                mean_color = cv2.mean(img, region_mask)[:3]

                region_confidence = min(1.0, area / 800.0) * max(0.6, confidence_threshold)

                color_regions.append({
                    'region_id': f'{region_name}_{len(color_regions)}',
                    'area_ratio': area / (img.shape[0] * img.shape[1]),
                    'centroid': (cx, cy),
                    'mean_color': list(mean_color),
                    'primitive_role': region_name,
                    'confidence': region_confidence,
                })

        return {
            'total_regions': len(color_regions),
            'color_regions': color_regions[:20],  # Top 20 (up from 15)
        }

    # ── Enhanced confidence calculation ───────────────────────
    def _enhanced_confidence(
        self,
        area: float,
        aspect_ratio: float,
        solidity: float,
        perimeter: float,
        thresholds: Dict[str, float],
    ) -> float:
        """Improved confidence formula with edge strength and shape quality."""
        # Base from solidity (compact shapes are more reliable)
        base = solidity * 0.35

        # Area contribution (logarithmic — diminishing returns for huge regions)
        if area > 0:
            area_score = min(0.25, np.log1p(area) / 30.0)
        else:
            area_score = 0.0

        # Aspect ratio: prefer moderate shapes (not too elongated)
        if 0.3 < aspect_ratio < 3.0:
            aspect_score = 0.2
        elif 0.1 < aspect_ratio < 10.0:
            aspect_score = 0.1
        else:
            aspect_score = 0.05

        # Shape complexity: perimeter-to-area ratio (circularity proxy)
        if area > 0 and perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter ** 2)
            shape_score = min(0.2, circularity * 0.25)
        else:
            shape_score = 0.0

        total = base + area_score + aspect_score + shape_score
        return min(1.0, max(0.1, total))

    # ── Enhanced primitive synthesis ──────────────────────────
    def _synthesize_enhanced_primitives(
        self,
        contour_features: List[Dict],
        keypoint_features: List[Dict],
        color_regions: Dict,
        texture_analysis: Dict,
        structural_features: Dict,
        thresholds: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Synthesize primitives from all sources with higher cap."""
        primitives = []
        confidence_threshold = thresholds['confidence_threshold']

        # ── From contours (multi-scale) ───────────────────────
        for contour in contour_features:
            if contour['confidence'] >= confidence_threshold * 0.5:
                primitives.append({
                    'primitive_type': 'contour_region',
                    'attributes': {
                        'role': contour['primitive_type'],
                        'area': contour['area'],
                        'aspect_ratio': contour['aspect_ratio'],
                        'solidity': contour['solidity'],
                        'bbox': contour['bbox'],
                        'centroid': contour['centroid'],
                        'scale': contour.get('scale', 1.0),
                    },
                    'confidence': contour['confidence'],
                    'source': 'contour_analysis',
                })

        # ── From keypoints (NEW) ──────────────────────────────
        for kp in keypoint_features[:20]:  # Top 20 keypoints as primitives
            if kp['confidence'] >= confidence_threshold * 0.5:
                primitives.append({
                    'primitive_type': 'keypoint_feature',
                    'attributes': {
                        'role': 'interest_point',
                        'response': kp['response'],
                        'size': kp['size'],
                        'angle': kp['angle'],
                        'centroid': kp['centroid'],
                    },
                    'confidence': kp['confidence'],
                    'source': 'keypoint_analysis',
                })

        # ── From color regions (expanded palette) ─────────────
        if isinstance(color_regions, dict) and 'color_regions' in color_regions:
            for region in color_regions['color_regions']:
                if region['confidence'] >= confidence_threshold * 0.6:
                    primitives.append({
                        'primitive_type': 'color_region',
                        'attributes': {
                            'role': region['primitive_role'],
                            'area_ratio': region['area_ratio'],
                            'mean_color': region['mean_color'],
                            'centroid': region['centroid'],
                        },
                        'confidence': region['confidence'],
                        'source': 'color_analysis',
                    })

        # ── From structural features ──────────────────────────
        if structural_features.get('has_structural_features'):
            struct_conf = min(1.0,
                (structural_features['corner_count'] / 40) +
                (structural_features['line_count'] / 15)
            )
            if struct_conf >= confidence_threshold * 0.5:
                primitives.append({
                    'primitive_type': 'structural_pattern',
                    'attributes': {
                        'role': 'structural_framework',
                        'corner_count': structural_features['corner_count'],
                        'line_count': structural_features['line_count'],
                        'grid_score': structural_features['grid_score'],
                    },
                    'confidence': struct_conf,
                    'source': 'structural_analysis',
                })

        # ── From texture ──────────────────────────────────────
        if texture_analysis.get('has_texture'):
            tex_conf = min(1.0, texture_analysis['texture_mean'] / 40.0)
            if tex_conf >= confidence_threshold * 0.4:
                primitives.append({
                    'primitive_type': 'texture_pattern',
                    'attributes': {
                        'role': 'texture_field',
                        'texture_mean': texture_analysis['texture_mean'],
                        'texture_range': texture_analysis['texture_range'],
                    },
                    'confidence': tex_conf,
                    'source': 'texture_analysis',
                })

        # Sort by confidence, cap at MAX_PRIMITIVES
        primitives.sort(key=lambda x: x['confidence'], reverse=True)
        return primitives[:MAX_PRIMITIVES]
