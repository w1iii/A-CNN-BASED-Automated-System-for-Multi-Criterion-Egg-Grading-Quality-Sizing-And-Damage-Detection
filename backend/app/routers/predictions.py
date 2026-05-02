from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Prediction
from app.schemas import PredictionResponse, PredictionDetail
from app.security import get_current_user
from app.services import file_service, prediction_service
from app.ml.yolo_inference import YOLOPredictor

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/upload", response_model=PredictionDetail)
async def upload_file(
    file: UploadFile = File(...),
    confidence_threshold: float = Query(0.75, ge=0.1, le=0.99),
    save_annotated: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file_service.is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: jpg, jpeg, png, webp, bmp, mp4, avi, mov, mkv"
        )

    file_path, file_type = file_service.save_file_sync(file)
    
    prediction = prediction_service.create_prediction(
        db, current_user.id, file.filename, file_path, file_type
    )
    
    try:
        predictor = YOLOPredictor(
            confidence=confidence_threshold,
            mm_per_pixel=current_user.mm_per_pixel
        )
        pred_service = prediction_service.__class__(predictor)
        prediction = pred_service.run_prediction(
            db, prediction.id, confidence_threshold, save_annotated
        )
    except Exception as e:
        prediction.status = "failed"
        prediction.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )
    
    return prediction


@router.get("", response_model=List[PredictionResponse])
def get_predictions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return prediction_service.get_predictions(db, current_user.id, skip, limit)


@router.get("/{prediction_id}", response_model=PredictionDetail)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prediction = prediction_service.get_prediction_detail(
        db, prediction_id, current_user.id
    )
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    return prediction


@router.delete("/{prediction_id}")
def delete_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = prediction_service.delete_prediction(
        db, prediction_id, current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    return {"message": "Prediction deleted"}


@router.get("/{prediction_id}/download")
def download_annotated(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prediction = prediction_service.get_prediction_detail(
        db, prediction_id, current_user.id
    )
    if not prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found"
        )
    if not prediction.annotated_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Annotated file not found"
        )
    return FileResponse(
        prediction.annotated_path,
        media_type="image/jpeg",
        filename=f"annotated_{prediction.file_name}"
    )