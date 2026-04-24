import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from fastapi.staticfiles import StaticFiles

from app.config import settings


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


class FileService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
        
    def get_file_type(self, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_IMAGE_EXTENSIONS:
            return "image"
        elif ext in ALLOWED_VIDEO_EXTENSIONS:
            return "video"
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def is_allowed_file(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in ALLOWED_IMAGE_EXTENSIONS or ext in ALLOWED_VIDEO_EXTENSIONS
    
    async def save_file(self, file: UploadFile) -> tuple[str, str]:
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        stored_name = f"{file_id}{ext}"
        file_path = self.upload_dir / stored_name
        
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        file_type = self.get_file_type(file.filename)
        return str(file_path), file_type
    
    def save_file_sync(self, file: UploadFile) -> tuple[str, str]:
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        stored_name = f"{file_id}{ext}"
        file_path = self.upload_dir / stored_name
        
        content = file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_type = self.get_file_type(file.filename)
        return str(file_path), file_type
    
    def delete_file(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception:
            return False


file_service = FileService()