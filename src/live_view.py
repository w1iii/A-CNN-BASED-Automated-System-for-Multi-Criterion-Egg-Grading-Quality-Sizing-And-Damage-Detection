import cv2
import torch
import yaml
import numpy as np
import time
from collections import defaultdict
import csv
from datetime import datetime

from model import EggGradingCNN
from utils import get_transforms


def load_model(model_path, config_path):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    model = EggGradingCNN(num_classes=cfg["model"]["num_classes"])
    model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
    model.eval()
    return model, cfg


def predict_image(model, img, cfg):
    """Predict damage classification and return both prediction and confidence scores."""
    transform = get_transforms(train=False, img_size=cfg["data"]["img_size"])
    input_tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)
        # Get softmax probabilities for confidence
        probs = torch.softmax(output, dim=1)[0]
        pred = torch.argmax(output, 1).item()
        confidence = float(probs[pred].cpu().numpy())
    return pred, confidence


class ObjectTracker:
    """Simple centroid tracking to prevent duplicate counts across frames."""
    
    def __init__(self, max_distance=50, max_disappeared=30):
        self.objects = {}  # {object_id: (cx, cy, frame_count)}
        self.next_id = 0
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.disappeared = defaultdict(int)
    
    def update(self, detections):
        """
        Update tracker with new detections.
        detections: list of (x1, y1, x2, y2, confidence)
        Returns: list of (object_id, x1, y1, x2, y2, confidence, is_new)
        """
        if len(detections) == 0:
            # Mark all objects as disappeared
            for obj_id in list(self.objects.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return []
        
        # Compute centroids of new detections
        new_centroids = []
        for det in detections:
            x1, y1, x2, y2 = det[:4]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            new_centroids.append((cx, cy, det))
        
        # Match existing objects to new centroids
        used_detections = set()
        output = []
        
        if len(self.objects) == 0:
            # No existing objects, register all new ones
            for cent_idx, (cx, cy, det) in enumerate(new_centroids):
                self.objects[self.next_id] = (cx, cy, 0)
                self.disappeared[self.next_id] = 0
                output.append((self.next_id, det[0], det[1], det[2], det[3], det[4], True))
                self.next_id += 1
                used_detections.add(cent_idx)
        else:
            # Try to match existing objects
            # Use list() to create a copy of keys to avoid "dictionary changed size during iteration"
            for obj_id in list(self.objects.keys()):
                last_cx, last_cy, _ = self.objects[obj_id]
                best_dist = float('inf')
                best_idx = -1
                
                for cent_idx, (cx, cy, det) in enumerate(new_centroids):
                    if cent_idx in used_detections:
                        continue
                    dist = np.sqrt((cx - last_cx)**2 + (cy - last_cy)**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = cent_idx
                
                # If found a match within threshold
                if best_idx != -1 and best_dist < self.max_distance:
                    cx, cy, det = new_centroids[best_idx]
                    self.objects[obj_id] = (cx, cy, self.objects[obj_id][2] + 1)
                    self.disappeared[obj_id] = 0
                    output.append((obj_id, det[0], det[1], det[2], det[3], det[4], False))
                    used_detections.add(best_idx)
                else:
                    self.disappeared[obj_id] += 1
                    if self.disappeared[obj_id] > self.max_disappeared:
                        del self.objects[obj_id]
                        del self.disappeared[obj_id]
            
            # Register unmatched detections
            for cent_idx, (cx, cy, det) in enumerate(new_centroids):
                if cent_idx not in used_detections:
                    self.objects[self.next_id] = (cx, cy, 0)
                    self.disappeared[self.next_id] = 0
                    output.append((self.next_id, det[0], det[1], det[2], det[3], det[4], True))
                    self.next_id += 1
        
        return output


class CameraCalibrator:
    """Camera calibration for converting pixels to real-world measurements."""
    
    def __init__(self, config_path=None):
        self.mm_per_pixel = 1.0  # Default: 1 pixel = 1 mm
        self.calibration_valid = False
        if config_path:
            self.load_calibration(config_path)
    
    def load_calibration(self, config_path):
        """Load calibration from config file."""
        try:
            with open(config_path, 'r') as f:
                cfg = yaml.safe_load(f)
                if 'calibration' in cfg and 'mm_per_pixel' in cfg['calibration']:
                    self.mm_per_pixel = cfg['calibration']['mm_per_pixel']
                    self.calibration_valid = True
        except:
            pass
    
    def set_calibration(self, mm_per_pixel):
        """Set manual calibration value."""
        self.mm_per_pixel = mm_per_pixel
        self.calibration_valid = True
    
    def pixels_to_mm(self, pixels):
        """Convert pixel measurement to millimeters."""
        return pixels * self.mm_per_pixel
    
    def estimate_weight(self, diameter_mm):
        """Estimate egg weight based on diameter using empirical formula."""
        # Empirical egg weight formula: W = 0.05 * D^3 (approximately)
        # D in mm, W in grams (calibrated for chicken eggs)
        if diameter_mm <= 0:
            return -1
        weight_g = 0.05 * (diameter_mm ** 3)
        # Clamp to reasonable range (30-80g for typical eggs)
        weight_g = max(30, min(80, weight_g))
        return round(weight_g, 1)
    
    def categorize_egg(self, diameter_px):
        """Categorize egg by diameter with calibration support."""
        if diameter_px < 0:
            return "N/A", -1
        
        diameter_mm = self.pixels_to_mm(diameter_px)
        weight = self.estimate_weight(diameter_mm)
        
        # Category based on mm measurements
        if diameter_mm < 50:
            return "Small", weight
        elif diameter_mm < 60:
            return "Medium", weight
        else:
            return "Large", weight


class StatisticsLogger:
    """Log egg detection statistics to CSV file."""
    
    def __init__(self, output_path="egg_statistics.csv"):
        self.output_path = output_path
        self.log_file = None
        self.writer = None
        self.initialize_log()
    
    def initialize_log(self):
        """Initialize CSV log file with headers."""
        try:
            self.log_file = open(self.output_path, 'a', newline='')
            self.writer = csv.DictWriter(
                self.log_file,
                fieldnames=[
                    'timestamp', 'egg_id', 'x1', 'y1', 'x2', 'y2',
                    'yolo_confidence', 'class', 'cnn_confidence',
                    'diameter_px', 'diameter_mm', 'size_category', 'weight_g'
                ]
            )
            # Write header if file is new
            self.log_file.seek(0, 2)  # Seek to end
            if self.log_file.tell() == 0:
                self.writer.writeheader()
        except Exception as e:
            print(f"Warning: Could not initialize statistics log: {e}")
    
    def log_detection(self, egg_id, x1, y1, x2, y2, yolo_conf, 
                      egg_class, cnn_conf, diameter_px, diameter_mm, 
                      size_category, weight_g):
        """Log a single egg detection."""
        try:
            if self.writer:
                self.writer.writerow({
                    'timestamp': datetime.now().isoformat(),
                    'egg_id': egg_id,
                    'x1': x1,
                    'y1': y1,
                    'x2': x2,
                    'y2': y2,
                    'yolo_confidence': round(yolo_conf, 4),
                    'class': egg_class,
                    'cnn_confidence': round(cnn_conf, 4),
                    'diameter_px': diameter_px,
                    'diameter_mm': round(diameter_mm, 2),
                    'size_category': size_category,
                    'weight_g': weight_g
                })
                self.log_file.flush()
        except Exception as e:
            print(f"Warning: Could not log detection: {e}")
    
    def close(self):
        """Close the log file."""
        if self.log_file:
            self.log_file.close()


def main():
    """
    Enhanced live egg detection and grading with YOLOv8 and EggGradingCNN.
    
    Features:
    - YOLOv8 object detection with configurable confidence threshold
    - CNN-based damage classification with confidence scores
    - Frame-to-frame object tracking (prevents duplicate counting)
    - Camera calibration support (mm per pixel)
    - Empirical weight estimation
    - CSV logging of all detections
    
    Keyboard Controls:
    - Q: Quit
    - P: Pause/Resume
    - S: Screenshot
    - +/-: Increase/Decrease YOLO confidence threshold
    - C: Toggle CNN confidence filtering
    """
    import argparse
    from ultralytics import YOLO

    parser = argparse.ArgumentParser(description="Enhanced Egg Detection Live View")
    parser.add_argument("--source", type=str, default="0", 
                        help="Camera index (0, 1, ...) or video file path")
    parser.add_argument("--yolo-conf", type=float, default=0.65,
                        help="YOLO confidence threshold (default 0.65)")
    parser.add_argument("--cnn-conf", type=float, default=0.6,
                        help="CNN confidence threshold (default 0.6)")
    parser.add_argument("--no-logging", action="store_true",
                        help="Disable CSV logging")
    args = parser.parse_args()

    yolov8_model_path = "runs/detect/egg_detection/train1/weights/best.pt"

    # Load models
    model_path = "models/egg_grader.pth"
    config_path = "config/config.yaml"
    classifier, cfg = load_model(model_path, config_path)
    class_names = ["Damaged", "Not Damaged"]

    # Try to load YOLO
    try:
        yolomodel = YOLO(yolov8_model_path)
    except Exception as e:
        print(f"Could not load YOLO model: {e}\n" 
              "Download or train an egg detector and update yolov8_model_path.")
        return

    # Try to open video source
    source = args.source
    try:
        source = int(source)
    except ValueError:
        pass
    
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Failed to open video source: {args.source}")
        return
    
    source_name = args.source if args.source.isalpha() or "/" in args.source else f"camera {args.source}"
    print(f"\n{'='*60}")
    print("Enhanced Egg Detection System")
    print(f"{'='*60}")
    print(f"Source: {source_name}")
    print(f"Controls:")
    print(f"  Q: Quit | P: Pause | S: Screenshot")
    print(f"  +/-: Adjust YOLO confidence | C: Toggle CNN filtering")
    print(f"Current settings:")
    print(f"  YOLO confidence: {args.yolo_conf}")
    print(f"  CNN confidence: {args.cnn_conf}")
    print(f"{'='*60}\n")

    # Initialize components
    tracker = ObjectTracker(max_distance=50, max_disappeared=30)
    calibrator = CameraCalibrator(config_path)
    logger = None if args.no_logging else StatisticsLogger("egg_statistics.csv")
    
    # State variables
    paused = False
    pause_frame = None
    yolo_conf = args.yolo_conf
    cnn_conf = args.cnn_conf
    enable_cnn_filtering = True
    
    egg_count = 0
    counted_ids = set()  # Track which egg IDs have been counted
    
    fps = 0
    prev_time = time.time()
    
    last_class_label = ""
    last_diameter = -1
    last_size = ""
    last_weight = -1
    last_cnn_conf = -1
    
    print("Starting detection loop...\n")

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                if isinstance(source, str) and not args.source.isdigit():
                    print("Video ended. Press any key to exit...")
                    cv2.waitKey(0)
                    break
                continue
        else:
            frame = pause_frame.copy() if pause_frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)

        # YOLO inference
        egg_detected = False
        egg_boxes = []
        egg_confs = []
        
        yolores = yolomodel(frame)
        boxes = yolores[0].boxes

        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy() if hasattr(boxes, 'conf') else np.ones(len(xyxy))
            
            # Create detection list (x1, y1, x2, y2, conf)
            raw_detections = []
            for i, box in enumerate(xyxy):
                conf = float(confs[i])
                if conf >= yolo_conf:
                    x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                    raw_detections.append((x1, y1, x2, y2, conf))
            
            # Apply object tracking
            tracked_detections = tracker.update(raw_detections)
            
            if len(tracked_detections) > 0:
                egg_detected = True
                
                # Track size distribution and classifications
                size_counts = {"Small": 0, "Medium": 0, "Large": 0, "N/A": 0}
                total_weight = 0
                egg_classifications = []
                
                for obj_id, x1, y1, x2, y2, yolo_conf_val, is_new in tracked_detections:
                    egg_crop = frame[y1:y2, x1:x2]
                    
                    # Get CNN classification with confidence
                    cnn_pred = 0
                    cnn_conf_val = 0.0
                    egg_class = "Error"
                    
                    if egg_crop is not None and egg_crop.size > 0:
                        rgb_crop = cv2.cvtColor(egg_crop, cv2.COLOR_BGR2RGB)
                        try:
                            cnn_pred, cnn_conf_val = predict_image(classifier, rgb_crop, cfg)
                            
                            # Apply CNN confidence filtering if enabled
                            if enable_cnn_filtering and cnn_conf_val < cnn_conf:
                                egg_class = "Low Confidence"
                            else:
                                egg_class = class_names[cnn_pred] if cnn_pred < len(class_names) else str(cnn_pred)
                        except Exception as e:
                            egg_class = "Error"
                        
                        # Calculate size and weight with calibration
                        diameter_px = max(x2 - x1, y2 - y1)
                        diameter_mm = calibrator.pixels_to_mm(diameter_px)
                        size, weight = calibrator.categorize_egg(diameter_px)
                        
                        size_counts[size] = size_counts.get(size, 0) + 1
                        total_weight += weight if weight > 0 else 0
                        
                        # Log detection to CSV
                        if logger:
                            logger.log_detection(
                                obj_id, x1, y1, x2, y2,
                                yolo_conf_val, egg_class, cnn_conf_val,
                                diameter_px, diameter_mm, size, weight
                            )
                        
                        # Track first egg for display
                        if obj_id not in counted_ids and is_new:
                            counted_ids.add(obj_id)
                            egg_count += 1
                        
                        # Store first egg info for display
                        if obj_id == 0 or (len(tracked_detections) > 0 and 
                                          obj_id == tracked_detections[0][0]):
                            last_diameter = diameter_px
                            last_size = size
                            last_weight = weight
                            last_cnn_conf = cnn_conf_val
                            last_class_label = egg_class
                    else:
                        size_counts["N/A"] += 1
                    
                    egg_boxes.append((x1, y1, x2, y2))
                    egg_confs.append(yolo_conf_val)
                    egg_classifications.append(egg_class)
                
                # Create size summary
                size_summary = ", ".join([f"{v} {k}" for k, v in size_counts.items() if v > 0])
                if not size_summary:
                    size_summary = "N/A"
            else:
                size_counts = {"Small": 0, "Medium": 0, "Large": 0, "N/A": 0}
                total_weight = 0
                size_summary = ""
                egg_classifications = []
        
        # Compute stats
        if egg_detected and len(egg_boxes) > 0:
            all_egg_pixels = []
            for (x1, y1, x2, y2) in egg_boxes:
                h, w, _ = frame.shape
                x1_safe, x2_safe = max(x1, 0), min(x2, w)
                y1_safe, y2_safe = max(y1, 0), min(y2, h)
                if x2_safe > x1_safe and y2_safe > y1_safe:
                    all_egg_pixels.append(frame[y1_safe:y2_safe, x1_safe:x2_safe])
            if all_egg_pixels:
                all_pixels = np.concatenate([crop.flatten() for crop in all_egg_pixels])
                stat_crop = all_pixels.reshape(-1, 1)
            else:
                stat_crop = frame
        else:
            stat_crop = frame
        
        mean = float(np.mean(stat_crop))
        var = float(np.var(stat_crop))

        # FPS calculation
        new_time = time.time()
        elapsed = max(new_time - prev_time, 1e-6)
        fps = 0.9 * fps + 0.1 * (1 / elapsed) if fps > 0 else 1 / elapsed
        prev_time = new_time

        # Display
        disp_frame = frame.copy()
        
        if egg_detected and len(egg_boxes) > 0:
            for idx, (x1, y1, x2, y2) in enumerate(egg_boxes):
                # Color code: green for high confidence, yellow for low CNN confidence
                color = (0, 255, 0) if (not enable_cnn_filtering or last_cnn_conf >= cnn_conf) else (0, 165, 255)
                cv2.rectangle(disp_frame, (x1, y1), (x2, y2), color, 2)
                
                if idx == 0:
                    # YOLO confidence
                    conf_text = f"YOLO: {egg_confs[idx]:.2f}"
                    cv2.putText(disp_frame, conf_text, (x1, y1 - 35),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # CNN confidence
                    cnn_text = f"CNN: {last_cnn_conf:.2f}"
                    cv2.putText(disp_frame, cnn_text, (x1, y1 - 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    
                    # Size and weight
                    if last_size and last_weight > 0:
                        info_text = f"Size: {last_size} | Wt: {last_weight:.1f}g"
                        cv2.putText(disp_frame, info_text, (x1, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Build overlay text
        cnn_filter_status = "CNN Filter ON" if enable_cnn_filtering else "CNN Filter OFF"
        
        if egg_detected and size_summary and size_summary != "N/A":
            overlay_text = (
                f"Count: {egg_count} | In-Frame: {len(egg_boxes)} | "
                f"Size: {size_summary} | Wt: {total_weight:.1f}g | "
                f"Class: {last_class_label} | {cnn_filter_status} | FPS: {fps:.1f}"
            )
        else:
            overlay_text = (
                f"Count: {egg_count} | In-Frame: {len(egg_boxes)} | "
                f"Mean: {mean:.1f} | Var: {var:.1f} | "
                f"{cnn_filter_status} | FPS: {fps:.1f}"
            )
        
        (wtext, htext), _ = cv2.getTextSize(
            overlay_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        frame_h = disp_frame.shape[0]
        cv2.rectangle(disp_frame, (0, frame_h - htext - 18),
                      (min(wtext + 12, disp_frame.shape[1] - 1), frame_h), (0, 0, 0), -1)
        cv2.putText(
            disp_frame, overlay_text,
            (4, frame_h - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show confidence thresholds in top-left
        settings_text = f"YOLO: {yolo_conf:.2f} | CNN: {cnn_conf:.2f}"
        cv2.putText(disp_frame, settings_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Enhanced Egg Detection", disp_frame)
        key = cv2.waitKey(1) & 0xFF
        
        time.sleep(0.03)
        
        if key == ord('q'):
            break
        elif key == ord('p'):
            paused = not paused
            if paused:
                pause_frame = frame.copy()
        elif key == ord('s'):
            fname = f"egg_snapshot_{egg_count}_{int(time.time())}.jpg"
            cv2.imwrite(fname, disp_frame)
            print(f"Saved screenshot to {fname}")
        elif key == ord('+') or key == ord('='):
            yolo_conf = min(0.99, yolo_conf + 0.05)
            print(f"YOLO confidence: {yolo_conf:.2f}")
        elif key == ord('-'):
            yolo_conf = max(0.1, yolo_conf - 0.05)
            print(f"YOLO confidence: {yolo_conf:.2f}")
        elif key == ord('c'):
            enable_cnn_filtering = not enable_cnn_filtering
            status = "ON" if enable_cnn_filtering else "OFF"
            print(f"CNN confidence filtering: {status}")

    cap.release()
    cv2.destroyAllWindows()
    
    if logger:
        logger.close()
        print(f"\nDetection statistics saved to egg_statistics.csv")
    
    print(f"Session complete. Total eggs counted: {egg_count}")


if __name__ == "__main__":
    main()
