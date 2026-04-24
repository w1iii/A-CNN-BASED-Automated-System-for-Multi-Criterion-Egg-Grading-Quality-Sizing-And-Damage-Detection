# Egg-CV Prediction System - MVP Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React + Vite)                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│  │  Upload   │  │ Dashboard │  │  History  │  │  Results  │              │
│  │   Page    │  │   Page    │  │   Page    │  │   Display │              │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘              │
│        │              │              │              │                      │
│        └──────────────┼──────────────┼──────────────┘                      │
│                       ▼                                                   │
│              ┌──────────────┐                                             │
│              │   API Client │                                             │
│              │  (Axios/WS)   │                                             │
│              └──────┬───────┘                                             │
└─────────────────────┼────────────────────────────────────────────────────┘
                      │ HTTP/WebSocket
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                  │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐              │
│  │  Auth     │  │  Upload   │  │ Predict   │  │  History  │              │
│  │  Routes   │  │  Routes   │  │  Service  │  │  Routes   │              │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘              │
│        │              │              │              │                      │
│        └──────────────┼──────────────┼──────────────┘                      │
│                       ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │                      SERVICES LAYER                          │        │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │        │
│  │  │ AuthService │  │FileService  │  │  PredictionService  │  │        │
│  │  │  (JWT)      │  │ (Storage)   │  │  (YOLO Inference)   │  │        │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │        │
│  └─────────────────────────────────────────────────────────────┘        │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ PostgreSQL│ │  Model   │ │   File   │
   │  Database │ │  Files   │ │  Storage │
   │  (Users, │ │ (YOLOv8) │ │ (Images, │
   │  History)│ │          │ │  Videos) │
   └──────────┘ └──────────┘ └──────────┘
```

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-------------|---------|---------|
| **Frontend** | React | 18.x | User interface |
| **Frontend Build** | Vite | 5.x | Fast development |
| **Frontend Router** | React Router | 6.x | Page navigation |
| **Frontend State** | Zustand | 4.x | Lightweight state |
| **HTTP Client** | Axios | 1.x | API requests |
| **WebSocket** | socket.io-client | 4.x | Real-time updates |
| **UI Components** | TailwindCSS | 3.x | Styling |
| **Charts** | Recharts | 2.x | Dashboard charts |
| **Backend** | FastAPI | 0.109.x | REST API |
| **Server** | Uvicorn | 0.27.x | ASGI server |
| **ORM** | SQLAlchemy | 2.x | Database |
| **Migrations** | Alembic | 1.x | DB migrations |
| **Auth** | python-jose | 3.x | JWT tokens |
| **PasswordHash** | Passlib | 1.x | Password hashing |
| **Validation** | Pydantic | 2.x | Data validation |
| **File Uploads** | python-multipart | - | Multi-part form |
| **ML Runtime** | Ultralytics | 8.x | YOLO inference |
| **ML Framework** | PyTorch | 2.x | Model loading |
| **Database** | PostgreSQL | 15.x | Primary DB |
| **File Storage** | Local/S3 | - | Media storage |

---

## Database Schema

### Entity Relationship Diagram

```
┌──────────────────┐         ┌──────────────────┐
│      users       │         │   predictions     │
├──────────────────┤         ├──────────────────┤
│ id (PK)          │◄────────│ id (PK)           │
│ email (UQ)       │         │ user_id (FK)       │
│ username (UQ)    │         │ file_name         │
│ password_hash    │         │ file_type         │
│ created_at       │         │ file_path         │
│ updated_at       │         │ status            │
│ is_active        │         │ result_json       │
└──────────────────┘         │ annotated_path   │
                              │ created_at       │
                              │ completed_at     │
                              │ error_message    │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │  detection_boxes │
                              ├──────────────────��
                              │ id (PK)           │
                              │ prediction_id(FK)│
                              │ class_name        │
                              │ confidence        │
                              │ x1, y1, x2, y2    │
                              │ annotated         │
                              └──────────────────┘
```

### SQL Tables

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Predictions table (images and videos)
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- 'image' or 'video'
    file_path VARCHAR(500) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    result_json JSONB,
    annotated_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    processing_time_ms INTEGER,
    total_detections INTEGER DEFAULT 0,
    damaged_count INTEGER DEFAULT 0,
    not_damaged_count INTEGER DEFAULT 0
);

-- Detection boxes (individual detections per prediction)
CREATE TABLE detection_boxes (
    id SERIAL PRIMARY KEY,
    prediction_id INTEGER REFERENCES predictions(id) ON DELETE CASCADE,
    class_name VARCHAR(100) NOT NULL,  -- 'damaged' or 'not_damaged'
    confidence FLOAT NOT NULL,
    x1 INTEGER NOT NULL,
    y1 INTEGER NOT NULL,
    x2 INTEGER NOT NULL,
    y2 INTEGER NOT NULL,
    annotated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_predictions_user_id ON predictions(user_id);
CREATE INDEX idx_predictions_status ON predictions(status);
CREATE INDEX idx_predictions_created_at ON predictions(created_at);
CREATE INDEX idx_detection_boxes_prediction_id ON detection_boxes(prediction_id);
```

### Pydantic Models

```python
# core/schemas.py

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class PredictionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
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
    user_id: int
    email: str


# Detection schemas
class DetectionBox(BaseModel):
    id: Optional[int] = None
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    annotated: bool = False


class PredictionRequest(BaseModel):
    confidence_threshold: float = 0.75
    save_annotated: bool = True


class PredictionResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    status: PredictionStatus
    result_json: Optional[dict] = None
    annotated_path: Optional[str] = None
    total_detections: int
    damaged_count: int
    not_damaged_count: int
    processing_time_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PredictionDetail(PredictionResponse):
    detections: List[DetectionBox] = []


# Statistics schemas
class DashboardStats(BaseModel):
    total_predictions: int
    total_images: int
    total_videos: int
    total_detections: int
    damaged_percentage: float
    avg_processing_time_ms: float
    recent_predictions: List[PredictionResponse]


# Health check
class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    database_connected: bool
```

---

## API Endpoints Specification

### Base URL: `/api/v1`

### Authentication Routes

| Method | Endpoint | Description | Auth |
|-------|----------|-------------|-----|
| POST | `/auth/register` | Register new user | Public |
| POST | `/auth/login` | Login, returns JWT | Public |
| POST | `/auth/refresh` | Refresh token | JWT |
| POST | `/auth/logout` | Invalidate token | JWT |
| GET | `/auth/me` | Get current user | JWT |

### Upload & Prediction Routes

| Method | Endpoint | Description | Auth |
|-------|----------|-------------|-----|
| POST | `/predictions/upload` | Upload image/video | JWT |
| GET | `/predictions` | List user's predictions | JWT |
| GET | `/predictions/{id}` | Get prediction detail | JWT |
| DELETE | `/predictions/{id}` | Delete prediction | JWT |
| GET | `/predictions/{id}/download` | Download annotated | JWT |

### Dashboard & Statistics Routes

| Method | Endpoint | Description | Auth |
|-------|----------|-------------|-----|
| GET | `/dashboard/stats` | Get dashboard statistics | JWT |
| GET | `/dashboard/chart-data` | Get chart data for graphs | JWT |
| GET | `/health` | Health check | Public |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `prediction:start` | Server→Client | Prediction started |
| `prediction:progress` | Server→Client | Progress update (0-100) |
| `prediction:complete` | Server→Client | Prediction finished |
| `prediction:error` | Server→Client | Prediction failed |

---

## API Request/Response Examples

### 1. Register User

**Request:**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "securepassword123"
}
```

**Response (201):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "created_at": "2026-04-23T10:00:00Z",
    "is_active": true
}
```

### 2. Login

**Request:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "securepassword123"
}
```

**Response (200):**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### 3. Upload Image for Prediction

**Request:**
```http
POST /api/v1/predictions/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <image file>
confidence_threshold: 0.75
save_annotated: true
```

**Response (202):**
```json
{
    "message": "Prediction queued",
    "prediction_id": 1,
    "status": "pending"
}
```

### 4. Get Prediction Detail

**Request:**
```http
GET /api/v1/predictions/1
Authorization: Bearer <token>
```

**Response (200):**
```json
{
    "id": 1,
    "file_name": "egg_image_001.jpg",
    "file_type": "image",
    "status": "completed",
    "result_json": {
        "model": "YOLOv8s",
        "confidence_threshold": 0.75,
        "inference_time_ms": 45,
        "detections": [
            {
                "class": "not_damaged",
                "confidence": 0.92,
                "bbox": [100, 50, 200, 150]
            },
            {
                "class": "damaged",
                "confidence": 0.87,
                "bbox": [300, 80, 400, 180]
            }
        ]
    },
    "annotated_path": "/uploads/annotated_1.jpg",
    "total_detections": 2,
    "damaged_count": 1,
    "not_damaged_count": 1,
    "processing_time_ms": 45,
    "created_at": "2026-04-23T10:05:00Z",
    "completed_at": "2026-04-23T10:05:01Z"
}
```

### 5. Get Dashboard Stats

**Request:**
```http
GET /api/v1/dashboard/stats
Authorization: Bearer <token>
```

**Response (200):**
```json
{
    "total_predictions": 150,
    "total_images": 120,
    "total_videos": 30,
    "total_detections": 450,
    "damaged_percentage": 28.5,
    "avg_processing_time_ms": 52.3,
    "recent_predictions": [
        {...},
        {...},
        {...}
    ]
}
```

---

## Frontend Component Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Loading.tsx
│   │   │   └── Modal.tsx
│   │   ├── layout/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── upload/
│   │   │   ├── DropZone.tsx
│   │   │   ├── FilePreview.tsx
│   │   │   └── UploadProgress.tsx
│   │   ├── dashboard/
│   │   │   ├── StatsCards.tsx
│   │   │   ├── Chart.tsx
│   │   │   └── RecentActivity.tsx
│   │   └── results/
│   ��       ├── DetectionList.tsx
│   │       ├── ImageViewer.tsx
│   │       └── ResultCard.tsx
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Upload.tsx
│   │   ├── History.tsx
│   │   └── Result.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── usePrediction.ts
│   │   └── useWebSocket.ts
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── predictions.ts
│   │   └── dashboard.ts
│   ├── store/
│   │   └── authStore.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
```

---

## Backend Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py             # Configuration
│   ├── database.py           # Database connection
│   └── security.py          # JWT/Security utilities
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── prediction.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── prediction.py
│   ├── routers/            # API routes
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── predictions.py
│   │   └── dashboard.py
│   ├── services/           # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── file_service.py
│   │   └── prediction_service.py
│   ├── ml/                 # ML components
│   │   ├── __init__.py
│   │   └── yolo_inference.py
│   └── utils/              # Utilities
│       ├── __init__.py
│       └── helpers.py
├── models/                  # YOLO model files
│   └── egg_detection_finetuned/
│       └── weights/
│           └── best.pt
├── uploads/                 # Uploaded files
├── alembic/               # Database migrations
├── requirements.txt
├── alembic.ini
├── .env.example
└── uvicorn_run.py
```

---

## YOLO Integration

```python
# app/ml/yolo_inference.py

import torch
from ultralytics import YOLO
from pathlib import Path
from typing import List, Dict, Any
import cv2
import numpy as np


class YOLOPredictor:
    def __init__(self, model_path: str, confidence: float = 0.75):
        self.model_path = model_path
        self.confidence = confidence
        self.class_names = ["not_damaged", "damaged"]
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = YOLO(self.model_path)
        return self._model

    def load_model(self):
        """Load YOLO model into memory."""
        if self._model is None:
            self._model = YOLO(self.model_path)
        return self._model is not None

    def predict_image(self, image_path: str) -> Dict[str, Any]:
        """Predict on a single image."""
        results = self.model(image_path, conf=self.confidence)
        return self._parse_results(results[0])

    def predict_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Predict on a frame (numpy array)."""
        results = self.model(frame, conf=self.confidence)
        return self._parse_results(results[0])

    def _parse_results(self, result) -> Dict[str, Any]:
        """Parse YOLO results into structured format."""
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
        """Draw bounding boxes on image."""
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
```

---

## Prediction Service Flow

```python
# app/services/prediction_service.py

import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any
import cv2

from app.ml.yolo_inference import YOLOPredictor
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionDetail


class PredictionService:
    def __init__(self, db, predictor: YOLOPredictor):
        self.db = db
        self.predictor = predictor
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

    async def process_image(
        self,
        user_id: int,
        file_data: bytes,
        file_name: str,
        confidence: float,
        save_annotated: bool
    ) -> PredictionDetail:
        start_time = time.time()
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_ext = Path(file_name).suffix
        stored_name = f"{file_id}{file_ext}"
        file_path = self.upload_dir / stored_name
        
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        # Create prediction record
        prediction = Prediction(
            user_id=user_id,
            file_name=file_name,
            file_type="image",
            file_path=str(file_path),
            status="processing"
        )
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        
        # Run YOLO prediction
        self.predictor.confidence = confidence
        result = self.predictor.predict_image(str(file_path))
        
        # Save annotated image
        annotated_path = None
        if save_annotated and result["detections"]:
            img = cv2.imread(str(file_path))
            annotated = self.predictor.draw_boxes(img, result["detections"])
            annotated_name = f"annotated_{file_id}{file_ext}"
            annotated_path = self.upload_dir / annotated_name
            cv2.imwrite(str(annotated_path), annotated)
        
        # Save detection boxes
        for det in result["detections"]:
            detection_box = DetectionBox(
                prediction_id=prediction.id,
                class_name=det["class"],
                confidence=det["confidence"],
                x1=det["bbox"][0],
                y1=det["bbox"][1],
                x2=det["bbox"][2],
                y2=det["bbox"][3],
                annotated=save_annotated
            )
            self.db.add(detection_box)
        
        # Update prediction record
        prediction.status = "completed"
        prediction.result_json = result
        prediction.annotated_path = str(annotated_path) if annotated_path else None
        prediction.total_detections = result["total"]
        prediction.damaged_count = result["damaged"]
        prediction.not_damaged_count = result["not_damaged"]
        prediction.processing_time_ms = int((time.time() - start_time) * 1000)
        prediction.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        return PredictionDetail.from_orm(prediction)
```

---

## Authentication Flow

```python
# app/security.py

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user
```

---

## WebSocket Real-time Updates

```python
# app/routers/predictions.py

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import List

from app.security import get_current_user
from app.database import get_db


router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_prediction_update(self, prediction_id: int, event: str, data: dict):
        message = {"prediction_id": prediction_id, "event": event, "data": data}
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/predictions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## Configuration

```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Egg-CV API"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/eggcvdatabase"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Files
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50
    
    # Model
    MODEL_PATH: str = "models/egg_detection_finetuned/weights/best.pt"
    CONFIDENCE_THRESHOLD: float = 0.75
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
```

---

## Testing Strategy

### Unit Tests
- Authentication (register, login, token validation)
- File upload (size limits, type validation)
- YOLO inference (result parsing)
- Database models (CRUD operations)

### Integration Tests
- Full prediction pipeline
- Authentication flow
- Dashboard statistics

### Manual Tests
- Large file uploads
- Concurrent predictions
- WebSocket reconnection

---

## Deployment Considerations (Post-MVP)

- [ ] Containerization (Docker)
- [ ] GPU inference setup
- [ ] Object storage (S3)
- [ ] CI/CD pipeline
- [ ] Monitoring & logging
- [ ] Rate limiting
- [ ] Caching (Redis)

---

## Quick Start Commands

```bash
# Backend
cd backend
cp .env.example .env
# Update .env with database credentials

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Next Steps

1. **Set up PostgreSQL database**
2. **Initialize backend project structure**
3. **Implement authentication**
4. **Integrate YOLO model**
5. **Build file upload & prediction**
6. **Create React frontend**
7. **Add dashboard & history**
8. **Test and iterate**