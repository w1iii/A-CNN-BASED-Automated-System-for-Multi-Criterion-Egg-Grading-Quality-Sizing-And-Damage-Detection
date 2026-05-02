from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserSettings, UserSettingsUpdate
from app.security import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettings)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return UserSettings(mm_per_pixel=current_user.mm_per_pixel)


@router.put("")
def update_settings(
    settings: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.mm_per_pixel = settings.mm_per_pixel
    db.commit()
    return {"message": "Settings updated successfully", "mm_per_pixel": settings.mm_per_pixel}