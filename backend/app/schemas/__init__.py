from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class DetectionBoxResponse(BaseModel):
    id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    annotated: bool

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    status: str
    total_detections: int
    damaged_count: int
    not_damaged_count: int
    processing_time_ms: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class PredictionDetail(PredictionResponse):
    result_json: Optional[dict]
    annotated_path: Optional[str]
    detection_boxes: List[DetectionBoxResponse] = []

    class Config:
        from_attributes = True


class PredictionCreate(BaseModel):
    confidence_threshold: float = 0.75
    save_annotated: bool = True


class DashboardStats(BaseModel):
    total_predictions: int
    total_images: int
    total_videos: int
    total_detections: int
    damaged_percentage: float
    avg_processing_time_ms: float
    recent_predictions: List[PredictionResponse]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database_connected: bool