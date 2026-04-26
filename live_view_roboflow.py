import argparse
import csv
import time
from collections import defaultdict
from datetime import datetime

import cv2
import numpy as np
import time
from collections import defaultdict
import csv
from datetime import datetime
import argparse
from roboflow import Roboflow
import threading
import queue


class AsyncInference:
    def __init__(self, model):
        self.model = model
        self.input_queue = queue.Queue(maxsize=1)  # Only keep latest frame
        self.output_queue = queue.Queue(maxsize=1)
        self.running = True
        self.thread = threading.Thread(target=self._inference_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def _inference_worker(self):
        while self.running:
            try:
                frame, conf_threshold = self.input_queue.get(timeout=1)
                if frame is None:
                    break
                result = self.model.predict(frame, confidence=conf_threshold, overlap=30).json()
                # Clear old results and add new one
                if not self.output_queue.empty():
                    try:
                        self.output_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.output_queue.put(result)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Inference error: {e}")
                if not self.output_queue.empty():
                    try:
                        self.output_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.output_queue.put({"predictions": []})
    
    def predict(self, frame, conf_threshold):
        # Non-blocking: try to add frame to queue, replace if full
        try:
            self.input_queue.put_nowait((frame, conf_threshold))
        except queue.Full:
            try:
                self.input_queue.get_nowait()
                self.input_queue.put_nowait((frame, conf_threshold))
            except queue.Empty:
                pass
    
    def get_result(self):
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop(self):
        self.running = False
        self.input_queue.put((None, 0))
        self.thread.join(timeout=2)
class ObjectTracker:
    """Simple centroid tracking to prevent duplicate counts across frames."""
    
    def __init__(self, max_distance=50, max_disappeared=30):
        self.objects = {}
        self.next_id = 0
        self.max_distance = max_distance
        self.max_disappeared = max_disappeared
        self.disappeared = defaultdict(int)

    def update(self, detections):
        if len(detections) == 0:
            for obj_id in list(self.objects.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    del self.objects[obj_id]
                    del self.disappeared[obj_id]
            return []

        new_centroids = []
        for det in detections:
            x1, y1, x2, y2 = det[:4]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            new_centroids.append((cx, cy, det))

        used_detections = set()
        output = []

        if len(self.objects) == 0:
            for cent_idx, (cx, cy, det) in enumerate(new_centroids):
                self.objects[self.next_id] = (cx, cy, 0)
                self.disappeared[self.next_id] = 0
                output.append(
                    (self.next_id, det[0], det[1], det[2], det[3], det[4], True)
                )
                self.next_id += 1
                used_detections.add(cent_idx)
        else:
            for obj_id in list(self.objects.keys()):
                last_cx, last_cy, _ = self.objects[obj_id]
                best_dist = float("inf")
                best_idx = -1

                for cent_idx, (cx, cy, det) in enumerate(new_centroids):
                    if cent_idx in used_detections:
                        continue
                    dist = np.sqrt((cx - last_cx) ** 2 + (cy - last_cy) ** 2)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = cent_idx

                if best_idx != -1 and best_dist < self.max_distance:
                    cx, cy, det = new_centroids[best_idx]
                    self.objects[obj_id] = (cx, cy, self.objects[obj_id][2] + 1)
                    self.disappeared[obj_id] = 0
                    output.append(
                        (obj_id, det[0], det[1], det[2], det[3], det[4], False)
                    )
                    used_detections.add(best_idx)
                else:
                    self.disappeared[obj_id] += 1
                    if self.disappeared[obj_id] > self.max_disappeared:
                        del self.objects[obj_id]
                        del self.disappeared[obj_id]

            for cent_idx, (cx, cy, det) in enumerate(new_centroids):
                if cent_idx not in used_detections:
                    self.objects[self.next_id] = (cx, cy, 0)
                    self.disappeared[self.next_id] = 0
                    output.append(
                        (self.next_id, det[0], det[1], det[2], det[3], det[4], True)
                    )
                    self.next_id += 1

        return output


class CameraCalibrator:
    def __init__(self):
        self.mm_per_pixel = 1.0

    def pixels_to_mm(self, pixels):
        return pixels * self.mm_per_pixel

    def estimate_weight(self, diameter_mm):
        if diameter_mm <= 0:
            return -1
        weight_g = 0.05 * (diameter_mm**3)
        weight_g = max(30, min(80, weight_g))
        return round(weight_g, 1)

    def categorize_egg(self, diameter_px):
        if diameter_px < 0:
            return "N/A", -1
        diameter_mm = self.pixels_to_mm(diameter_px)
        weight = self.estimate_weight(diameter_mm)
        if diameter_mm < 50:
            return "Small", weight
        elif diameter_mm < 60:
            return "Medium", weight
        else:
            return "Large", weight


class StatisticsLogger:
    def __init__(self, output_path="egg_statistics_roboflow.csv"):
        self.output_path = output_path
        self.log_file = None
        self.writer = None
        self.initialize_log()

    def initialize_log(self):
        try:
            self.log_file = open(self.output_path, "a", newline="")
            self.writer = csv.DictWriter(
                self.log_file,
                fieldnames=[
                    "timestamp",
                    "egg_id",
                    "x1",
                    "y1",
                    "x2",
                    "y2",
                    "confidence",
                    "class",
                    "diameter_px",
                    "diameter_mm",
                    "size_category",
                    "weight_g",
                ],
            )
            self.log_file.seek(0, 2)
            if self.log_file.tell() == 0:
                self.writer.writeheader()
        except Exception as e:
            print(f"Warning: Could not initialize statistics log: {e}")

    def log_detection(
        self,
        egg_id,
        x1,
        y1,
        x2,
        y2,
        conf,
        egg_class,
        diameter_px,
        diameter_mm,
        size_category,
        weight_g,
    ):
        try:
            if self.writer:
                self.writer.writerow(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "egg_id": egg_id,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "confidence": round(conf, 4),
                        "class": egg_class,
                        "diameter_px": diameter_px,
                        "diameter_mm": round(diameter_mm, 2),
                        "size_category": size_category,
                        "weight_g": weight_g,
                    }
                )
                self.log_file.flush()
        except Exception as e:
            print(f"Warning: Could not log detection: {e}")

    def close(self):
        if self.log_file:
            self.log_file.close()


def main():
    parser = argparse.ArgumentParser(description="Egg Detection Live View (Roboflow)")
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Camera index (0, 1, ...) or video file path",
    )
    parser.add_argument(
        "--conf", type=float, default=40, help="Confidence threshold (default 40)"
    )
    parser.add_argument("--api-key", type=str, required=True, help="Roboflow API key")
    parser.add_argument("--no-logging", action="store_true", help="Disable CSV logging")
    parser.add_argument("--frame-skip", type=int, default=2,
                        help="Process every Nth frame to improve FPS (default 2)")
    parser.add_argument("--resize", type=float, default=0.5,
                        help="Resize factor for frames (default 0.5 for better speed)")
    args = parser.parse_args()

    print("Initializing Roboflow...")
    try:
        rf = Roboflow(api_key=args.api_key)
        project = rf.workspace().project("boysmithv2-rohz2")
        model = project.version(1).model
        async_model = AsyncInference(model)
        print("Roboflow model loaded with async inference!")
    except Exception as e:
        print(f"Error initializing Roboflow: {e}")
        return

    source = args.source
    try:
        source = int(source)
    except ValueError:
        pass

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Failed to open video source: {args.source}")
        return

    print(f"\n{'=' * 60}")
    print("Egg Detection Live View (Roboflow)")
    print(f"{'=' * 60}")
    print("Controls: Q=Quit, P=Pause, S=Screenshot, +/-=Confidence")
    print(f"Confidence threshold: {args.conf}")
    print(f"Frame skip: {args.frame_skip}, Resize: {args.resize}")
    print(f"{'=' * 60}\n")

    tracker = ObjectTracker()
    calibrator = CameraCalibrator()
    logger = None if args.no_logging else StatisticsLogger()

    paused = False
    pause_frame = None
    conf_threshold = args.conf
    egg_count = 0
    counted_ids = set()
    fps = 0
    prev_time = time.time()
    frame_count = 0
    last_processed_frame = None

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                if isinstance(source, str) and "/" in source:
                    print("Video ended.")
                    break
                continue
        else:
            frame = (
                pause_frame.copy()
                if pause_frame is not None
                else np.zeros((480, 640, 3), dtype=np.uint8)
            )

        frame_count += 1
        process_frame = frame_count % args.frame_skip == 0

        if process_frame and not paused:
            # Resize frame for faster inference
            if args.resize != 1.0:
                h, w = frame.shape[:2]
                new_w, new_h = int(w * args.resize), int(h * args.resize)
                resized_frame = cv2.resize(frame, (new_w, new_h))
            else:
                resized_frame = frame

            # Submit frame for async inference
            async_model.predict(resized_frame, conf_threshold)

        # Get latest inference result (non-blocking)
        result = async_model.get_result()
        if result is None:
            result = last_processed_frame if last_processed_frame else {"predictions": []}
        else:
            last_processed_frame = result

        egg_detected = False
        egg_boxes = []
        egg_confs = []
        egg_classes = []

        raw_detections = []
        for pred in result.get("predictions", []):
            # Scale coordinates back if frame was resized
            scale_x = 1.0 / args.resize if args.resize != 1.0 else 1.0
            scale_y = 1.0 / args.resize if args.resize != 1.0 else 1.0

            x1 = int((pred["x"] - pred["width"] / 2) * scale_x)
            y1 = int((pred["y"] - pred["height"] / 2) * scale_y)
            x2 = int((pred["x"] + pred["width"] / 2) * scale_x)
            y2 = int((pred["y"] + pred["height"] / 2) * scale_y)
            conf = pred["confidence"]
            cls = pred["class"]

            raw_detections.append((x1, y1, x2, y2, conf))
            egg_boxes.append((x1, y1, x2, y2))
            egg_confs.append(conf)
            egg_classes.append(cls)

        tracked = tracker.update(raw_detections)

        if len(tracked) > 0:
            egg_detected = True
            for obj_id, x1, y1, x2, y2, conf, is_new in tracked:
                if obj_id not in counted_ids and is_new:
                    counted_ids.add(obj_id)
                    egg_count += 1

                cls_label = "egg"  # Roboflow model may have different class names

                if logger:
                    diameter_px = max(x2 - x1, y2 - y1)
                    diameter_mm = calibrator.pixels_to_mm(diameter_px)
                    size, weight = calibrator.categorize_egg(diameter_px)
                    logger.log_detection(
                        obj_id,
                        x1,
                        y1,
                        x2,
                        y2,
                        conf,
                        cls_label,
                        diameter_px,
                        diameter_mm,
                        size,
                        weight,
                    )

        new_time = time.time()
        elapsed = max(new_time - prev_time, 1e-6)
        fps = 0.9 * fps + 0.1 * (1 / elapsed) if fps > 0 else 1 / elapsed
        prev_time = new_time

        disp_frame = frame.copy()

        if egg_detected:
            for i, (x1, y1, x2, y2) in enumerate(egg_boxes):
                color = (0, 255, 0)  # Green for detected eggs
                cv2.rectangle(disp_frame, (x1, y1), (x2, y2), color, 2)
                label = f"Egg {egg_confs[i]:.2f}"
                cv2.putText(
                    disp_frame,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                )

        info = f"Count: {egg_count} | In-Frame: {len(egg_boxes)} | Conf: {conf_threshold} | FPS: {fps:.1f} | Proc: {'Yes' if process_frame else 'No'}"
        cv2.putText(
            disp_frame,
            info,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

        cv2.imshow("Egg Detection (Roboflow)", disp_frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("p"):
            paused = not paused
            if paused:
                pause_frame = frame.copy()
        elif key == ord("s"):
            fname = f"egg_snapshot_{egg_count}_{int(time.time())}.jpg"
            cv2.imwrite(fname, disp_frame)
            print(f"Saved: {fname}")
        elif key in [ord("+"), ord("=")]:
            conf_threshold = min(99, conf_threshold + 5)
            print(f"Confidence: {conf_threshold}")
        elif key == ord("-"):
            conf_threshold = max(1, conf_threshold - 5)
            print(f"Confidence: {conf_threshold}")

    cap.release()
    cv2.destroyAllWindows()
    
    # Stop async inference
    async_model.stop()

    if logger:
        logger.close()
        print("Statistics saved to egg_statistics_roboflow.csv")

    print(f"Session complete. Total eggs counted: {egg_count}")


if __name__ == "__main__":
    main()
