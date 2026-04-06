import cv2
import torch
import yaml

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
    transform = get_transforms(train=False, img_size=cfg["data"]["img_size"])
    input_tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        output = model(input_tensor)
        pred = torch.argmax(output, 1).item()
    return pred


def main():
    """
    Live egg detection and grading with YOLOv8 and EggGradingCNN.
    Requirements:
    - pip install ultralytics opencv-python torch
    - Place your YOLOv8 egg detection model at './yolo_egg.pt', or change yolov8_model_path
    - Optional: calibrate mm-per-pixel for real-world diameter/weight
    """
    import time
    import numpy as np
    import argparse
    from ultralytics import YOLO  # pip install ultralytics

    parser = argparse.ArgumentParser(description="Egg Detection Live View")
    parser.add_argument("--source", type=str, default="0", 
                        help="Camera index (0, 1, ...) or video file path")
    args = parser.parse_args()

    # yolov8_model_path = "yolo_egg.pt"  # Use this for custom trained model
    yolov8_model_path = "runs/detect/egg_detection/train1/weights/best.pt"
    # CAMERA_INDEX = 0  # Default. Change to 1,2,... for other cameras

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

    # Try to open video source (camera index or video file)
    source = args.source
    try:
        source = int(source)  # Try as camera index
    except ValueError:
        pass  # Keep as string (video file path)
    
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Failed to open video source: {args.source}")
        return
    
    source_name = args.source if args.source.isalpha() or "/" in args.source else f"camera {args.source}"
    print(f"Controls: Q-quit, P-pause, S-screenshot | Source: {source_name}")

    last_egg_present_time = 0
    last_egg_absent_time = time.time()
    egg_present = False
    egg_count = 0
    first_egg_counted = False  # Track if first egg has been properly counted
    paused = False
    last_class_label = ""
    last_diameter = -1
    last_size = ""
    last_weight = -1
    size_summary = ""
    total_weight = 0
    fps = 0
    prev_time = time.time()
    pause_frame = None
    yolo_conf = 0.5  # Minimum confidence for valid detection

    # Helper for egg sizing (adjust as appropriate for your grading)
    def categorize_egg(diameter):
        # Placeholder: thresholds in pixels (CALIBRATE for mm!)
        # e.g., Small <40, Medium <55, Large >= 55
        if diameter < 0:
            return "N/A", -1
        if diameter < 40:
            return "Small", 45
        elif diameter < 55:
            return "Medium", 55
        else:
            return "Large", 65

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                # For video files: exit when video ends
                if isinstance(source, str) and not args.source.isdigit():
                    print("Video ended. Press any key to exit...")
                    cv2.waitKey(0)
                    break
                continue
        else:
            frame = pause_frame.copy() if pause_frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)

        # Compute mean/var (over the ROI if eggs found, else whole frame)
        egg_detected = False
        egg_boxes = []  # Store all detected eggs
        egg_confs = []
        # YOLO inference
        yolores = yolomodel(frame)
        boxes = yolores[0].boxes

        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy() if hasattr(boxes,'conf') else np.ones(len(xyxy))
            for i, box in enumerate(xyxy):
                conf = float(confs[i])
                if conf < yolo_conf:
                    continue
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                egg_boxes.append((x1, y1, x2, y2))
                egg_confs.append(conf)
            if len(egg_boxes) > 0:
                egg_detected = True

        nowtime = time.time()
        current_egg_count = len(egg_boxes)
        
        # Track size distribution for all eggs in frame
        size_counts = {"Small": 0, "Medium": 0, "Large": 0, "N/A": 0}
        total_weight = 0
        
        if egg_detected:
            if not egg_present:  # Eggs just appeared (was absent before)
                egg_count += current_egg_count
                first_egg_counted = True
            egg_present = True
            last_egg_present_time = nowtime
            
            # Classify each detected egg
            egg_classifications = []
            for idx, (x1, y1, x2, y2) in enumerate(egg_boxes):
                egg_crop = frame[y1:y2, x1:x2]
                if egg_crop is not None and egg_crop.size > 0:
                    rgb_crop = cv2.cvtColor(egg_crop, cv2.COLOR_BGR2RGB)
                    try:
                        pred = predict_image(classifier, rgb_crop, cfg)
                        egg_class = class_names[pred] if pred < len(class_names) else str(pred)
                    except Exception as e:
                        egg_class = f"Error"
                    egg_classifications.append(egg_class)
                    
                    # Calculate size and weight for each egg
                    diameter_px = max(x2-x1, y2-y1)
                    size, weight = categorize_egg(diameter_px)
                    size_counts[size] = size_counts.get(size, 0) + 1
                    total_weight += weight if weight > 0 else 0
                    
                    if idx == 0:
                        last_diameter = diameter_px
                        last_size, last_weight = size, weight
                        last_class_label = egg_class
                else:
                    egg_classifications.append("N/A")
                    size_counts["N/A"] += 1
            
            # Create summary string
            if size_counts["Small"] > 0 or size_counts["Medium"] > 0 or size_counts["Large"] > 0:
                size_summary = ", ".join([f"{v} {k}" for k, v in size_counts.items() if v > 0])
            else:
                size_summary = "N/A"
            
            last_class_label = ", ".join(egg_classifications) if egg_classifications else "N/A"
        else:  # No eggs detected
            if egg_present:  # Eggs just disappeared
                egg_present = False
                size_summary = ""
                total_weight = 0

        # Stats: mean/var over all detected eggs or whole frame
        if egg_detected and len(egg_boxes) > 0:
            # Combine all egg regions
            all_egg_pixels = []
            for (x1, y1, x2, y2) in egg_boxes:
                h, w, _ = frame.shape
                x1, x2 = max(x1, 0), min(x2, w)
                y1, y2 = max(y1, 0), min(y2, h)
                if x2 > x1 and y2 > y1:
                    all_egg_pixels.append(frame[y1:y2, x1:x2])
            if all_egg_pixels:
                # Flatten each crop and compute stats
                all_pixels = np.concatenate([crop.flatten() for crop in all_egg_pixels])
                stat_crop = all_pixels.reshape(-1, 1)
            else:
                stat_crop = frame
        else:
            stat_crop = frame
        mean = float(np.mean(stat_crop))
        var = float(np.var(stat_crop))

        # FPS
        new_time = time.time()
        elapsed = max(new_time - prev_time, 1e-6)
        fps = 0.9 * fps + 0.1 * (1 / elapsed) if fps > 0 else 1 / elapsed
        prev_time = new_time

        # Create display frame and draw
        disp_frame = frame.copy()
        
        # Draw first egg info on frame
        if egg_detected and len(egg_boxes) > 0:
            for idx, (x1, y1, x2, y2) in enumerate(egg_boxes):
                cv2.rectangle(disp_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Show details on first egg
                if idx == 0:
                    conf_text = f"Conf: {egg_confs[idx]:.2f}"
                    cv2.putText(disp_frame, conf_text, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    # Show size/weight for first egg
                    if last_size and last_weight > 0:
                        info_text = f"Size: {last_size} | Wt: {last_weight}g"
                        cv2.putText(disp_frame, info_text, (x1, y1 - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Build overlay text
        if size_summary:
            overlay_text = (
                f"Count: {egg_count} | In-Frame: {len(egg_boxes)} | "
                f"Size: {size_summary} | Wt: {total_weight}g | "
                f"Class: {last_class_label} | FPS: {fps:.1f}"
            )
        else:
            overlay_text = (
                f"Count: {egg_count} | In-Frame: {len(egg_boxes)} | "
                f"Mean: {mean:.1f} | Var: {var:.1f} | "
                f"Class: {last_class_label} | FPS: {fps:.1f}"
            )
        (wtext, htext), _ = cv2.getTextSize(
            overlay_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        frame_h = disp_frame.shape[0]
        # Make sure rectangle fits even on small frames
        cv2.rectangle(disp_frame, (0, frame_h - htext - 18),
                      (min(wtext + 12, disp_frame.shape[1]-1), frame_h), (0, 0, 0), -1)
        cv2.putText(
            disp_frame, overlay_text,
            (4, frame_h - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Controls
        cv2.imshow("YOLO Egg Grading Live", disp_frame)
        key = cv2.waitKey(1) & 0xFF
        
        # Control frame rate (adjust 0.03 for ~30 FPS, 0.1 for ~10 FPS)
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

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
