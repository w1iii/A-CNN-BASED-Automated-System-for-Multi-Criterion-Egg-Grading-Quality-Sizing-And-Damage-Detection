#!/usr/bin/env python3
"""
YOLO Confidence Threshold Finder

This script helps you find the optimal YOLO confidence threshold for your camera setup.
It starts at a low threshold and gradually increases it, showing you when detections disappear.

Usage:
    python3 find_yolo_threshold.py --source 0
    
    Move the egg around in front of the camera.
    Press '+' to increase confidence (make stricter).
    Press '-' to decrease confidence (make lenient).
    Watch when the box disappears and report back!
"""

import cv2
import torch
import yaml
import numpy as np
import argparse
from ultralytics import YOLO


def find_threshold(camera_index=0):
    """Interactive YOLO threshold finder."""
    
    # Load YOLO
    print("\nLoading YOLO model...")
    yolov8_model_path = "runs/detect/egg_detection/train1/weights/best.pt"
    try:
        yolomodel = YOLO(yolov8_model_path)
    except Exception as e:
        print(f"Error loading YOLO: {e}")
        return
    
    # Open camera
    source = camera_index
    try:
        source = int(source)
    except ValueError:
        pass
    
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Failed to open camera {source}")
        return
    
    print(f"\n{'='*70}")
    print("YOLO CONFIDENCE THRESHOLD FINDER")
    print(f"{'='*70}")
    print("""
INSTRUCTIONS:
1. Hold the egg in front of camera
2. Move it around (different distances, rotations, positions)
3. Press '+' to INCREASE confidence (watch when box disappears!)
4. Press '-' to DECREASE confidence
5. When you find the critical threshold, tell me:
   "Box disappears at 0.XX confidence"

This tells us the optimal threshold for your camera setup.

KEYBOARD CONTROLS:
    + : Increase YOLO confidence (stricter)
    - : Decrease YOLO confidence (more lenient)
    R : Reset to 0.30
    S : Save optimal threshold to config
    Q : Quit
""")
    print(f"{'='*70}\n")
    
    yolo_conf = 0.30
    detections_list = []
    fps = 0
    prev_time = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # YOLO inference
        yolores = yolomodel(frame)
        boxes = yolores[0].boxes
        
        detections = []
        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy() if hasattr(boxes, 'conf') else np.ones(len(xyxy))
            
            for i, box in enumerate(xyxy):
                conf = float(confs[i])
                if conf >= yolo_conf:
                    x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                    detections.append((x1, y1, x2, y2, conf))
        
        # FPS
        import time
        current_time = time.time()
        if prev_time:
            elapsed = current_time - prev_time
            fps = 0.9 * fps + 0.1 * (1 / max(elapsed, 0.001)) if fps > 0 else 1 / max(elapsed, 0.001)
        prev_time = current_time
        
        # Draw
        display_frame = frame.copy()
        
        if detections:
            for x1, y1, x2, y2, conf in detections:
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display_frame, f"Conf: {conf:.3f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Show detection count
            text = f"DETECTED: {len(detections)} egg(s)"
            cv2.putText(display_frame, text, (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            # Show no detection
            text = "NO DETECTION"
            cv2.putText(display_frame, text, (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Show threshold
        threshold_text = f"YOLO Confidence Threshold: {yolo_conf:.2f}"
        cv2.putText(display_frame, threshold_text, (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Show controls
        controls = "+/-: Adjust | R: Reset | S: Save | Q: Quit"
        cv2.putText(display_frame, controls, (10, display_frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Show FPS
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(display_frame, fps_text, (display_frame.shape[1] - 150, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        
        cv2.imshow("YOLO Threshold Finder", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('+') or key == ord('='):
            yolo_conf = min(0.99, yolo_conf + 0.01)
            print(f"Confidence: {yolo_conf:.2f}")
        elif key == ord('-'):
            yolo_conf = max(0.01, yolo_conf - 0.01)
            print(f"Confidence: {yolo_conf:.2f}")
        elif key == ord('r'):
            yolo_conf = 0.30
            print("Reset to 0.30")
        elif key == ord('s'):
            # Save to config
            try:
                config_path = "config/config.yaml"
                with open(config_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                
                cfg['detection']['yolo_confidence'] = round(yolo_conf, 2)
                
                with open(config_path, 'w') as f:
                    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
                
                print(f"\n✓ Saved YOLO confidence {yolo_conf:.2f} to config.yaml")
                break
            except Exception as e:
                print(f"Error saving: {e}")
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find optimal YOLO confidence threshold")
    parser.add_argument("--source", type=str, default="0",
                        help="Camera index (0, 1, ...) or video file path")
    args = parser.parse_args()
    
    try:
        source = int(args.source)
    except ValueError:
        source = args.source
    
    find_threshold(source)
