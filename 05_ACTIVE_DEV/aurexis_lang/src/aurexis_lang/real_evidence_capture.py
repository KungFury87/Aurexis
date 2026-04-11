"""
Real Observed Evidence Capture System

This module provides the bridge between real camera input and the Aurexis visual language pipeline.
It captures real-world visual data and processes it through the existing CV extraction and analysis pipeline.
"""

import cv2
import numpy as np
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import threading
import queue

from .cv_primitive_extractor import extract_cv_primitives, cv_image_to_parser_bundle
from .advanced_cv_extractor import AdvancedCVExtractor, extract_advanced_cv_primitives
from .segmentation_pipeline import coarse_partition, segments_to_primitives, image_to_segmented_parser_bundle
from .confidence_parser import summarize_confidence, parse_with_confidence
from .perception_dataset_prep import load_rows, rank_row_usefulness, build_dataset_manifest, write_dataset_manifest
from .gate3_evidence_loop import stamp_gate3_surface
from .gate3_comparison_audit import build_real_capture_reference_surface


class EvidenceCapture:
    """Real-time evidence capture from camera sources"""
    
    def __init__(self, output_dir: str = "evidence_batches", use_advanced_cv: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.capture_queue = queue.Queue()
        self.is_capturing = False
        self.capture_thread = None
        self.use_advanced_cv = use_advanced_cv
        
        if self.use_advanced_cv:
            self.advanced_extractor = AdvancedCVExtractor()
        
    def list_available_cameras(self) -> List[int]:
        """List all available camera devices"""
        available_cameras = []
        for i in range(10):  # Check first 10 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
        return available_cameras
    
    def capture_single_frame(self, camera_id: int = 0) -> Optional[np.ndarray]:
        """Capture a single frame from specified camera"""
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print(f"Camera {camera_id} not available")
            return None
            
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return frame
        else:
            print("Failed to capture frame")
            return None
    
    def start_continuous_capture(self, camera_id: int = 0, fps_target: int = 5):
        """Start continuous capture in background thread"""
        if self.is_capturing:
            print("Already capturing")
            return
            
        self.is_capturing = True
        self.capture_thread = threading.Thread(
            target=self._capture_loop, 
            args=(camera_id, fps_target)
        )
        self.capture_thread.start()
        print(f"Started capture from camera {camera_id} at {fps_target} FPS")
    
    def stop_continuous_capture(self):
        """Stop continuous capture"""
        self.is_capturing = False
        if self.capture_thread:
            self.capture_thread.join()
        print("Stopped capture")
    
    def _capture_loop(self, camera_id: int, fps_target: int):
        """Background capture loop"""
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print(f"Camera {camera_id} not available")
            return
            
        frame_interval = 1.0 / fps_target
        last_capture = time.time()
        
        while self.is_capturing:
            ret, frame = cap.read()
            if ret and time.time() - last_capture >= frame_interval:
                timestamp = datetime.now().isoformat()
                self.capture_queue.put((frame, timestamp))
                last_capture = time.time()
                
        cap.release()
    
    def process_captured_frame(self, frame: np.ndarray, timestamp: str) -> Dict[str, Any]:
        """Process a captured frame through the full pipeline"""
        
        # Convert to different color spaces for analysis
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        if self.use_advanced_cv:
            # Use advanced CV extraction
            advanced_result = self.advanced_extractor.extract_advanced_primitives(frame)
            
            # Extract primitives using advanced methods
            cv_primitives = advanced_result
            cv_bundle = advanced_result
            
            # Segmentation-based extraction
            segments = coarse_partition(frame)
            segmented_primitives = segments_to_primitives(segments)
            segmented_bundle = image_to_segmented_parser_bundle(frame)
            
            # Calculate confidence scores
            confidence_summary = advanced_result.get('confidence', {'overall': 0.5})
            
            # Create evidence record with advanced data
            evidence = {
                'timestamp': timestamp,
                'frame_info': {
                    'shape': frame.shape,
                    'dtype': str(frame.dtype),
                    'size_bytes': frame.nbytes
                },
                'advanced_extraction': advanced_result,
                'cv_extraction': {
                    'primitives': advanced_result.get('primitive_observations', []),
                    'bundle': advanced_result,
                    'primitive_count': len(advanced_result.get('primitive_observations', []))
                },
                'segmentation_extraction': {
                    'segments_count': len(segments) if isinstance(segments, list) else 1,
                    'primitives': segmented_primitives,
                    'bundle': segmented_bundle
                },
                'confidence': confidence_summary,
                'processing_timestamp': datetime.now().isoformat(),
                'extraction_method': 'advanced_cv',
                'evidence_tier': 'real-capture',
                'source_class': 'real_capture'
            }
        else:
            # Use basic CV extraction
            cv_primitives = extract_cv_primitives(frame)
            cv_bundle = cv_image_to_parser_bundle(frame)
            
            # Segmentation-based extraction
            segments = coarse_partition(frame)
            segmented_primitives = segments_to_primitives(segments)
            segmented_bundle = image_to_segmented_parser_bundle(frame)
            
            # Calculate confidence scores
            confidence_summary = summarize_confidence({
                'cv_primitives': cv_primitives,
                'segmented_primitives': segmented_primitives,
                'cv_bundle': cv_bundle,
                'segmented_bundle': segmented_bundle
            })
            
            # Create evidence record
            evidence = {
                'timestamp': timestamp,
                'frame_info': {
                    'shape': frame.shape,
                    'dtype': str(frame.dtype),
                    'size_bytes': frame.nbytes
                },
                'cv_extraction': {
                    'primitives': cv_primitives,
                    'bundle': cv_bundle,
                    'primitive_count': len(cv_primitives.get('primitive_observations', [])) if isinstance(cv_primitives, dict) else 1
                },
                'segmentation_extraction': {
                    'segments_count': len(segments) if isinstance(segments, list) else 1,
                    'primitives': segmented_primitives,
                    'bundle': segmented_bundle
                },
                'confidence': confidence_summary,
                'processing_timestamp': datetime.now().isoformat(),
                'extraction_method': 'basic_cv',
                'evidence_tier': 'real-capture',
                'source_class': 'real_capture'
            }
        
        return evidence
    
    def save_evidence_batch(self, evidence_list: List[Dict[str, Any]], batch_name: str = None) -> str:
        """Save a batch of evidence records"""
        if batch_name is None:
            batch_name = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        batch_dir = self.output_dir / batch_name
        batch_dir.mkdir(exist_ok=True)
        
        # Save evidence data
        evidence_file = batch_dir / "evidence.json"
        with open(evidence_file, 'w') as f:
            json.dump(evidence_list, f, indent=2, default=str)
        
        # Save summary statistics
        summary = self._generate_batch_summary(evidence_list)
        summary_file = batch_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"Saved evidence batch: {batch_name} with {len(evidence_list)} records")
        return str(batch_dir)
    
    def _generate_batch_summary(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for evidence batch"""
        if not evidence_list:
            return {}
        
        # Extract key metrics
        cv_primitive_counts = []
        segment_counts = []
        confidence_scores = []
        
        for evidence in evidence_list:
            cv_primitive_counts.append(evidence['cv_extraction']['primitive_count'])
            segment_counts.append(evidence['segmentation_extraction']['segments_count'])
            
            if 'confidence' in evidence and 'overall' in evidence['confidence']:
                confidence_scores.append(evidence['confidence']['overall'])
        
        summary = {
            'batch_size': len(evidence_list),
            'time_range': {
                'start': evidence_list[0]['timestamp'],
                'end': evidence_list[-1]['timestamp']
            },
            'cv_primitives': {
                'total': sum(cv_primitive_counts),
                'average': np.mean(cv_primitive_counts),
                'min': min(cv_primitive_counts),
                'max': max(cv_primitive_counts)
            },
            'segments': {
                'total': sum(segment_counts),
                'average': np.mean(segment_counts),
                'min': min(segment_counts),
                'max': max(segment_counts)
            },
            'confidence': {
                'average': np.mean(confidence_scores) if confidence_scores else 0,
                'min': min(confidence_scores) if confidence_scores else 0,
                'max': max(confidence_scores) if confidence_scores else 0
            },
            'output_honesty_explicit': True,
        }
        summary = stamp_gate3_surface(summary, source_class='real_capture', evidence_tier='real-capture')
        summary['gate_3_real_capture_reference_surface'] = build_real_capture_reference_surface(summary)
        return summary
    
    def capture_and_process_batch(self, camera_id: int = 0, duration_seconds: int = 30, fps_target: int = 5) -> str:
        """Capture and process a batch of evidence"""
        print(f"Starting {duration_seconds} second capture from camera {camera_id}")
        
        evidence_list = []
        start_time = time.time()
        
        self.start_continuous_capture(camera_id, fps_target)
        
        try:
            while time.time() - start_time < duration_seconds:
                try:
                    frame, timestamp = self.capture_queue.get(timeout=1.0)
                    evidence = self.process_captured_frame(frame, timestamp)
                    evidence_list.append(evidence)
                    print(f"Processed frame {len(evidence_list)}: {evidence['confidence'].get('overall', 'N/A')}")
                except queue.Empty:
                    continue
        finally:
            self.stop_continuous_capture()
        
        if evidence_list:
            return self.save_evidence_batch(evidence_list)
        else:
            print("No evidence captured")
            return ""


def quick_capture_demo():
    """Quick demonstration of evidence capture"""
    capturer = EvidenceCapture()
    
    # List available cameras
    cameras = capturer.list_available_cameras()
    print(f"Available cameras: {cameras}")
    
    if not cameras:
        print("No cameras available")
        return
    
    # Capture single frame test
    frame = capturer.capture_single_frame(cameras[0])
    if frame is not None:
        print(f"Captured frame: {frame.shape}")
        
        # Process it
        timestamp = datetime.now().isoformat()
        evidence = capturer.process_captured_frame(frame, timestamp)
        print(f"Processed evidence with {evidence['cv_extraction']['primitive_count']} primitives")
        
        # Save as small batch
        batch_path = capturer.save_evidence_batch([evidence], "demo_batch")
        print(f"Saved demo batch: {batch_path}")


if __name__ == "__main__":
    quick_capture_demo()
