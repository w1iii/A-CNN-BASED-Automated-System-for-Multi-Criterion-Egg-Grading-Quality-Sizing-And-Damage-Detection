import os
import time
from pathlib import Path
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
import cv2

from app.models import Prediction, DetectionBox
from app.ml.yolo_inference import YOLOPredictor
from app.config import settings


class PredictionService:
    def __init__(self, predictor: Optional[YOLOPredictor] = None):
        self.predictor = predictor or YOLOPredictor()
    
    def create_prediction(
        self,
        db: Session,
        user_id: int,
        file_name: str,
        file_path: str,
        file_type: str
    ) -> Prediction:
        prediction = Prediction(
            user_id=user_id,
            file_name=file_name,
            file_type=file_type,
            file_path=file_path,
            status="processing"
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction
    
    def run_prediction(
        self,
        db: Session,
        prediction_id: int,
        confidence: float,
        save_annotated: bool
    ) -> Prediction:
        start_time = time.time()
        
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            raise ValueError("Prediction not found")
        
        self.predictor.confidence = confidence
        
        try:
            if prediction.file_type == "image":
                result = self.predictor.predict_image(prediction.file_path)
            else:
                result = {"detections": [], "total": 0, "damaged": 0, "not_damaged": 0}
            
            annotated_path = None
            if save_annotated and result["detections"]:
                img = cv2.imread(prediction.file_path)
                if img is not None:
                    annotated = self.predictor.draw_boxes(img, result["detections"])
                    base_name = Path(prediction.file_path).stem
                    ext = Path(prediction.file_path).suffix
                    annotated_path = str(Path(prediction.file_path).parent / f"annotated_{base_name}{ext}")
                    cv2.imwrite(annotated_path, annotated)
            
            for det in result["detections"]:
                box = DetectionBox(
                    prediction_id=prediction.id,
                    class_name=det["class"],
                    confidence=det["confidence"],
                    x1=det["bbox"][0],
                    y1=det["bbox"][1],
                    x2=det["bbox"][2],
                    y2=det["bbox"][3],
                    annotated=save_annotated
                )
                db.add(box)
            
            prediction.status = "completed"
            prediction.result_json = result
            prediction.annotated_path = annotated_path
            prediction.total_detections = result["total"]
            prediction.damaged_count = result["damaged"]
            prediction.not_damaged_count = result["not_damaged"]
            prediction.processing_time_ms = int((time.time() - start_time) * 1000)
            prediction.completed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(prediction)
            
        except Exception as e:
            prediction.status = "failed"
            prediction.error_message = str(e)
            db.commit()
            raise
        
        return prediction
    
    def get_predictions(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> list[Prediction]:
        return db.query(Prediction).filter(
            Prediction.user_id == user_id
        ).order_by(
            Prediction.created_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_prediction_detail(
        self,
        db: Session,
        prediction_id: int,
        user_id: int
    ) -> Optional[Prediction]:
        return db.query(Prediction).filter(
            Prediction.id == prediction_id,
            Prediction.user_id == user_id
        ).first()
    
    def delete_prediction(
        self,
        db: Session,
        prediction_id: int,
        user_id: int
    ) -> bool:
        prediction = self.get_prediction_detail(db, prediction_id, user_id)
        if not prediction:
            return False
        
        try:
            if os.path.exists(prediction.file_path):
                os.remove(prediction.file_path)
            if prediction.annotated_path and os.path.exists(prediction.annotated_path):
                os.remove(prediction.annotated_path)
        except Exception:
            pass
        
        db.delete(prediction)
        db.commit()
        return True


prediction_service = PredictionService()