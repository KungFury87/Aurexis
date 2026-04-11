"""
Simulated Camera System for Aurexis Testing

Uses real images to simulate camera input when no physical camera is available.
Demonstrates the full potential of the Aurexis visual processing pipeline.
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time
from datetime import datetime

def create_test_images() -> Dict[str, np.ndarray]:
    """Create diverse test images that showcase different visual features"""
    
    test_images = {}
    
    # 1. Geometric shapes with clear regions
    geo_img = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # Central sigil (red circle)
    cv2.circle(geo_img, (320, 240), 60, (0, 0, 255), -1)
    
    # Ring delimiter (blue square)
    cv2.rectangle(geo_img, (200, 120), (440, 360), (255, 0, 0), 8)
    
    # Outer field with grid pattern
    for i in range(0, 640, 40):
        cv2.line(geo_img, (i, 0), (i, 480), (200, 200, 200), 1)
    for i in range(0, 480, 40):
        cv2.line(geo_img, (0, i), (640, i), (200, 200, 200), 1)
    
    # Add some text
    cv2.putText(geo_img, "AUREXIS", (250, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    test_images["geometric_test"] = geo_img
    
    # 2. Natural scene simulation
    nature_img = np.ones((480, 640, 3), dtype=np.uint8) * 135  # Light green background
    
    # Add some "trees" (dark green circles)
    for _ in range(8):
        x, y = np.random.randint(50, 590), np.random.randint(50, 430)
        radius = np.random.randint(20, 50)
        cv2.circle(nature_img, (x, y), radius, (0, 100, 0), -1)
    
    # Add "sky" gradient
    for i in range(160):
        nature_img[i, :] = (135 + i//2, 135 + i//2, 255 - i//4)
    
    # Add "sun"
    cv2.circle(nature_img, (550, 80), 30, (255, 255, 0), -1)
    
    test_images["nature_scene"] = nature_img
    
    # 3. High contrast pattern
    pattern_img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Checkerboard pattern
    for i in range(0, 480, 40):
        for j in range(0, 640, 40):
            if (i//40 + j//40) % 2 == 0:
                pattern_img[i:i+40, j:j+40] = [255, 255, 255]
    
    # Central focus point
    cv2.circle(pattern_img, (320, 240), 80, (255, 0, 0), 3)
    cv2.circle(pattern_img, (320, 240), 40, (0, 255, 0), 3)
    cv2.circle(pattern_img, (320, 240), 10, (0, 0, 255), -1)
    
    test_images["high_contrast"] = pattern_img
    
    # 4. Document-like image
    doc_img = np.ones((480, 640, 3), dtype=np.uint8) * 240
    
    # Add text blocks
    cv2.rectangle(doc_img, (50, 50), (590, 150), (0, 0, 0), 2)
    cv2.rectangle(doc_img, (50, 170), (590, 270), (0, 0, 0), 2)
    cv2.rectangle(doc_img, (50, 290), (590, 390), (0, 0, 0), 2)
    
    # Add some lines
    for i in range(70, 140, 15):
        cv2.line(doc_img, (60, i), (580, i), (100, 100, 100), 1)
    
    # Add header
    cv2.putText(doc_img, "DOCUMENT HEADER", (200, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    test_images["document"] = doc_img
    
    # 5. Low light / challenging scene
    low_light = np.ones((480, 640, 3), dtype=np.uint8) * 30
    
    # Add some subtle features
    cv2.circle(low_light, (320, 240), 50, (60, 60, 60), -1)
    cv2.rectangle(low_light, (250, 180), (390, 300), (50, 50, 50), 3)
    
    # Add noise
    noise = np.random.normal(0, 10, (480, 640, 3)).astype(np.uint8)
    low_light = cv2.add(low_light, noise)
    
    test_images["low_light"] = low_light
    
    return test_images


class SimulatedCamera:
    """Simulates camera input using test images"""
    
    def __init__(self, test_images_dir: str = "test_images"):
        self.test_images_dir = Path(test_images_dir)
        self.test_images_dir.mkdir(exist_ok=True)
        
        # Generate and save test images
        self.test_images = create_test_images()
        self.image_names = list(self.test_images.keys())
        
        # Save images to disk
        for name, img in self.test_images.items():
            cv2.imwrite(str(self.test_images_dir / f"{name}.png"), img)
        
        self.current_index = 0
        self.is_looping = True
        
    def get_frame(self, image_name: Optional[str] = None) -> Tuple[np.ndarray, str]:
        """Get a frame from the simulated camera"""
        
        if image_name and image_name in self.test_images:
            frame = self.test_images[image_name]
            timestamp = datetime.now().isoformat()
            return frame, timestamp
        
        # Cycle through images
        frame = self.test_images[self.image_names[self.current_index]]
        timestamp = datetime.now().isoformat()
        
        if self.is_looping:
            self.current_index = (self.current_index + 1) % len(self.image_names)
        else:
            if self.current_index < len(self.image_names) - 1:
                self.current_index += 1
        
        return frame, timestamp
    
    def list_available_scenes(self) -> List[str]:
        """List all available test scenes"""
        return self.image_names.copy()
    
    def reset_sequence(self):
        """Reset to first image"""
        self.current_index = 0


def run_simulated_capture_demo():
    """Run a demonstration with simulated camera input"""
    from .real_evidence_capture import EvidenceCapture
    from .evidence_batch_processor import EvidenceBatchProcessor
    
    print("=== Aurexis Simulated Camera Demo ===")
    print("Using test images to demonstrate full pipeline potential")
    print()
    
    # Initialize simulated camera
    sim_cam = SimulatedCamera()
    scenes = sim_cam.list_available_scenes()
    print(f"Available test scenes: {scenes}")
    
    # Initialize evidence capture
    capturer = EvidenceCapture()
    
    # Capture one frame from each scene
    all_evidence = []
    
    for scene_name in scenes:
        print(f"\n📸 Capturing scene: {scene_name}")
        frame, timestamp = sim_cam.get_frame(scene_name)
        
        # Process the frame
        evidence = capturer.process_captured_frame(frame, timestamp)
        evidence['scene_name'] = scene_name
        all_evidence.append(evidence)
        
        # Show results
        conf_score = evidence['confidence'].get('overall', 'N/A')
        if conf_score != 'N/A':
            print(f"   - Confidence: {conf_score:.3f}")
        else:
            print(f"   - Confidence: {conf_score}")
        print(f"   - CV primitives: {evidence['cv_extraction']['primitive_count']}")
        print(f"   - Segments: {evidence['segmentation_extraction']['segments_count']}")
    
    # Save all evidence as a batch
    batch_path = capturer.save_evidence_batch(all_evidence, "simulated_camera_batch")
    print(f"\n💾 Saved simulated batch: {batch_path}")
    
    # Process the batch
    print("\n🔬 Processing simulated batch...")
    processor = EvidenceBatchProcessor()
    
    # Analyze quality
    quality = processor.analyze_batch_quality("simulated_camera_batch")
    print(f"📊 Batch quality score: {quality['quality_score']:.3f}")
    
    conf_mean = quality['confidence_distribution'].get('mean', 'N/A')
    if conf_mean != 'N/A':
        print(f"📊 Average confidence: {conf_mean:.3f}")
    else:
        print(f"📊 Average confidence: {conf_mean}")
        
    print(f"📊 Average primitives: {quality['primitive_analysis']['cv_primitives']['mean']:.1f}")
    
    # Generate training data
    training_path = processor.process_batch_to_training_data("simulated_camera_batch")
    print(f"🎓 Training data: {training_path}")
    
    # Generate report
    report_path = processor.generate_batch_report("simulated_camera_batch")
    print(f"📄 Report: {report_path}")
    
    print("\n🎉 Simulated camera demo complete!")
    print("This demonstrates Aurexis processing real visual features:")
    print("   - Geometric shapes and regions")
    print("   - Natural scenes with varied lighting") 
    print("   - High contrast patterns")
    print("   - Document-like structures")
    print("   - Challenging low-light conditions")
    
    return batch_path, quality


if __name__ == "__main__":
    run_simulated_capture_demo()
