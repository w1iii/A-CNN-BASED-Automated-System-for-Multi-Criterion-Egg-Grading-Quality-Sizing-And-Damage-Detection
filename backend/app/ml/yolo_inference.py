import os
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import cv2

from app.config import settings


class YOLOPredictor:
    def __init__(self, model_path: Optional[str] = None, confidence: float = 0.75):
        self.model_path = model_path or settings.MODEL_PATH
        self.confidence = confidence
        self.class_names = ["not_damaged", "damaged"]
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
        return self._model

    def load_model(self) -> bool:
        if not os.path.exists(self.model_path):
            print(f"Warning: Model file not found at {self.model_path}")
            return False
        try:
            _ = self.model
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def predict_image(self, image_path: str) -> Dict[str, Any]:
        results = self.model(image_path, conf=self.confidence)
        return self._parse_results(results[0])

    def predict_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        results = self.model(frame, conf=self.confidence)
        return self._parse_results(results[0])

    def predict_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self.predict_frame(frame)

    def _parse_results(self, result) -> Dict[str, Any]:
        detections = []
        boxes = result.boxes

        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy()

            for i, box in enumerate(xyxy):
                detections.append({
                    "class": self.class_names[int(clss[i])],
                    "confidence": float(confs[i]),
                    "bbox": [int(x) for x in box]
                })

        return {
            "detections": detections,
            "total": len(detections),
            "damaged": sum(1 for d in detections if d["class"] == "damaged"),
            "not_damaged": sum(1 for d in detections if d["class"] == "not_damaged")
        }

    def draw_boxes(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        img = image.copy()

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cls = det["class"]
            conf = det["confidence"]

            color = (0, 255, 0) if cls == "not_damaged" else (0, 0, 255)
            label = f"{cls} {conf:.2f}"

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, label, (x1, y1 - 10),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return img