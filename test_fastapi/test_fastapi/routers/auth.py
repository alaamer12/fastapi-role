"""
Authentication router for the test application.
Simple JWT-based authentication for testing RBAC.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..auth import authenticate_user, create_access_token
from ..schemas import MessageResponse

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_email: str
    user_role: str


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Simple login endpoint for testing.
    In a real application, you would verify password here.
    """
    user = authenticate_user(db, login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_email=user.email,
        user_role=user.role
    )


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """
    Logout endpoint.
    In a real application, you might invalidate the token here.
    """
    return MessageResponse(message="Successfully logged out")


@router.get("/test-users", response_model=dict)
async def get_test_users(db: Session = Depends(get_db)):
    """
    Get list of test users for easy login during development.
    Remove this in production!
    """
    from ..models import User
    
    users = db.query(User).all()
    return {
        "message": "Available test users (for development only)",
        "users": [
            {
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
            for user in users
        ]
    }