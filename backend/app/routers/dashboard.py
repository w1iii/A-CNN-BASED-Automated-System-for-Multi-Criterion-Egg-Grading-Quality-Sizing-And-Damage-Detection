from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.database import get_db
from app.models import User, Prediction
from app.schemas import DashboardStats, HealthResponse
from app.security import get_current_user
from app.ml.yolo_inference import YOLOPredictor
from app.config import settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total = db.query(Prediction).filter(Prediction.user_id == current_user.id).count()
    total_images = db.query(Prediction).filter(
        Prediction.user_id == current_user.id,
        Prediction.file_type == "image"
    ).count()
    total_videos = db.query(Prediction).filter(
        Prediction.user_id == current_user.id,
        Prediction.file_type == "video"
    ).count()
    total_detections = db.query(func.sum(Prediction.total_detections)).filter(
        Prediction.user_id == current_user.id
    ).scalar() or 0
    
    damaged = db.query(func.sum(Prediction.damaged_count)).filter(
        Prediction.user_id == current_user.id
    ).scalar() or 0
    not_damaged = db.query(func.sum(Prediction.not_damaged_count)).filter(
        Prediction.user_id == current_user.id
    ).scalar() or 0
    
    damaged_percentage = (damaged / total_detections * 100) if total_detections > 0 else 0
    
    avg_time = db.query(func.avg(Prediction.processing_time_ms)).filter(
        Prediction.user_id == current_user.id,
        Prediction.status == "completed"
    ).scalar() or 0
    
    recent = db.query(Prediction).filter(
        Prediction.user_id == current_user.id
    ).order_by(
        Prediction.created_at.desc()
    ).limit(5).all()
    
    return DashboardStats(
        total_predictions=total,
        total_images=total_images,
        total_videos=total_videos,
        total_detections=total_detections,
        damaged_percentage=round(damaged_percentage, 1),
        avg_processing_time_ms=round(avg_time, 1),
        recent_predictions=recent
    )


@router.get("/health", response_model=HealthResponse)
def health_check():
    model_loaded = False
    try:
        predictor = YOLOPredictor()
        model_loaded = predictor.load_model()
    except Exception:
        pass
    
    database_connected = False
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        database_connected = True
    except Exception:
        pass
    
    return HealthResponse(
        status="healthy" if (model_loaded and database_connected) else "degraded",
        model_loaded=model_loaded,
        database_connected=database_connected
    )