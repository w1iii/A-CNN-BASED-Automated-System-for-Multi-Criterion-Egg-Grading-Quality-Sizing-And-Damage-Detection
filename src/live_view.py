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
    from ultralytics import YOLO  # pip install ultralytics

    yolov8_model_path = "yolo_egg.pt"  # <- Place your custom YOLO model here
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

    cap = cv2.VideoCapture(0)  # See CAMERA_INDEX note above
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    print("Controls: Q-quit, P-pause, S-screenshot\nShowing YOLO-detected eggs with live grading.")

    last_egg_present_time = 0
    last_egg_absent_time = time.time()
    egg_present = False
    paused = False
    egg_count = 0
    last_class_label = ""
    last_diameter = -1
    last_size = ""
    last_weight = -1
    fps = 0
    prev_time = time.time()
    pause_frame = None

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
                continue
        else:
            frame = pause_frame.copy() if pause_frame is not None else np.zeros((480, 640, 3), dtype=np.uint8)

        # Compute mean/var (over the ROI if egg found, else whole frame)
        egg_detected = False
        egg_box = None
        # YOLO inference (set conf=0.4 if too many false positives)
        yolores = yolomodel(frame)
        boxes = yolores[0].boxes

        if boxes is not None and len(boxes) > 0:
            # Find box with largest area (since only one egg expected)
            xyxy = boxes.xyxy.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy() if hasattr(boxes,'conf') else np.ones(len(boxes))
            max_area = 0
            egg_box = None
            for box in xyxy:
                x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
                area = (x2 - x1) * (y2 - y1)
                if area > max_area:
                    max_area = area
                    egg_box = (x1, y1, x2, y2)
            if egg_box is not None:
                egg_detected = True

        nowtime = time.time()
        if egg_detected:
            last_egg_present_time = nowtime
            # If egg was previously absent, count new egg
            if not egg_present and nowtime - last_egg_absent_time > 2.0:
                egg_count += 1
                egg_present = True
                # Crop egg region for classification
                x1, y1, x2, y2 = egg_box
                egg_crop = frame[y1:y2, x1:x2]
                if egg_crop is not None and egg_crop.size > 0:
                    rgb_crop = cv2.cvtColor(egg_crop, cv2.COLOR_BGR2RGB)
                    try:
                        pred = predict_image(classifier, rgb_crop, cfg)
                        last_class_label = class_names[pred] if pred < len(class_names) else str(pred)
                    except Exception as e:
                        last_class_label = f"Error: {e}"
                    # Diameter as max of width/height
                    diameter_px = max(x2-x1, y2-y1)
                    last_diameter = diameter_px  # For real mm: multiply by your calibration
                    last_size, last_weight = categorize_egg(diameter_px)
        else:
            if egg_present and nowtime - last_egg_present_time > 2.0:
                egg_present = False
                last_egg_absent_time = nowtime

        # Stats: mean/var over egg crop if present, else whole frame
        if egg_detected and egg_box is not None:
            x1, y1, x2, y2 = map(int, egg_box)
            # Bounds-check to prevent slicing errors
            h, w, _ = frame.shape
            x1, x2 = max(x1, 0), min(x2, w)
            y1, y2 = max(y1, 0), min(y2, h)
            if x2 > x1 and y2 > y1:
                stat_crop = frame[y1:y2, x1:x2]
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

        # Draw
        disp_frame = frame.copy()
        if egg_detected and egg_box is not None:
            x1, y1, x2, y2 = map(int, egg_box)
            cv2.rectangle(disp_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        overlay_text = (
            f"Eggs: {egg_count} | Mean: {mean:.1f} | Var: {var:.1f} | "
            f"Diameter(px): {last_diameter if last_diameter > 0 else 'N/A'} | "
            f"Size: {last_size} | Weight(g): {last_weight} | Class: {last_class_label} | "
            f"FPS: {fps:.1f}"
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
