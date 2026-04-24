from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

from app.models import User
from app.security import get_password_hash, verify_password, create_access_token


class AuthService:
    def register_user(self, db: Session, email: str, username: str, password: str) -> User:
        existing = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing:
            if existing.email == email:
                raise ValueError("Email already registered")
            else:
                raise ValueError("Username already taken")
        
        user = User(
            email=email,
            username=username,
            password_hash=get_password_hash(password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user

    def create_token(self, user: User) -> str:
        return create_access_token({"sub": str(user.id), "email": user.email})


auth_service = AuthService()